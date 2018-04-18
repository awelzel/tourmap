import datetime

import dateutil.parser
import hashids
import polyline
from sqlalchemy.schema import Index, UniqueConstraint

from tourmap.resources import db
from tourmap.utils import seconds_to_readable_interval
from tourmap.utils import json


class HashidMixin(object):

    @classmethod
    def __get_Hashids(cls):
        # XXX" This is ugly
        from tourmap.app import app
        salt = app.config["HASHIDS_SALT"]
        salt = "{}{}".format(cls.__name__, salt)
        min_length = app.config["HASHIDS_MIN_LENGTH"]
        return hashids.Hashids(salt, min_length=min_length)

    @classmethod
    def get_by_hashid(cls, hashid):
        id = cls.__get_Hashids().decode(hashid)
        if len(id) != 1:
            return None
        return cls.query.get(id[0])

    @property
    def hashid(self):
        return self.__get_Hashids().encode(self.id)


class User(db.Model, HashidMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    strava_id = db.Column(db.BigInteger, unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    firstname = db.Column(db.String(255))
    lastname = db.Column(db.String(255))
    country = db.Column(db.String(255))

    @property
    def name_str(self):
        return " ".join(filter(None, [self.firstname, self.lastname]))

    @property
    def strava_link(self):
        """
        Hackish...
        """
        return "https://www.strava.com/athletes/{}".format(self.strava_id)


class Tour(db.Model, HashidMixin):
    __tablename__ = "tours"
    __table_args__ = (
        UniqueConstraint("user_id", "name",
                         name="uq_%(column_0_label)s %(column_1_name)s"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship(User)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)

    # Display settings
    tilelayer_provider = db.Column(db.String(16), nullable=True)
    polyline_color = db.Column(db.String(16), nullable=True)
    polyline_weight = db.Column(db.SmallInteger, nullable=True)
    marker_positioning = db.Column(db.String(16), nullable=True)
    marker_enable_clusters = db.Column(
        db.Boolean(name="marker_enable_clusters"), nullable=True
    )

    # Privacy settings
    public = db.Column(db.Boolean(name="public"), default=False)

    @property
    def activities(self):
        query = Activity.query.filter_by(user=self.user)
        if self.start_date:
            query = query.filter(Activity.start_date >= self.start_date)
        if self.end_date:
            query = query.filter(Activity.start_date <= self.end_date)
        return query

    @property
    def start_date_str(self):
        return self.start_date.date().isoformat() if self.start_date is not None else ""

    @property
    def end_date_str(self):
        return self.end_date.date().isoformat() if self.end_date is not None else ""

    @staticmethod
    def default_tour_for(user):
        return Tour(
            user=user,
            name="All Activities",
            marker_positioning="middle",
            marker_enable_clusters=True,
            description="Automatically created."
        )

    @staticmethod
    def get_public_tours():
        return Tour.query.filter(Tour.public.is_(True))


User.tours = db.relationship(Tour, order_by=Tour.id)


class Activity(db.Model):
    """
    Most importantly, datetime, name and distance.
    """
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    strava_id = db.Column(db.BigInteger, unique=True, nullable=False)
    external_id = db.Column(db.String(255))
    type = db.Column(db.String(32), nullable=False)

    name = db.Column(db.String(255), nullable=False)

    distance = db.Column(db.Float)
    moving_time = db.Column(db.Integer, nullable=False)
    elapsed_time = db.Column(db.Integer, nullable=False)
    total_elevation_gain = db.Column(db.Float)
    average_temp = db.Column(db.Float)

    start_date = db.Column(db.DateTime, nullable=False)
    start_date_local = db.Column(db.DateTime, nullable=False)
    utc_offset = db.Column(db.Integer, nullable=False)
    timezone = db.Column(db.String(64))

    start_lat = db.Column(db.Float)
    start_lng = db.Column(db.Float)
    end_lat = db.Column(db.Float)
    end_lng = db.Column(db.Float)
    summary_polyline = db.Column(db.Text)

    total_photo_count = db.Column(db.Integer)

    user = db.relationship(User)

    @property
    def latlngs(self):
        if self.summary_polyline:
            return polyline.decode(self.summary_polyline)
        return []

    @property
    def moving_time_str(self):
        return seconds_to_readable_interval(seconds=self.moving_time)

    @property
    def elapsed_time_str(self):
        return seconds_to_readable_interval(seconds=self.elapsed_time)

    @property
    def distance_str(self):
        """
        Cycling is all about kilometers! Suck it!
        """
        if self.distance is None:
            return ""

        suffix = "m"
        divisor = 1.0
        if self.distance > 1000.0:
            suffix = "km"
            divisor = 1000.0

        return "{:.1f} {}".format(self.distance / divisor, suffix)

    @property
    def elevation_gain_str(self):
        if self.total_elevation_gain is None:
            return "0 m"
        return "{:.1f} m".format(self.total_elevation_gain)

    @property
    def average_temp_str(self):
        if self.average_temp is None:
            return ""
        return "{:.0f} °C".format(self.average_temp)

    @property
    def strava_link(self):
        """
        Hackish...
        """
        return "https://www.strava.com/activities/{}".format(self.strava_id)

    def update_from_strava(self, src):
        """
        Update from a dict as provided by the Strava API with condition checks
        """
        assert self.strava_id == src["id"], (
            "Wrong activity?! {} != {}".format(self.strava_id, src["id"])
        )
        self.external_id = src["external_id"]
        self.type = src["type"]
        self.name = src.get("name", "")

        # Unify this to a single method!
        start_date = dateutil.parser.parse(src["start_date"])
        if start_date.tzinfo is not None:
            if start_date.utcoffset().seconds != 0:
                raise Exception("Non UTC date parsed! {!r}".format(src["start_date"]))
        start_date = start_date.replace(tzinfo=None)
        self.start_date = start_date

        start_date_local = dateutil.parser.parse(src["start_date_local"])
        if start_date_local.tzinfo is not None:
            if start_date_local.utcoffset().seconds != 0:
                msg = "Non UTC date parsed! {!r}".format(start_date_local)
                raise Exception(msg)

        start_date_local = start_date_local.replace(tzinfo=None)
        self.start_date_local = start_date_local

        self.utc_offset = int(src["utc_offset"])
        self.timezone = src["timezone"]

        summary_polyline = src.get("map", {}).get("summary_polyline")
        self.summary_polyline = summary_polyline

        # XXX: We should probably just do a loop...
        start_latlng = src.get("start_latlng", [None, None]) or [None, None]
        self.start_lat, self.start_lng = start_latlng[0], start_latlng[1]
        end_latlng = src.get("end_latlng", [None, None]) or [None, None]
        self.end_lat, self.end_lng = end_latlng[0], end_latlng[1]
        self.distance = src.get("distance")
        self.moving_time = src.get("moving_time")
        self.elapsed_time = src.get("elapsed_time")
        self.total_elevation_gain = src.get("total_elevation_gain")
        self.average_temp = src.get("average_temp")
        self.total_photo_count = src.get("total_photo_count", 0)


User.activities = db.relationship(Activity, order_by=Activity.start_date_local.desc())


class Token(db.Model):
    __tablename__ = "tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"),
                        unique=True, nullable=False)
    access_token = db.Column(db.String(64), nullable=False)
    user = db.relationship(User, backref=db.backref("token", uselist=False))


class PollState(db.Model):
    """
    One row for each user we poll for.
    """
    __tablename__ = "strava_poll_states"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"),
                        unique=True, nullable=False)
    user = db.relationship(User, backref=db.backref("poll_state", uselist=False))

    # If the user deletes activities while a full fetch is in progress,
    # we may miss some... Lets ignore for now and allow to trigger refetching.
    full_fetch_next_page = db.Column(db.SmallInteger)
    full_fetch_per_page = db.Column(db.SmallInteger)
    full_fetch_completed = db.Column(
        db.Boolean(name="full_fetch_completed"), default=False
    )
    last_fetch_completed_at = db.Column(db.DateTime)

    total_fetches = db.Column(db.BigInteger, default=0, nullable=False)

    # State if something bad has happened...
    error_happened = db.Column(db.Boolean(name="error_happened"))
    error_happened_at = db.Column(db.DateTime)
    error_message = db.Column(db.String(255))
    error_data = db.Column(db.Text)

    # If set do not pull from this anymore.
    stopped = db.Column(db.Boolean(name="stopped"))

    def clear_error(self):
        self.error_happened = False
        self.error_happened_at = None
        self.error_message = None
        self._set_error_data({})

    def set_error(self, message, error_data):
        """
        Record an error state. Note, this *also* sets last_fetch_completed_at,
        as currently only a fetch can put the poll_state into an error.
        This may or may not be clear, but if we do not set it, the poller
        will pick up the failed poll_state again.

        Note, we really should have a log table where all the errors are kept so
        that we still have them after a clear_error()
        """
        now = datetime.datetime.utcnow()
        self.error_happened = True
        self.error_message = message
        self._set_error_data(error_data)

        # Set timestamps
        self.error_happened_at = now
        self.last_fetch_completed_at = now

    def get_error_data(self):
        if not self.error_data:
            return {}
        return json.loads(self.error_data)

    def _set_error_data(self, error_data):
        self.error_data = json.dumps(error_data)

    def stop(self):
        self.stopped = True

    def start(self):
        self.stopped = False

    def __repr__(self):
        return "<PollState {}>".format(self.id)

    # We currently do not want to fetch based on last_fetch_timestamp
    __table_args__ = (
        Index("ix_strava_poll_states_full_fetch_completed_at",
              "full_fetch_completed", "last_fetch_completed_at"),
    )


class ActivityPhotos(db.Model):
    __tablename__ = "activity_photos"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), nullable=False)

    # A JSON map with sizes to lists of photos. Each photo is a map with
    # "width", "height", "url", "caption"
    data = db.Column(db.TEXT, nullable=False)
    user = db.relationship(User)
    activity = db.relationship(Activity)

    def get_photos(self):
        data = json.loads(self.data)
        return {int(size): photos for (size, photos) in data.items()}


Activity.photos = db.relationship(ActivityPhotos, order_by=ActivityPhotos.id,
                                  uselist=False)
