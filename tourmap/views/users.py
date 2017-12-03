from flask import Blueprint, render_template, abort, request, current_app, redirect, url_for, flash
from flask_login import current_user, login_required

from tourmap.views.tours import TourForm

from tourmap import database

def create_user_tours_blueprint(app):
    """
    A blueprint designated to handle /users/<user_hashid>/tours/ stuff

    Note, this needs to be registerd with an url_prefix that contains
    a single variable part <user_hashid>.

        # Register under url_prefix with variable part...
        app.register_blueprint(blueprint, url_prefix="/users/<user_hashid>")

    """
    bp = Blueprint("user_tours", __name__)
    @bp.record
    def check_url_prefix(state):
        """
        Upon registering this blueprint we check for an url_prefix that
        contains a <user_hashid> variable. Crash hard otherwise...
        """
        if "<user_hashid>" not in state.url_prefix:
            raise RuntimeError("<user_hashid> not in url_prefix")

    @bp.route("/tours/new")
    @login_required
    def new_tour(user_hashid):
        user = database.User.get_by_hashid(user_hashid)
        if user is None:
            abort(404)


        if user != current_user:
            abort(403)

        return render_template("tours/new.html", form=TourForm(formdata=None), user=user)

    @bp.route("/tours", methods=["POST"])
    @login_required
    def create_tour(user_hashid):
        tour_exists_errors = ["A tour with this name already exists."]
        user = database.User.get_by_hashid(user_hashid)
        if user is None:
            abort(404)

        if user != current_user:
            abort(403)

        form = TourForm()
        if form.validate_on_submit():
            tour = database.Tour(user=user)
            form.populate_obj(tour)
            database.db.session.add(tour)
            try:
                database.db.session.commit()
                return redirect(url_for("user_tours.tour", user_hashid=user_hashid,
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

    @bp.route("/tours/<tour_hashid>")
    def tour(user_hashid, tour_hashid):
        """
        This returns the big map, visible for anyone.
        """
        user = database.User.get_by_hashid(user_hashid)
        tour = database.Tour.get_by_hashid(tour_hashid)

        if user is None or tour is None or tour.user.id != user.id:
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
                    "photos": src.photos.get_photos(256),
                }
                activities.append(a)

        return render_template("tours/tour.html",
                               user=user, tour=tour,
                               activities=activities)

    @bp.route("/tours/<tour_hashid>/delete", methods=["POST"])
    @login_required
    def delete(user_hashid, tour_hashid):
        """
        We do not bother with DELETE requests, because browsers do
        not support them anyhow. Further, we redirect to the users
        page for no good reason but to make it simpler...
        """
        user = database.User.get_by_hashid(user_hashid)
        tour = database.Tour.get_by_hashid(tour_hashid)
        if user is None or tour is None or tour.user.id != user.id:
            abort(404)

        if user != current_user:
            abort(403)

        database.db.session.delete(tour)
        database.db.session.commit()

        return redirect(url_for("users.user", user_hashid=user.hashid))

    return bp




def create_user_blueprint(app):
    bp = Blueprint("users", __name__)

    @bp.route("/")
    def index():
        return render_template("users/index.html",
                               users=database.User.query.all())

    @bp.route("/<user_hashid>")
    def user(user_hashid):
        user = database.User.get_by_hashid(user_hashid)
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

    @bp.route("/<user_hashid>/activities")
    def user_activities(user_hashid):
        user = database.User.get_by_hashid(user_hashid)
        return render_template("users/activities.html",
                               user=user,
                               activities=user.activities)

    return bp
