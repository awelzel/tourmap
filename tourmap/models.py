import json

from tourmap.database import db
from tourmap.database import Activity, Tour, User  # Should move them over!
from sqlalchemy.schema import Index

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
    full_fetch_completed = db.Column(db.Boolean, default=False)
    last_fetch_completed_at = db.Column(db.DateTime, nullable=True)

    total_fetches = db.Column(db.BigInteger, default=0, nullable=False);

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
    json_blob = db.Column(db.TEXT)
    user = db.relationship(User)
    activity = db.relationship(Activity)

    def get_photos(self, size=256):
        d = json.loads(self.json_blob)
        return d.get(str(size), [])


Activity.photos = db.relationship(ActivityPhotos, order_by=ActivityPhotos.id, uselist=False)
