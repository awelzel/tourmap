from flask import Blueprint, render_template

from tourmap.models import Tour


def create_blueprint(app):
    bp = Blueprint("tours", __name__)

    # We want to match /tours as well, so strict_slashes=False is required.
    @bp.route("/", strict_slashes=False)
    def index():
        """
        XXX: This will break when there are many many tours.
        """
        tours = Tour.get_public_tours().order_by(Tour.id)
        return render_template("tours/index.html", tours=tours)
    return bp
