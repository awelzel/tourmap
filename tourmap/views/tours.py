from flask import Blueprint, render_template, abort, request, current_app, redirect, url_for

from tourmap.models import Tour

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, BooleanField, SelectField
from wtforms.validators import DataRequired, Optional

class TourForm(FlaskForm):

    tour_exists_errors = ["A tour with this name already exists."]

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
    marker_positioning = SelectField(
        label="Marker Position",
        choices=[("end", "End"), ("middle", "Middle"), ("start", "Start")],
        default="end",
        validators=[Optional()]
    )
    marker_enable_clusters = BooleanField(
        label="Cluster Markers",
        false_values=["no", "false", "0"],
        default="no",
        validators=[Optional()]
    )
    polyline_color = SelectField(
        label="Line Color",
        choices=[
            ("red", "Red"),
            ("azure", "Azure"),
            ("gold", "Gold"),
            ("lightgreen", "Light Green"),
            ("blue", "Blue"),
            ("black", "Black"),
        ],
        validators=[Optional()]
    )

    def set_tour_exists(self):
        self.name.errors = self.tour_exists_errors
        self.errors["name"] = list(self.name.errors)


def create_blueprint(app):
    bp = Blueprint("tours", __name__)

    # We want to match /tours as well, so strict_slashes=False is required.
    @bp.route("/", strict_slashes=False)
    def index():
        """
        XXX: This will break when there are many many tours.
        """
        return render_template("tours/index.html", tours=Tour.query.all())

    return bp
