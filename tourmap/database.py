"""
For simplicity, also define the models here.
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError  # pylint: disable=unused-import
from sqlalchemy.schema import MetaData

from tourmap.resources import db
