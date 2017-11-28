from flask import Blueprint, render_template, abort

from tourmap import database

def create_blueprint(app):
    bp = Blueprint("users", __name__)

    @bp.route("/<user_hashid>/tour/<tour_hashid>/map")
    def user_map(user_hashid, tour_hashid):
        user = database.User.get_by_hashid(user_hashid)
        unused = tour_hashid  # XXX: Make this work once Tour is implemented
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

    @bp.route("/")
    def index():
        return render_template("users/index.html",
                               users=database.User.query.all())

    @bp.route("/<hashid>")
    def user(hashid):
        user = database.User.get_by_hashid(hashid)
        if user is None:
            app.logger.warning("Failed user lookup")
            abort(404)
        return render_template("users/user.html", user=user)


    return bp
