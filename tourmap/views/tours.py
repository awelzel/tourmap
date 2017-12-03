from flask import Blueprint, render_template, abort, request, current_app, redirect, url_for

from tourmap.database import db
from tourmap.models import User, Tour

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField
from wtforms.validators import DataRequired, Optional

class TourForm(FlaskForm):
    name = StringField(
        label="Name",
        render_kw={"placeholder": "Name"},
        validators=[DataRequired()],
        filters=[lambda data: data.strip() if data else data]  # Strip whitespace!
    )
    description = TextAreaField(
        label="Description",
        render_kw={"placeholder": "Optional description"},
        validators=[Optional()]
    )

    start_date = DateField(
        label="Start Date",
        render_kw={"placeholder": "Optional start date"},
        validators=[Optional()]
    )
    end_date = DateField(
        label="End Date",
        render_kw={"placeholder": "Optional end date"},
        validators=[Optional()]
    )


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

    return bp
