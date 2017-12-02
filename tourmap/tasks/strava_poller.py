"""
Run endlessly, polling Strava for activities.

Requires to be run as a flask cli command, since we are making use of
the flask SQLAlchemy setup...

## Design Notes

The main thread polls the database in regular intervals to find users with:

      a) A non completed full fetch...
      b) Users with the last fetch time greater than a given delta.

It then submits the tasks to a ThreadPoolExecutor to work on. The idea is
that the whole thing is extremly IO bound, so threads are just fine.
"""
import datetime
import json
import logging
import queue
import time
from concurrent.futures import ThreadPoolExecutor

from tourmap.models import PollState, Activity, ActivityPhotos
from tourmap.utils import dt2ts

logger = logging.getLogger(__name__)

class StravaPoller(object):

    def __init__(self, session, strava_client_constructor,
                 per_page_default=4, executor=None):
        """
        :param session: SQLAlchemy session
        :param db: Session object to work with...
        :param strava_client_constructor: How to construct StravaClient objects
        :param executor: The executor to use, defaults to ThreadPoolExecutor()
            with all defaults...
        """
        self.__session = session
        self.__executor = executor or ThreadPoolExecutor()
        self.__result_futures = {}
        self.__strava_client_constructor = strava_client_constructor
        self.__client_pool = queue.Queue()
        self.__per_page_default = per_page_default

        # How often do we want to run the latest check?
        self.__latest_interval_seconds = 5
        self.__latest_lookback_seconds = 0
        self.__latest_lookback_days = 14
        self.__latest_lookback_per_page = 50

    def _sleep(self):
        logger.debug("Sleep...")
        # XXX: We should either sleep until the executor finished a job,
        #      or a maximum time has exceeded...
        time.sleep(0.5)

    def _now(self):
        return datetime.datetime.utcnow()

    def _has_submitted_ids(self):
        return len(self.__result_futures) > 0

    def _get_submitted_ids(self):
        return list(self.__result_futures.keys())

    def _get_strava_client(self):
        class ClientManager(object):
            def __init__(self, pool, constructor):
                self.__pool = pool
                self.__constructor = constructor
                self.__client = None

            def __enter__(self):
                try:
                    self.__client = self.__pool.get_nowait()
                except queue.Empty:
                    self.__client = self.__constructor()
                return self.__client

            def __exit__(self, *args, **kwargs):
                print("__exit__", repr(args), repr(kwargs))
                self.__pool.put(self.__client)

        return ClientManager(self.__client_pool, self.__strava_client_constructor)

    def _get_poll_states(self):
        """
        Find PollStates in the DB that need to be worked on.

          a) Those that where full_fetch_completed is False
          b) Those that havent't been polled since
             self.__latest_interval_seconds...
          c) Filter a) and b) with self.__poll_states_submitted

        :returns: iterator over all poll states that match above
            criterias.
        """
        full_fetch_in_progress = (
            PollState.full_fetch_completed.is_(None)
            | PollState.full_fetch_completed.is_(False)
        )
        last_fetch_before_dt = self._now() - datetime.timedelta(
            seconds=self.__latest_interval_seconds
        )
        needs_latest_fetch = (
            PollState.full_fetch_completed.is_(True) & (
                PollState.last_fetch_completed_at.is_(None)
                | (PollState.last_fetch_completed_at < last_fetch_before_dt)
            )
        )

        query = (
            self.__session.query(PollState)
            .filter(full_fetch_in_progress | needs_latest_fetch)
        )
        if self._has_submitted_ids():
            query = query.filter(PollState.id.notin_(self._get_submitted_ids()))

        for state in query:
            yield state

    def _submit(self, executor):
        """
        Find PollState instances that should be worked on and submit
        them to the executor...
        """
        for poll_state in self._get_poll_states():
            submit_kwargs = {
                "user": poll_state.user,
                "token": poll_state.user.token,
                "poll_state": poll_state,
            }
            logger.debug("Submitting: %s", repr(submit_kwargs))
            future = executor.submit(self.fetch_activities, **submit_kwargs)
            assert poll_state.id not in self.__result_futures
            self.__result_futures[poll_state.id] = (future, submit_kwargs)

    def _process_result(self, poll_state_id, result, submit_kwargs):
        """

        """
        poll_state = PollState.query.get(poll_state_id)
        user = poll_state.user

        for activity_info in result["activity_infos"]:
            a = activity_info["activity"]
            activity = Activity.query.filter_by(strava_id=a["id"]).one_or_none()
            if activity is None:
                activity = Activity(user=user, strava_id=a["id"])
            else:
                assert activity.user_id == user.id

            activity.update_from_strava(a)
            self.__session.add(activity)

            # We store all pictures in a single row as a blob. This
            # way we will not bloat the table so much.
            # table too much. We use a JSON column to do so...
            photos_dict = {}
            for size, photos in activity_info["photos"].items():
                photos_dict.setdefault(size, [])
                photos_list = photos_dict[size]
                for p in photos:
                    photos_list.append({
                        "url": list(p["urls"].values())[0],
                        "caption": p.get("caption"),
                        "width": p["__tourmap_width"],
                        "height": p["__tourmap_height"],
                    })

            photo = ActivityPhotos.query.filter_by(activity=activity).one_or_none()
            if photo is None:
                photo = ActivityPhotos(user=user, activity=activity)

            # We do this on every poll... It might hurt :-/
            json_blob = json.dumps(photos_dict, sort_keys=True)
            if not photo.json_blob or photo.json_blob != json_blob:
                photo.json_blob = json_blob

            self.__session.add(photo)

        # Updating PollState:
        for k, v in result["state_update"].items():
            getattr(poll_state, k)
            setattr(poll_state, k, v)
            self.__session.add(poll_state)

        # Commit after we worked through one result.
        self.__session.commit()

    def _process_result_futures(self):
        """
        If something was found that had a status of "done", return True
        else False.
        """
        found_done_future = False
        for poll_state_id, (future, submit_kwargs) in list(self.__result_futures.items()):
            if not future.done():
                continue

            found_done_future = True
            logger.debug("Processing done future: %s", future)
            try:
                result = future.result()
                self._process_result(poll_state_id, result, submit_kwargs)
            except Exception as e:
                self.__session.rollback()
                logger.exception("Job failed: %s", repr(e))
            finally:
                self.__result_futures.pop(poll_state_id)

        return found_done_future

    def run(self):
        with self.__executor as executor:
            self._run(executor)

    def _run(self, executor):
        """
        Run endlessly
        """
        while True:
            self._submit(executor)
            # Only if there was no work to be done, sleep a bit, else
            # kick in another _submit() round...
            if not self._process_result_futures():
                self._sleep()

    def _fetch_photos_for_activity(self, client, token, activity):
        """
        Fetch photos for two sizes with some error checking.
        """
        requested_sizes = [256, 1024]
        result_photos = {}

        if activity["total_photo_count"] == 0:
            logger.debug("Skipping photo fetch...")
            return result_photos


        for requested_size in requested_sizes:
            photos = client.activity_photos(token.access_token, activity["id"],
                                            size=requested_size)
            logger.debug("Got %d photos for size %d", len(photos), requested_size)
            for p in photos:
                sizes = list(p["sizes"].values())
                if len(sizes) != 1:
                    raise Exception("Bad sizes {}".format(repr(sizes)))
                width, height = sizes[0]

                if width != requested_size and height != requested_size:
                    raise Exception("Got weird sizes {}".format(repr(sizes)))
                p["__tourmap_width"] = width
                p["__tourmap_height"] = height

            result_photos[requested_size] = photos
        return result_photos

    @staticmethod
    def _activity_resource_state_filter(activities):
        for a in activities:
            resource_state = a.get("resource_state", -1)
            if resource_state < 0:
                logger.warning("Skipping id=%d resource_state=%d", resource_state, a["id"])
                continue
            yield a

    def _full_fetch(self, client, user, token, poll_state):
        """
        Do a single page based fetch iteration.

        XXX: This sucks, we should have just used before iteration and
             then iterate with a <= before value over intervals of 10
             days? But then we do not know when to stop, I guess...
        """
        result_activities = []
        logger.debug("FULL FETCH MODE for %s %s", user, token)

        # Pages start at!
        page = poll_state.full_fetch_next_page or 1
        per_page = poll_state.full_fetch_per_page or self.__per_page_default
        activities = list(client.activities(
            token=token.access_token,
            page=page,
            per_page=per_page
        ))
        for a in self._activity_resource_state_filter(activities):
            result_photos = self._fetch_photos_for_activity(client, token, a)
            result_activities.append({
                "activity": a,
                "photos": result_photos,
            })
        return {
            "activity_infos": result_activities,
            "state_update": {
                "full_fetch_next_page": page + 1,
                "full_fetch_per_page": per_page,
                "full_fetch_completed": len(result_activities) == 0,
                "total_fetches": poll_state.total_fetches + 1,
                "last_fetch_completed_at": self._now(),
            },
        }

    def _latest_fetch(self, client, user, token, poll_state):
        """
        Fetch the past X days...
        """
        logger.debug("LATEST FETCH MODE for %s %s", user, token)
        result_activities = []
        now = self._now()
        last_fetch_completed_at = poll_state.last_fetch_completed_at or now
        after_td = datetime.timedelta(
            days=self.__latest_lookback_days,
            seconds=self.__latest_lookback_seconds
        )
        after_dt = last_fetch_completed_at - after_td

        # This can trigger if the poller hasn't completed this user in
        # one day or so...
        if now - after_dt > (after_td + datetime.timedelta(days=1)):
            logger.warning("Probably missed some stuff and should trigger "
                           "a full fetch for %s %s now=%s after_dt=%s",
                           user, poll_state, now.isoformat(), after_dt.isoformat())

        after_ts = dt2ts(after_dt)

        logger.debug("Fetching activities after %s (%s)", after_dt.isoformat(), after_ts)
        activities = list(client.activities(
            token=token.access_token,
            after=after_ts,
            per_page=self.__latest_lookback_per_page,
        ))

        if len(activities) >= self.__latest_lookback_per_page:
            logger.warning("Latest fetch got per_page or more results. "
                           "This means we may have missed some activities. "
                           "per_page=%s len(activities)=%s",
                           self.__latest_lookback_per_page, len(activities))

        logger.debug("Got %s activities", len(activities))
        for a in self._activity_resource_state_filter(activities):
            result_photos = self._fetch_photos_for_activity(client, token, a)
            result_activities.append({
                "activity": a,
                "photos": result_photos,
            })
        return {
            "activity_infos": result_activities,
            "state_update": {
                "total_fetches": poll_state.total_fetches + 1,
                "last_fetch_completed_at": self._now(),
            },
        }

    def _fetch_activities(self, client, user, token, poll_state):
        """
        Dispatch between doing a full fetch or a latest fetch depending
        on the poll_state.
        """
        if not poll_state.full_fetch_completed:
            return self._full_fetch(client, user, token, poll_state)
        return self._latest_fetch(client, user, token, poll_state)

    def fetch_activities(self, user, token, poll_state):
        """
        :returns: list results with { "activity": {strava}, "activity_photos": {strava}
        """
        with self._get_strava_client() as client:
            return self._fetch_activities(client, user, token, poll_state)
