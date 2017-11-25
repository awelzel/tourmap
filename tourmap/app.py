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

    app.config["TEMPLATES_AUTO_RELOAD"] = True
    # app.config["DEBUG"] = True

    # Load some configuration from the environment here
    # XXX: Should be done more nicely:
    # http://flask.pocoo.org/docs/0.12/config/#development-production
    app.config["STRAVA_OAUTH_AUTHORIZE_URL"] = "https://www.strava.com/oauth/authorize"
    app.config["STRAVA_OAUTH_TOKEN_URL"] = "https://www.strava.com/oauth/token"
    app.config["STRAVA_CLIENT_ID"] = os.environ["STRAVA_CLIENT_ID"]
    app.config["STRAVA_CLIENT_SECRET"] = os.environ["STRAVA_CLIENT_SECRET"]

    app.config["HASHIDS_SALT"] = os.environ.get("HASHIDS_SALT", "UNCONFIGURED")
    app.config["HASHIDS_MIN_LENGTH"] = int(os.environ.get("HASHIDS_MIN_LENGTH", 8))

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
            output="gen/tourmap.css"),
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
        return render_template("users/index.html", users=database.User.query.all())

    @app.route("/users/<hashid>")
    def user(hashid):
        user = database.User.get_by_hashid(hashid)
        if user is None:
            abort(404)
        return render_template("users/user.html", user=user)

    @app.route("/users/<hashid>/map")
    def user_map(user_id):
        return render_template("users/map.html", users=users)

    @app.route("/test/db")
    def test_db():
        return repr(database.User.query.count())


    from tourmap.blueprints import strava
    app.register_blueprint(strava.create_blueprint(app), url_prefix="/strava")

    return app

app = create_app()
