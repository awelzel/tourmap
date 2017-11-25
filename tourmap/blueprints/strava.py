"""
Strava OAUTH flow hacked together.
"""
import logging
from urllib.parse import urlunparse

import dateutil.parser
from flask import Blueprint, redirect, request, url_for, render_template

from tourmap.utils.strava import StravaClient
from tourmap import database

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
        result = strava_client.exchange_token(request.args["code"])
        print(result)
        athlete = result["athlete"]
        state = request.args.get("state")
        if state and state in ["CONNECT"]:
            app.logger.info("INITIAL CONNECT!")
            user = database.User(
                strava_id=athlete["id"],
                email=athlete.get("email"),
                firstname=athlete.get("firstname"),
                lastname=athlete.get("lastname")
            )
            database.db.session.add(user)
            try:
                database.db.session.commit()
            except database.IntegrityError:
                database.db.session.rollback()

                # XXX: Should probably update changes!
                user = database.User.query.filter_by(strava_id=athlete["id"]).one()

            # Update the token
            token = database.Token.query.filter_by(user_id=user.id).one_or_none()
            if not token:
                token = database.Token(user_id=user.id)

            token.access_token = result["access_token"]
            database.db.session.add(token)
            try:
                database.db.session.commit()
            except database.IntegrityError as e:
                database.db.session.rollback()

        # XXX: Probably want to redirect so the URL does not look as bad...
        return render_template("strava/hello.html", firstname=user.firstname)

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

    @strava.route("/proxy/<int:user_id>/activities")
    def list_rides(user_id):
        user = database.User.query.get_or_404(user_id)
        token = database.Token.query.filter_by(user_id=user.id).one_or_none()
        if token is None:
            abort(404)


        page = int(request.args.get("page")) if "page" in request.args else None
        activities = strava_client.activities(token=token.access_token, page=page)
        import pprint
        pprint.pprint(activities[0])
        cleaned_activities = []
        for a in activities:
            ca = {
                "name": a["name"],
                "distance": round(a["distance"] / 1000.0, 2),
                "date": dateutil.parser.parse(a["start_date_local"]).date(),
            }
            cleaned_activities.append(ca)

        return render_template("strava/activities.html", user=user, activities=cleaned_activities)

    return strava
