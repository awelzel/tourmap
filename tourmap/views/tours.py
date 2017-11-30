from flask import Blueprint, render_template, abort, request, current_app, redirect, url_for


from tourmap.database import db
from tourmap.models import User, Tour

class TourController(object):

    def create(self, user_hashid, data):
        # Do Flask-WTF if not too complicated...
        # import IPython
        # IPython.embed()
        user = User.get_by_hashid(user_hashid)
        if user is None:
            abort(404)
        tour = Tour(user=user, name="XXX")
        db.session.add(tour)
        db.session.commit()
        return tour

def create_blueprint(app):
    bp = Blueprint("tours", __name__)

    # We want to match /tours as well, so strict_slashes=False is required.
    @bp.route("/", strict_slashes=False)
    def index():
        status_code = 200
        if request.method == "POST":
            tour = TourController().create(request.form)


        return render_template("tours/index.html", tours=Tour.query.all())


    @bp.route("/<hashid>")
    def tour(hashid):
        tour = Tour.get_by_hashid(hashid)
        if tour is None:
            current_app.logger.info("Not found: %s", hashid)
            abort(404)
        return render_template("tours/tour.html", user=tour.user, tour=tour)


    @bp.route("/<hashid>/map")
    def tour_map(hashid):
        tour = Tour.get_by_hashid(hashid)
        if tour is None:
            abort(404)
        user = tour.user

        activities = []
        for src in tour.activities:
            latlngs = list(src.latlngs)
            if latlngs:
                a = {
                    "name": src.name,  # MAKE HTML SAFE!
                    "date": src.start_date_local.date().isoformat(),
                    # "latlngs": latlngs,
                    # Naive sampling:
                    "latlngs": [latlngs[0]] + latlngs[8:-7:8] + [latlngs[-1]],
                    "photos": [
                        {
                            "url": p.url,
                            "width": p.width,
                            "height": p.height,
                        } for p in src.photos],
                }
                activities.append(a)

        return render_template("tours/tour_map.html",
                               user=user,
                               tour=tour,
                               activities=activities)
    return bp
