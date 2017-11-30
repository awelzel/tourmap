import os
import logging

import click

from flask import Flask, render_template, abort
from flask_assets import Environment, Bundle

import tourmap.config


logger = logging.getLogger(__name__)


def create_app(config=None):
    app = Flask(__name__)

    # Load default configuration that is with the application
    app = tourmap.config.configure_app(app, config=config)

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
    from tourmap.views import tours
    app.register_blueprint(tours.create_blueprint(app), url_prefix="/tours")

    return app
