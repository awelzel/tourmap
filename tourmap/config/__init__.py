import logging
import os

logger = logging.getLogger(__name__)

def _is_heroku_env(environ=None):
    environ = os.environ if not environ else environ
    return "DYNO" in environ and "heroku" in os.environ.get("PATH", "")


def configure_app(app, config=None):
    """
    Load the appropriate config and update app.config.

    Developing locally should be easy by using CONFIG_PYFILE and loading
    a local file. At the same time, we want to easily support heroku by
    just fetching everything from the environment. And for unit tests,
    the config options should be explictly passed in through.

    :param config: Update app.config from this dictionary and do not
        try any other methods of configuration.
    """
    app.config.from_object("tourmap.config.defaults")

    if config:
        app.config.update(config)
    elif _is_heroku_env():
        logger.info("Detected heroku environment...")
        app.config.from_object("tourmap.config.heroku")
    else:
        config_pyfile = os.environ.get("CONFIG_PYFILE", "../config.py")
        logger.info("Reading local config %s...", config_pyfile)
        app.config.from_pyfile(config_pyfile)

    # SQLAlchemy configuration...
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DATABASE_URL"]
    from tourmap.resources import db
    db.init_app(app)

    # StravaClient configuration
    from tourmap.resources import strava
    strava.init_app(app)

    # Check if the mapbox access token is available, else crash
    if "MAPBOX_ACCESS_TOKEN" not in app.config or not app.config["MAPBOX_ACCESS_TOKEN"]:
        raise RuntimeError("It appears MAPBOX_ACCESS_TOKEN was not set")

    return app
