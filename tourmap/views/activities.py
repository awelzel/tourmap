from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from tourmap.models import User


def create_user_activities_blueprint(app):
    bp = Blueprint("user_activities", __name__)

    @bp.record
    def check_url_prefix(state):
        """
        Upon registering this blueprint we check for an url_prefix that
        contains a <user_hashid> variable. Crash hard otherwise...
        """
        if "<user_hashid>" not in state.url_prefix:
            raise RuntimeError("<user_hashid> not in url_prefix")

    @bp.route("/activities")
    @login_required
    def activities(user_hashid):
        user = User.get_by_hashid(user_hashid)
        if user is None:
            abort(404)

        if user != current_user:
            abort(403)

        user = User.get_by_hashid(user_hashid)
        return render_template("users/activities.html",
                               user=user,
                               activities=user.activities)

    @bp.route("/activities/<activity_hashid>")
    def activity(user_hashid, activity_hashid):
        return "activity {}".format(activity_hashid)

    return bp
