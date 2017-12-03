"""
Strava OAUTH flow hacked together.

XXX: the manual strava_client  extensions hack sucks.
"""
from urllib.parse import urlunparse

import dateutil.parser
from flask import Blueprint, redirect, request, url_for, render_template, abort, current_app, flash
import flask_login

import tourmap.utils
import tourmap.utils.strava
from tourmap import database


def create_blueprint(app):
    bp = Blueprint("strava", __name__)

    # XXX: This works only with a single thread or bad stuff might happen.
    # Check Flask-Plugins and pooling...
    __strava_client = tourmap.utils.strava.StravaClient.from_env(environ=app.config)
    app.extensions["strava_client"] = __strava_client

    @bp.route("/login")
    def login():
        """
        Just the Connect with Strava template.
        """
        return render_template("strava/login.html")

    @bp.route("/logout")
    def logout():
        """
        Do a logout.
        """
        flask_login.logout_user()
        return redirect(url_for("index"))

    @bp.route("/callback")
    def callback():
        """
        XXX: Needs some serious error checking!
        XXX: This should really be a controller and not in a view...
        XXX: The strava client is not thread safe!
        """
        strava_client = current_app.extensions["strava_client"]

        if "error" in request.args:
            msg = "Connect with Strava failed: {!r}".format(request.args["error"])
            current_app.logger.warning(msg)
            flash(msg, category="error")
            return redirect(url_for("strava.login"))

        state = request.args.get("state")
        if not state or state.lower() not in ["connect"]:
            msg = "Connect with Strava failed (state was {!r})".format(state)
            current_app.logger.warning(msg)
            flash(msg, category="error")
            return redirect(url_for("strava.login"))
        try:
            result = strava_client.exchange_token(request.args["code"])
        except tourmap.utils.strava.StravaBadRequest as e:
            msg = "Connect with Strava failed: {!r}".format(e.errors)
            current_app.logger.error(msg)
            flash(msg, category="error")
            return redirect(url_for("strava.login"))

        athlete = result["athlete"]

        # Now work on this user!
        new_user = False
        user = database.User.query.filter_by(strava_id=athlete["id"]).one_or_none()
        if user is None:
            current_app.logger.info("New User!")
            user = database.User(strava_id=athlete["id"])
            new_user = True

        # Update this user object...
        user.email = athlete.get("email")
        user.firstname = athlete.get("firstname"),
        user.lastname = athlete.get("lastname")
        user.country = athlete.get("country")

        database.db.session.add(user)
        try:
            database.db.session.commit()
        except database.IntegrityError as e:
            # Now, this can happen if someone tries to sign-up the
            # same account at the same time. But than he can just
            # retry...
            current_app.logger.exception("User %s: %s", user, e)
            database.db.session.rollback()
            abort(500)

        # Update the token
        token = database.Token.query.filter_by(user_id=user.id).one_or_none()
        if not token:
            token = database.Token(user_id=user.id)

        if result["access_token"] != token.access_token:
            current_app.logger.info("Setting token for %s", user)
            token.access_token = result["access_token"]
            database.db.session.add(token)

        try:
            database.db.session.commit()
        except database.IntegrityError as e:
            database.db.session.rollback()

        # At this point we can be somewhat sure the user has a Strava
        # account and that is good enough for us to log him in.
        current_app.logger.info("%s just logged in!", user)
        flask_login.login_user(tourmap.utils.UserProxy(user))

        if new_user:
            flash("Successfully connected with Strava. Thanks!", category="success")
            flash("Fetching your activities in the background, "
                  "just refresh this page until they show up ;-)", category="info")

        # Not sure this is working properly... If we got here through a
        # redirect it should go back to the original page.
        try:
            return tourmap.utils.redirect_back("users.user", hashid=user.hashid)
        except Exception as e:
            current_app.logger.exception("Redirect exception... %s", e)
            raise

    @bp.route("/authorize")
    def authorize():
        """
        Redirect the user to Strava asking to authorize our app.
        """
        app.logger.info("Strava authorize call!")

        # XXX: This may break behind a proxy, or maybe not?
        components = (request.scheme, request.host, url_for("strava.callback"), None, None, None)
        redirect_uri = urlunparse(components)
        strava_client = current_app.extensions["strava_client"]
        return redirect(strava_client.authorize_redirect_url(
            redirect_uri=redirect_uri,
            scope=None,
            state="CONNECT",
            approval_prompt="auto"
        ))

    @bp.route("/proxy/<int:user_id>/activities")
    def activities(user_id):
        user = database.User.query.get_or_404(user_id)
        token = database.Token.query.filter_by(user_id=user.id).one_or_none()
        if token is None:
            abort(404)

        page = int(request.args.get("page")) if "page" in request.args else None

        try:
            strava_client = current_app.extensions["strava_client"]
            activities = strava_client.activities(token=token.access_token, page=page)
        except tourmap.utils.strava.StravaTimeout:
            app.logger.warning("Strava timeout...")
            abort(504)

        cleaned_activities = []
        for a in activities:
            ca = {
                "name": a["name"],
                "distance": round(a["distance"] / 1000.0, 2),
                "date": dateutil.parser.parse(a["start_date_local"]).date(),
            }
            cleaned_activities.append(ca)

        return render_template("strava/activities.html", user=user, activities=cleaned_activities)
    return bp
