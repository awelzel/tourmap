import os
import logging

import click

from flask import Flask, render_template, abort
from flask_assets import Environment, Bundle

from flask_login import LoginManager

import tourmap.config
import tourmap.utils


logger = logging.getLogger(__name__)


def create_app(config=None):
    app = Flask(__name__)

    # Load default configuration that is with the application
    app = tourmap.config.configure_app(app, config=config)

    # Login manager stuff...
    login_manager = LoginManager()
    login_manager.user_loader(tourmap.utils.user_loader)
    login_manager.login_view = "strava.login"
    login_manager.init_app(app)

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


    # Install a view views...
    from tourmap.views import strava
    app.register_blueprint(strava.create_blueprint(app), url_prefix="/strava")
    from tourmap.views import users
    app.register_blueprint(users.create_user_blueprint(app), url_prefix="/users")
    app.register_blueprint(users.create_user_tours_blueprint(app), url_prefix="/users/<user_hashid>")
    from tourmap.views import tours
    app.register_blueprint(tours.create_blueprint(app), url_prefix="/tours")

    @app.after_request
    def add_cache_headers(response):
        # https://stackoverflow.com/a/2068407
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # HTTP 1.1.
        response.headers["Pragma"] = "no-cache" # HTTP 1.0.
        response.headers["Expires"] = "0" # Proxies.
        return response


    # Support a few more flask commands for convenience...
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
        from tourmap.database import db
        from tourmap.models import Activity, ActivityPhoto, Tour, User

        sc = app.extensions["strava_client"]
        import IPython
        IPython.embed()

    @app.cli.command()
    @click.option("--loglevel", default="info")
    def strava_poller(loglevel):
        from tourmap.database import db
        import tourmap.tasks.strava_poller
        from tourmap.utils.strava import StravaClient
        logging.basicConfig(level=getattr(logging, loglevel.upper()))
        sc = app.extensions["strava_client"]
        strava_poller = tourmap.tasks.strava_poller.StravaPoller(
            session=db.session,
            strava_client_constructor=lambda: StravaClient.from_env(environ=app.config)
        )
        try:
            strava_poller.run()
        except Exception as e:
            logger.exception("StravaPoller failed: %s", e)
            raise

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    return app
