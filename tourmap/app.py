import os
import logging

import click

from flask import Flask, render_template, abort
# from flask.logging import default_handler

from flask_assets import Environment, Bundle

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


def _is_heroku_env(environ=None):
    environ = os.environ if not environ else environ
    return "DYNO" in environ and "heroku" in os.environ.get("PATH", "")


def configure_app(app):
    """
    Load the configuration for this app.

    Developing locally should be easy by using CONFIG_PYFILE and loading
    a local file. At the same time, we want to easily support heroku by
    just fetching everything from the environment.
    """
    app.config.from_object("tourmap.config.defaults")

    # Check the environment we are running in...
    if _is_heroku_env():
        logger.info("Detected heroku environment...")
        app.config.from_object("tourmap.config.heroku")
    else:
        config_pyfile = os.environ.get("CONFIG_PYFILE", "../config.py")
        logger.info("Reading local config %s...", config_pyfile)
        app.config.from_pyfile(config_pyfile)

    return app


def create_app():
    app = Flask(__name__)
    app = configure_app(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DATABASE_URL"]

    # Static assets...
    assets = Environment(app)
    bundles = {
        "base_js": Bundle(
            "js/lib/jquery-3.2.1.js",
            "js/lib/bootstrap-3.3.7.js",
            "js/tourmap.js",
            output="gen/tourmap.js"
        ),
        "css": Bundle(
            "css/lib/bootstrap-3.3.7.css",
            "css/lib/bootstrap-theme-3.3.7.css",
            "css/tourmap.css",
            output="gen/tourmap.css"
        ),
        "map_js": Bundle(
            "js/lib/leaflet-1.2.0.js",
            output="gen/map.js"
        ),
        "map_css": Bundle(
            "css/lib/leaflet-1.2.0.css",
            output="gen/map.css"
        ),
    }
    assets.register(bundles)

    # Database initialization
    from tourmap import database
    database.db.init_app(app)

    @app.cli.command()
    def createdb():
        database.db.metadata.create_all(
            bind=database.db.engine,
            checkfirst=True
        )

    @app.cli.command()
    @click.argument("user_id", type=click.INT)
    def sync_activities(user_id):
        from tourmap import tasks
        tasks.sync_activities(user_id, environ=app.config)

    @app.cli.command()
    def resetdb():
        database.db.drop_all()
        database.db.create_all()

    @app.cli.command()
    def iem():
        from tourmap.database import Activity, ActivityPhoto, Tour, User
        import IPython
        IPython.embed()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    # Install a view views...
    from tourmap.views import strava
    app.register_blueprint(strava.create_blueprint(app), url_prefix="/strava")
    from tourmap.views import users
    app.register_blueprint(users.create_blueprint(app), url_prefix="/users")

    return app

app = create_app()
