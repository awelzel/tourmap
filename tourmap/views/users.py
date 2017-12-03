from flask import Blueprint, render_template, abort, request, current_app, redirect, url_for, flash
from flask_login import current_user

from tourmap.views.tours import TourForm

from tourmap import database

def create_blueprint(app):
    bp = Blueprint("users", __name__)

    @bp.route("/<user_hashid>/tours/new")
    def new_tour(user_hashid):
        user = database.User.get_by_hashid(user_hashid)
        if user is None:
            abort(404)
        return render_template("tours/new.html", form=TourForm(formdata=None), user=user)

    @bp.route("/<user_hashid>/tours", methods=["POST"])
    def create_tour(user_hashid):
        tour_exists_errors = ["A tour with this name already exists."]
        user = database.User.get_by_hashid(user_hashid)
        if user is None:
            abort(404)

        form = TourForm()
        if form.validate_on_submit():
            tour = database.Tour(user=user)
            form.populate_obj(tour)
            database.db.session.add(tour)
            try:
                database.db.session.commit()
                return redirect(url_for("users.tour", user_hashid=user_hashid,
                                        tour_hashid=tour.hashid), code=303)
            except database.IntegrityError:
                database.db.session.rollback()
                form.name.errors = tour_exists_errors
                form.errors["name"] = form.name.errors

        # We have a user, and maybe a valid tourname, inform the user
        # if this tour exists already...
        if not form.name.errors:
            tour = (database.Tour.query
                    .filter_by(
                        user=user,
                        name=form.name.data
                    ).one_or_none())
            if tour:
                form.name.errors = tour_exists_errors
                form.errors["name"] = form.name.errors


        return render_template("tours/new.html", form=form, user=user)

    @bp.route("/<user_hashid>/tours/<tour_hashid>")
    def tour(user_hashid, tour_hashid):
        """
        This returns the big map
        """
        user = database.User.get_by_hashid(user_hashid)
        tour = database.Tour.get_by_hashid(tour_hashid)

        if user is None or tour is None:
            abort(404)

        if (tour.user.id != user.id):
            app.logger.warning("Got request for mismatched user/tour")
            abort(404)

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
        return render_template("tours/tour.html",
                               user=user, tour=tour,
                               activities=activities)

    @bp.route("/")
    def index():
        return render_template("users/index.html",
                               users=database.User.query.all())

    @bp.route("/<hashid>")
    def user(hashid):
        user = database.User.get_by_hashid(hashid)
        limit = int(request.args.get("limit", 13))
        if user is None:
            app.logger.warning("Failed user lookup")
            abort(404)

        recent_activities = (database.Activity.query
                             .filter_by(user=user)
                             .order_by(database.Activity.start_date.desc())
                             .limit(limit)
                             .all())
        return render_template("users/user.html",
                               user=user, tours=user.tours,
                               recent_activities=recent_activities)

    @bp.route("/<hashid>/activities")
    def user_activities(hashid):
        user = database.User.get_by_hashid(hashid)
        return render_template("users/activities.html",
                               user=user,
                               activities=user.activities)

    return bp
