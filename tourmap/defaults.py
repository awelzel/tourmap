"""
# Set a few default options that are needed.
"""
# How to access Strava
STRAVA_OAUTH_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_OAUTH_TOKEN_URL = "https://www.strava.com/oauth/token"

# Real deployments should change this
HASHIDS_SALT = "INSECURE"
HASHIDS_MIN_LENGTH = 8

# New default for Flask-SQLAlchemy
SQLALCHEMY_TRACK_MODIFICATIONS = False
