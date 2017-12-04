from flask import Blueprint, render_template, abort, request, current_app, redirect, url_for

from tourmap.models import Tour

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
        """
        XXX: This will break when there are many many tours.
        """
        return render_template("tours/index.html", tours=Tour.query.all())

    return bp
