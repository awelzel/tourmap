"""
Flask-Strava

Providing the StravaClient in the form of a flask extension to any application.
"""
import tourmap.utils.strava
from tourmap.utils.objpool import ObjectPool

from flask import _app_ctx_stack as stack, current_app

class StravaState(object):

    def __init__(self, cfn):
        self.pool = ObjectPool(cfn=cfn)


class StravaClient(object):

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        assert app.config["STRAVA_CLIENT_ID"], "STRAVA_CLIENT_ID not configured"
        assert app.config["STRAVA_CLIENT_SECRET"], "STRAVA_CLIENT_SECRET not configured"

        # This extension creates a pool of StravaClient objects
        def _make_strava_client():
            return tourmap.utils.strava.StravaClient.from_env(environ=app.config)

        app.extensions["strava_client"] = StravaState(_make_strava_client)

        # Register teardown function
        app.teardown_appcontext(self.teardown)

    def teardown(self, exception):
        ctx = stack.top
        if ctx is not None and hasattr(ctx, "strava_client"):
            self._pool.put(ctx.strava_client)
            delattr(ctx, "strava_client")

    @property
    def client(self):
        """
        Lazily get a StravaClient from the pool and set it on the context.
        """
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'strava_client'):
                ctx.strava_client = self._pool.get()
            return ctx.strava_client

    @property
    def _pool(self):
        """
        Return a refernce to the object pool used by the extension.
        """
        assert "strava_client" in current_app.extensions, (
            "Looks like the flask_strava extension was not initialized.")
        return current_app.extensions["strava_client"].pool
