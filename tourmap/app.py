from flask import Flask, render_template
from flask_assets import Environment, Bundle


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


assets = Environment(app)

bundles = {
    "base_js": Bundle(
        "js/lib/jquery-3.2.1.js",
        "js/lib/bootstrap-2.3.2.js",
        "js/tourmap.js",
        output="gen/tourmap.js"
    ),
    "css": Bundle(
        "css/lib/bootstrap-2.3.2.css",
        "css/tourmap.css",
        output="gen/tourmap.css"),
}
assets.register(bundles)

@app.route("/")
def index():
    return render_template("index.html")
