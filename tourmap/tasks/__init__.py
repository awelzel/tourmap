import logging
import dateutil.parser

from tourmap import database
from tourmap.utils import strava

logger = logging.getLogger(__name__)

def sync_activities(user_id, environ=None):
    user = database.User.query.filter_by(id=user_id).one()
    token = user.token.access_token

    client = strava.StravaClient.from_env(environ=environ)
    page = 1
    while True:
        logger.info("Fetching page %d...", page)
        activities = list(client.activities(token=token, page=page, per_page=4))
        if not activities:
            break


        for src in activities:
            resource_state = src.get("resource_state", -1)
            if resource_state < 0:
                logger.warning("Skipping id=%d resource_state=%d\n",
                               resource_state, src["id"])
                continue

            # Fetch the detailed activity!
            # src = client.activity(token, src["id"])
            # import IPython
            # IPython.embed()
            # get_or_create approach based on strava id
            activity = (database.Activity.query
                        .filter_by(strava_id=src["id"])
                        .one_or_none())
            if activity is None:
                activity = database.Activity(
                    user=user,
                    strava_id=src["id"]
                )
            else:
                if activity.user_id != user.id:
                    raise Exception("not good...")

            activity.update_from_strava(src)
            database.db.session.add(activity)

            requested_image_size = 256

            for p in client.activity_photos(token, activity.strava_id, size=256):
            # Fetch photos with get_or_create()
                photo = database.ActivityPhoto.query.filter_by(strava_unique_id=p["unique_id"]).one_or_none()

                sizes = list(p["sizes"].values())
                if len(sizes) != 1:
                    raise Exception("Bad sizes {}".format(repr(sizes)))
                width, height = sizes[0]

                if width != requested_image_size and height != requested_image_size:
                    raise Exception("Got weird sizes {}".format(repr(sizes)))

                # import IPython
                # IPython.embed()
                if photo is None:
                    # import IPython
                    # IPython.embed()
                    photo = database.ActivityPhoto(
                        strava_unique_id=p["unique_id"],
                        user=user,
                        activity=activity,
                        caption=p.get("caption"),
                        width=width,
                        height=height,
                        url=list(p["urls"].values())[0]
                    )
                    database.db.session.add(photo)

        logger.info("DIRTY OBJECTS: %s", repr(database.db.session.dirty))
        database.db.session.commit()

        page += 1

    logger.info("Done!")
