"""
For simplicity, also define the models here.
"""
import logging

import dateutil.parser
import hashids
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError


logger = logging.getLogger(__name__)

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    strava_id = db.Column(db.Integer, unique=True, nullable=False)
    firstname = db.Column(db.String(80), nullable=True)
    lastname = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    @property
    def token(self):
        return self.token_list[0]

    @property
    def hashid(self, salt=None):
        # XXX" This is ugly
        from tourmap.app import app
        salt = app.config["HASHIDS_SALT"]
        min_length = app.config["HASHIDS_MIN_LENGTH"]

        hids = hashids.Hashids(salt, min_length=min_length)
        return hids.encode(self.id)

    @staticmethod
    def get_by_hashid(hashid):
        from tourmap.app import app
        salt = app.config["HASHIDS_SALT"]
        min_length = app.config["HASHIDS_MIN_LENGTH"]
        hids = hashids.Hashids(salt, min_length=min_length)
        user_id = hids.decode(hashid)
        if len(user_id) != 1:
            return None
        return User.query.get(user_id)

class Token(db.Model):
    __tablename__ = "tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    access_token = db.Column(db.String(64), nullable=False)
    user = db.relationship(User, backref="token_list")

class Activity(db.Model):
    """
    Most importantly, datetime, name and distance.
    """
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    strava_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    start_date_local = db.Column(db.DateTime, nullable=False)
    utc_offset = db.Column(db.Integer, nullable=False)
    summary_polyline = db.Column(db.Text, nullable=True)

    user = db.relationship(User)

    def update_from_strava(self, src):
        """
        Update from a dict as provided by the Strava API with condition checks
        """
        if not self.name or self.name != src["name"]:
            self.name = src["name"]

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

        polyline = src.get("map", {}).get("summary_polyline")
        if polyline and self.summary_polyline != polyline:
            self.summary_polyline = polyline

# Add activities.
User.activities = db.relationship(Activity, order_by=Activity.start_date_local.desc())
