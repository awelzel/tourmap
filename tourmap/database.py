"""
For simplicity, also define the models here.
"""
import logging

import dateutil.parser
import hashids
import polyline

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError


logger = logging.getLogger(__name__)

db = SQLAlchemy()

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
        print("id=", id)
        if len(id) != 1:
            return None
        return cls.query.get(id[0])

    @property
    def hashid(self, salt=None):
        return self.__get_Hashids().encode(self.id)


class User(db.Model, HashidMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    strava_id = db.Column(db.BigInteger, unique=True, nullable=False)
    firstname = db.Column(db.String(80), nullable=True)
    lastname = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    @property
    def token(self):
        return self.token_list[0]

class Token(db.Model):
    __tablename__ = "tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    access_token = db.Column(db.String(64), nullable=False)
    user = db.relationship(User, backref="token_list")


class Tour(db.Model, HashidMixin):
    __tablename__ = "tours"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship(User)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    filter_start_date = db.Column(db.DateTime, nullable=True)
    filter_end_date = db.Column(db.DateTime, nullable=True)

    tilelayer_provider = db.Column(db.String(16), nullable=True)
    polyline_color = db.Column(db.String(16), nullable=True)

    @property
    def activities(self):
        query = Activity.query.filter_by(user=self.user)
        if self.filter_start_date:
            query = query.filter(Activity.start_date >= self.filter_start_date)
        if self.filter_end_date:
            query = query.filter(Activity.end_date <= self.filter_end_date)

        return query

User.tours = db.relationship(Tour, order_by=Tour.id)

class Activity(db.Model):
    """
    Most importantly, datetime, name and distance.
    """
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    strava_id = db.Column(db.BigInteger, unique=True, nullable=False)
    external_id = db.Column(db.String(255), nullable=True)
    type = db.Column(db.String(32), nullable=False);

    name = db.Column(db.String(255))
    description = db.Column(db.Text, nullable=True)

    distance = db.Column(db.Float);
    moving_time = db.Column(db.Integer);
    elapsed_time = db.Column(db.Integer);
    total_elevation_gain = db.Column(db.Float)
    average_temp = db.Column(db.Float, nullable=True)

    start_date = db.Column(db.DateTime, nullable=False)
    start_date_local = db.Column(db.DateTime, nullable=False)
    utc_offset = db.Column(db.Integer, nullable=False)
    timezone = db.Column(db.String(64))

    start_lat = db.Column(db.Float)
    start_lng = db.Column(db.Float)
    end_lat = db.Column(db.Float)
    end_lng = db.Column(db.Float)
    summary_polyline = db.Column(db.Text)


    user = db.relationship(User)

    @property
    def latlngs(self):
        """
        This is so ugly, it is not funny anymore.
        """
        if self.summary_polyline:
            return polyline.decode(self.summary_polyline)
        return []


    def update_from_strava(self, src):
        """
        Update from a dict as provided by the Strava API with condition checks
        """
        if src.get("external_id") and self.external_id != src.get("external_id"):
            self.external_id = src["external_id"]

        if self.type != src["type"]:
            self.type = src["type"]

        if not self.name or self.name != src["name"]:
            self.name = src["name"]

        if src.get("description") and self.description != src.get("description"):
            self.description = src["description"]

        start_date = dateutil.parser.parse(src["start_date"])
        if start_date.tzinfo is not None and start_date.utcoffset().seconds != 0:
            raise Exception("Non UTC date parsed! {!r}".format(src["start_date"]))
        start_date = start_date.replace(tzinfo=None)
        if self.start_date is None or self.start_date != start_date:
            self.start_date = start_date

        start_date_local = dateutil.parser.parse(src["start_date_local"])
        if start_date_local.tzinfo is not None and start_date_local.utcoffset().seconds != 0:
            raise Exception("Non UTC date parsed! {!r}".format(src["start_date_local"]))
        start_date_local = start_date_local.replace(tzinfo=None)
        if self.start_date_local is None or self.start_date_local != start_date_local:
            self.start_date_local = start_date_local

        if self.utc_offset is None or self.utc_offset != int(src["utc_offset"]):
            self.utc_offset = int(src["utc_offset"])

        if src.get("timezone") and self.timezone != src["timezone"]:
            self.timezone = src["timezone"]


        polyline = src.get("map", {}).get("summary_polyline")
        if polyline and self.summary_polyline != polyline:
            self.summary_polyline = polyline

        # XXX: No check for changes here...
        start_latlng = src.get("start_latlng", [None, None])
        end_latlng = src.get("end_latlng", [None, None])
        self.start_lat, self.start_lng = start_latlng[0], start_latlng[1]
        self.end_lat, self.end_lng = end_latlng[0], end_latlng[1]
        self.distance = src.get("distance")
        self.moving_time = src.get("moving_time")
        self.elapsed_time = src.get("elapsed_time")
        self.total_elevation_gain = src.get("total_elevation_gain")
        self.average_temp = src.get("average_temp")


# Add activities.
User.activities = db.relationship(Activity, order_by=Activity.start_date_local.desc())


# XXX: Need photos endpoints
class ActivityPhoto(db.Model):
    __tablename__ = "activity_photos"
    id = db.Column(db.Integer, primary_key=True)
    strava_unique_id = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), nullable=False)
    caption = db.Column(db.Text)

    width = db.Column(db.SmallInteger, nullable=False)
    height = db.Column(db.SmallInteger, nullable=False)
    url = db.Column(db.String(255), nullable=False)

    user = db.relationship(User)
    activity = db.relationship(Activity)

Activity.photos = db.relationship(ActivityPhoto, order_by=ActivityPhoto.id)
