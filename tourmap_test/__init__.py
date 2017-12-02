import logging
import unittest

import flask
import flask.wrappers


import tourmap
from tourmap.database import db

logger = logging.getLogger(__name__)

TEST_CONFIG = {
        # "DATABASE_URL": "sqlite://test.db",
        "DATABASE_URL": "postgresql:///tourmap_test",
        "STRAVA_CLIENT_ID": "-1",
        "STRAVA_CLIENT_SECRET": "TEST",
        "TESTING": True,
        "SECRET_KEY": "TEST",
        "WTF_CSRF_ENABLED": False,
        "STRAVA_CLIENT_BASE_URL": "http://localhost:33",
        # "SQLALCHEMY_ECHO": True,
}


class TestableResponse(flask.wrappers.Response):

    def assertStatusCode(self, status_code):
        if self.status_code != status_code:
            msg = "status_code {} != {}".format(self.status_code, status_code)
            raise AssertionError(msg)

    def assertDataContains(self, s):
        if s not in self.data:
            raise AssertionError("'{}' not found in data".format(s))


class TestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logger.info("Creating database tables...")
        app = tourmap.create_app(config=TEST_CONFIG)
        with app.app_context():
            db.drop_all()
            db.create_all()

        # Monkey patch the response class to provide some helpers
        cls.flask_response_class = flask.Flask.response_class
        flask.Flask.response_class = TestableResponse

    @classmethod
    def tearDownClass(cls):
        flask.Flask.response_class = cls.flask_response_class

    def _get_app_config(self):
        return dict(TEST_CONFIG)

    def _create_app(self):
        return tourmap.create_app(config=self._get_app_config())

    def setUp(self):
        super().setUp()
        self.app = self._create_app()
        # Push an app context...
        self.app.app_context().push()
        self.client = self.app.test_client()
        self.assertIsNotNone(self.app)


        # Wipe all test tables...
        for t in reversed(db.metadata.sorted_tables):
            db.session.execute(t.delete())
        db.session.commit()

    def tearDown(self):
        super().setUp()
        try:
            db.session.rollback()
        except Exception as e:
            logger.warning("rollback in tearDown failed: %s", repr(e))

        # This does not work?
        # self.app.app_context().pop()
