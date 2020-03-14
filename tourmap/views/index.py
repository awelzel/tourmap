from flask import Blueprint, render_template

from tourmap.models import Tour


def create_blueprint(app):
    bp = Blueprint("index", __name__)

    @bp.route("/", strict_slashes=False)
    def index():
        # Ugly hack ;-)
        example_tour = Tour.query.filter_by(
            name="destination uncertain",
            user_id=1
        ).one_or_none()
        return render_template("index.html", example_tour=example_tour)

    return bp
