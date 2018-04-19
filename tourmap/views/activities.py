from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from tourmap.models import Activity, User
from tourmap.utils import activities_to_gpx, flask_attachment_response


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

        return render_template("users/activities.html",
                               user=user,
                               activities=user.activities)

    @bp.route("/activities/<activity_hashid>/summary_gpx")
    def summary_gpx(user_hashid, activity_hashid):
        """
        Allow downloading a low resolution GPX file of this activity.
        """
        user = User.get_by_hashid(user_hashid)
        activity = Activity.get_by_hashid(activity_hashid)
        if user is None or activity is None or activity.user.id != user.id:
            abort(404)

        gpx = activities_to_gpx([activity])
        date = activity.start_date_local.strftime("%Y%m%d ")
        name = activity.name[:30].strip()  # Hard-coded...
        return flask_attachment_response(
            data=gpx,
            mimetype="application/gpx+xml",
            filename=".".join([date + name, "gpx"])
        )

    return bp
