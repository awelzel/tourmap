import os
import logging

import click

from flask import Flask, render_template, abort, request
from flask_assets import Environment, Bundle

from flask_login import LoginManager

import tourmap.config
import tourmap.utils


logger = logging.getLogger(__name__)


def create_app(config=None):
    app = Flask(__name__)

    # Load default configuration
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
            "node_modules/jquery/dist/jquery.js",
            "node_modules/bootstrap/dist/js/bootstrap.js",
            "js/tourmap.js",
            output="gen/tourmap.js"
        ),
        "css": Bundle(
            "node_modules/bootstrap/dist/css/bootstrap.css",
            "node_modules/bootstrap/dist/css/bootstrap-theme.css",
            "css/tourmap.css",
            output="gen/tourmap.css"
        ),
        "map_js": Bundle(
            "node_modules/leaflet/dist/leaflet.js",
            "node_modules/leaflet.markercluster/dist/leaflet.markercluster.js",
            output="gen/map.js"
        ),
        "map_css": Bundle(
            "node_modules/leaflet/dist/leaflet.css",
            "node_modules/leaflet.markercluster/dist/MarkerCluster.css",
            "node_modules/leaflet.markercluster/dist/MarkerCluster.Default.css",
            "css/tourmap.css",
            output="gen/map.css"
        ),
        "tourmap_leaflet_map_js": Bundle(
            "js/tourmap-leaflet-map.js",
            output="gen/tourmap-leaflet-map.js"
        ),
    }
    assets.register(bundles)


    # Install a few views...
    from tourmap.views import activities, index, strava, tours, users
    app.register_blueprint(activities.create_user_activities_blueprint(app),
                           url_prefix="/users/<user_hashid>")
    app.register_blueprint(index.create_blueprint(app))
    app.register_blueprint(strava.create_blueprint(app), url_prefix="/strava")
    app.register_blueprint(users.create_user_blueprint(app), url_prefix="/users")
    app.register_blueprint(users.create_user_tours_blueprint(app),
                           url_prefix="/users/<user_hashid>")
    app.register_blueprint(tours.create_blueprint(app), url_prefix="/tours")


    @app.after_request
    def add_cache_headers(response):
        """
        Make sure we cache static files, but nothing else.
        """
            # https://stackoverflow.com/a/2068407
        if not request.path.startswith(app.static_url_path):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # HTTP 1.1.
            response.headers["Pragma"] = "no-cache" # HTTP 1.0.
            response.headers["Expires"] = "0" # Proxies.

        return response


    # Support a few more flask commands
    @app.cli.command()
    def createdb():
        from tourmap.resources import db
        db.metadata.create_all(
            bind=db.engine,
            checkfirst=True
        )

    @app.cli.command()
    def resetdb():
        from tourmap.resources import db
        db.drop_all()
        db.create_all()

    @app.cli.command()
    def iem():
        from tourmap.resources import db, strava
        from tourmap.models import Activity, ActivityPhotos, Tour, User
        import IPython
        IPython.embed()

    @app.cli.command()
    @click.option("--loglevel", default=None)
    def strava_poller(loglevel):
        from tourmap.resources import db, strava
        from tourmap.tasks import strava_poller
        from tourmap.config import configure_logging

        if loglevel and app.config["LOG_LEVEL"].upper() != loglevel.upper():
            app.config["LOG_LEVEL"] = loglevel
            configure_logging(app)

        kwargs = strava_poller.StravaPoller.config_kwargs_from_env(environ=app.config)
        strava_poller = strava_poller.StravaPoller(
            session=db.session,
            strava_client_pool=strava._pool,
            **kwargs,
        )
        try:
            strava_poller.run()
        except Exception as e:
            logger.exception("StravaPoller failed: %s", e)
            raise

    return app
