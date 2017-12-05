from flask import Blueprint, render_template, abort, request, current_app, redirect, url_for, flash, escape
from flask_login import current_user, login_required

from tourmap.views.tours import TourForm

from tourmap import database
from tourmap.models import User, Tour, Activity
from tourmap.resources import db

from tourmap.controllers import TourController


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
        user = User.get_by_hashid(user_hashid)
        if user is None:
            abort(404)

        if user != current_user:
            abort(403)

        return render_template("tours/new.html", form=TourForm(formdata=None), user=user)

    @bp.route("/tours", methods=["POST"])
    @login_required
    def create(user_hashid):
        user = User.get_by_hashid(user_hashid)
        if user is None:
            abort(404)

        if user != current_user:
            abort(403)

        form = TourForm()
        if form.validate_on_submit():
            tour = Tour(user=user)
            form.populate_obj(tour)
            db.session.add(tour)
            try:
                db.session.commit()
                flash("Created tour '{}'".format(escape(tour.name)), category="success")
                return redirect(url_for("user_tours.tour", user_hashid=user_hashid,
                                        tour_hashid=tour.hashid), code=303)
            except database.IntegrityError:
                db.session.rollback()
                form.set_tour_exists()

        # We have a user, and maybe a valid tourname, but something
        # went wrong. Maybe the tour exists already?
        # if this tour exists already...
        if not form.name.errors:
            if Tour.query.filter_by(user=user, name=form.name.data).count():
                form.set_tour_exists()

        return render_template("tours/new.html", form=form, user=user)

    @bp.route("/tours/<tour_hashid>", methods=["GET", "POST"])
    def tour(user_hashid, tour_hashid):
        """
        This returns the big map, visible for anyone.
        """
        user = User.get_by_hashid(user_hashid)
        tour = Tour.get_by_hashid(tour_hashid)

        if user is None or tour is None or tour.user.id != user.id:
            abort(404)

        ctrl = TourController()
        if request.method == "POST":
            if user != current_user:  # make sure the right user edits the tour.
                abort(403)
            # Get the data from the original object, and from
            # the submitted form data.
            form = TourForm(obj=tour)
            if form.validate_on_submit():
                form.populate_obj(tour)
                try:
                    db.session.commit()
                    flash("Updated tour '{}'".format(escape(tour.name)), category="success")
                    return redirect(url_for("users.user", user_hashid=user_hashid))
                except database.IntegrityError:
                    db.session.rollback()
                    form.set_tour_exists()

            # Something went wrong with the tour...
            return render_template("tours/edit.html", tour=tour, form=form)

        # Default: Just show the map...
        prepared_activities = ctrl.prepare_activities_for_map(tour)
        map_settings = ctrl.get_map_settings(tour, prepared_activities)
        return render_template("tours/tour.html",
                               user=user, tour=tour,
                               activities=prepared_activities,
                               map_settings=map_settings)

    @bp.route("/tours/<tour_hashid>/delete", methods=["POST"])
    @login_required
    def delete(user_hashid, tour_hashid):
        """
        We do not bother with DELETE requests, because browsers do
        not support them anyhow. Further, we redirect to the users
        page for no good reason but to make it simpler...
        """
        user = User.get_by_hashid(user_hashid)
        tour = Tour.get_by_hashid(tour_hashid)
        if user is None or tour is None or tour.user.id != user.id:
            abort(404)

        if user != current_user:
            abort(403)

        db.session.delete(tour)
        db.session.commit()
        flash("Deleted tour '{}'".format(escape(tour.name)), category="success")
        return redirect(url_for("users.user", user_hashid=user.hashid))

    @bp.route("/tours/<tour_hashid>/edit", methods=["GET"])
    @login_required
    def edit(user_hashid, tour_hashid):
        """
        """
        user = User.get_by_hashid(user_hashid)
        tour = Tour.get_by_hashid(tour_hashid)
        if user is None or tour is None or tour.user.id != user.id:
            abort(404)

        if user != current_user:
            abort(403)

        form = TourForm(obj=tour)
        return render_template("tours/edit.html", tour=tour, form=form)

    return bp


def create_user_blueprint(app):
    bp = Blueprint("users", __name__)

    @bp.route("/")
    def index():
        return render_template("users/index.html",
                               users=User.query.all())

    @bp.route("/<user_hashid>")
    def user(user_hashid):
        user = User.get_by_hashid(user_hashid)
        if user is None:
            abort(404)

        recent_activities = (Activity.query
                             .filter_by(user=user)
                             .order_by(Activity.start_date.desc())
                             .limit(8)
                             .all())
        return render_template("users/user.html",
                               user=user, tours=user.tours,
                               recent_activities=recent_activities)

    @bp.route("/<user_hashid>/activities")
    def user_activities(user_hashid):
        user = User.get_by_hashid(user_hashid)
        if user is None:
            abort(404)

        if user != current_user:
            abort(403)

        user = User.get_by_hashid(user_hashid)
        return render_template("users/activities.html",
                               user=user,
                               activities=user.activities)

    return bp
