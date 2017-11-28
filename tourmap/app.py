import os
import logging

import click

from flask import Flask, render_template, abort
# from flask.logging import default_handler

from flask_assets import Environment, Bundle

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


def create_app():
    app = Flask(__name__)

    # Config reading - load all defaults tourmap/defaults.py, then
    # override with settings in the file found through CONFIG_PYFILE,
    # or fallback to config.py
    app.config.from_object("tourmap.defaults")
    app.config.from_pyfile(os.environ.get("CONFIG_PYFILE", "../config.py"))

    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DATABASE_URL"]

    # Static assets...
    assets = Environment(app)
    bundles = {
        "base_js": Bundle(
            "js/lib/jquery-3.2.1.js",
            "js/lib/bootstrap-2.3.2.js",
            "js/tourmap.js",
            output="gen/tourmap.js"
        ),
        "css": Bundle(
            "css/lib/bootstrap-2.3.2.css",
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
        print(user_id)
        from tourmap import tasks
        tasks.sync_activities(user_id)

    @app.cli.command()
    def resetdb():
        database.db.drop_all()
        database.db.create_all()

    @app.cli.command()
    def iem():
        from tourmap import database
        import IPython
        IPython.embed()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/users")
    def user_index():
        return render_template("users/index.html",
                               users=database.User.query.all())

    @app.route("/users/<hashid>")
    def user(hashid):
        user = database.User.get_by_hashid(hashid)
        if user is None:
            abort(404)
        return render_template("users/user.html", user=user)

    @app.route("/users/<hashid>/map")
    def user_map(hashid):
        user = database.User.get_by_hashid(hashid)
        activities = []
        for src in user.activities:
            latlngs = list(src.latlngs)
            if latlngs:
                a = {
                    "name": src.name,  # MAKE HTML SAFE!
                    "date": src.start_date_local.date().isoformat(),
                    "latlngs": latlngs,
                    # Naive sampling:
                    # "latlngs": [latlngs[0]] + latlngs[8:-7:8] + [latlngs[-1]],
                    "photos": [p.url for p in src.photos],
                }
                activities.append(a)

        return render_template("users/map.html", user=user, activities=activities)

    from tourmap.views import strava
    app.register_blueprint(strava.create_blueprint(app), url_prefix="/strava")

    return app


app = create_app()
