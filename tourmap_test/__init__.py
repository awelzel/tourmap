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
}


class TestableResponse(flask.wrappers.Response):

    def assert_status_code(self, status_code):
        if self.status_code != status_code:
            msg = "status_code {} != {}".format(self.status_code, status_code)
            raise AssertionError(msg)


class TestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logger.info("Creating database tables...")
        app = tourmap.create_app(config=TEST_CONFIG)
        with app.app_context():
            db.drop_all()
            db.create_all()

        # Monkey patch...
        cls.flask_response_class = flask.Flask.response_class
        flask.Flask.response_class = TestableResponse

    @classmethod
    def tearDownClass(cls):
        flask.Flask.response_class = cls.flask_response_class

    def setUp(self):
        self.app = tourmap.create_app(config=TEST_CONFIG)
        self.client = self.app.test_client()
        self.assertIsNotNone(self.app)

        # Wipe all test tables...
        with self.app.app_context():
            for t in reversed(db.metadata.sorted_tables):
                db.session.execute(t.delete())
            db.session.commit()

    def tearDown(self):
        pass
