"""
For simplicity, also define the models here.
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    strava_id = db.Column(db.Integer, unique=True, nullable=False)
    firstname = db.Column(db.String(80), nullable=True)
    lastname = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), nullable=True)

class Token(db.Model):
    __tablename__ = "tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    access_token = db.Column(db.String(64), nullable=False)

def resetdb():
    db.drop_all()
    db.create_all()
