import os
import logging

from flask import Flask, render_template
from flask_assets import Environment, Bundle

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

    @app.route("/")
    def index():
        return render_template("index.html")

    from tourmap.blueprints import strava
    app.register_blueprint(strava.create_blueprint(app), url_prefix="/strava")

    print("URL MAP")
    print(app.url_map)

    return app

app = create_app()
