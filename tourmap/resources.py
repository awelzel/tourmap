import flask_sqlalchemy
from sqlalchemy.exc import IntegrityError  # pylint: disable=unused-import
from sqlalchemy.schema import MetaData

import tourmap.flask_strava as flask_strava

naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=naming_convention)

db = flask_sqlalchemy.SQLAlchemy(metadata=metadata)

strava = flask_strava.StravaClient()
