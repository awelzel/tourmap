"""
Strava OAUTH flow hacked together.
"""
import logging
from urllib.parse import urlunparse

from flask import Blueprint, redirect, request, url_for, render_template

from tourmap.utils.strava import StravaClient

logger = logging.getLogger(__name__)


def create_blueprint(app):
    strava = Blueprint("strava", __name__)

    # XXX - this works only with a single thread!!! Check Flask-Plugins!
    client_id = app.config["STRAVA_CLIENT_ID"]
    client_secret = app.config["STRAVA_CLIENT_SECRET"]
    strava_client = StravaClient(client_id, client_secret)

    @strava.route("/callback")
    def callback():
        if "error" in request.args:
            return "ERROR: {}".format(request.args["error"])
        app.logger.info("Strava callback!")
        athlete = strava_client.exchange_token(request.args["code"])

        state = request.args.get("state")

        if state and state in ["CONNECT"]:
            app.logger.info("INITIAL CONNECT!")

        firstname = athlete["athlete"]["firstname"]

        # XXX: Probably want to redirect so the URL does not look as bad...
        return render_template("strava/hello.html", firstname=firstname)

    @strava.route("/authorize")
    def authorize():
        """
        Redirect the user to Strava asking to authorize our app.
        """
        app.logger.info("Strava authorize call!")

        # XXX: This may break behind a proxy, or maybe not?
        components = (request.scheme, request.host, url_for("strava.callback"), None, None, None)
        redirect_uri = urlunparse(components)
        return redirect(strava_client.authorize_redirect_url(redirect_uri, state="CONNECT"))

    return strava
