import datetime
import json
import logging
import os
import os.path
import unittest

import flask
import flask.wrappers

import tourmap
from tourmap.models import User, Activity, ActivityPhotos, Tour
from tourmap.resources import db
from tourmap.utils import str2bool

from .data import db_photos1_dict

logger = logging.getLogger(__name__)

TEST_CONFIG = {
        "DATABASE_URL": "sqlite:///test.db",
        # "DATABASE_URL": "postgresql:///tourmap_test",
        "STRAVA_CLIENT_ID": "-1",
        "STRAVA_CLIENT_SECRET": "TEST",
        "HASHIDS_SALT": "TEST",
        "HASHIDS_MIN_LENGTH": 4,
        "TESTING": True,
        "SECRET_KEY": "TEST",
        "WTF_CSRF_ENABLED": False,
        "STRAVA_CLIENT_BASE_URL": "http://localhost:33",
        "SQLALCHEMY_ECHO": str2bool(os.environ.get("SQLALCHEMY_ECHO", "false")),
        "MAPBOX_ACCESS_TOKEN": "MAPBOXTESTTOKEN",
        "SERVER_NAME": "test.local",  # needed for url_for

        "LOG_LEVEL": "CRITICAL",
}


class TestableResponse(flask.wrappers.Response):

    def assertStatusCode(self, status_code):
        if self.status_code != status_code:
            msg = "status_code {} != {}".format(self.status_code, status_code)
            raise AssertionError(msg)

    def assertHTML(self):
        """
        Run the Python provided html parser over data and see if it crashed.
        """
        self.assertDataContains(b"<html>")
        self.assertDataContains(b"<head>")
        self.assertDataContains(b"<body>")

    def assertDataContains(self, s):
        if s not in self.data:
            raise AssertionError("{!r} not found in data".format(s))

    def assertNotDataContains(self, s):
        if s in self.data:
            raise AssertionError("{!r} found in data".format(s))

    def assertIsRedirect(self, code=None, location_contains=None):
        if code is not None:
            self.assertStatusCode(code)
        else:
            if not 300 <= self.status_code <= 310:
                msg = "{!r} is not a redirect code".format(self.status_code)
                raise AssertionError(msg)

        if "Location" not in self.headers:
            raise AssertionError("No Location header present")
        location = self.headers["Location"]
        if location_contains and location_contains not in location:
            raise AssertionError("{!r} not found in Location {!r}",
                                 location_contains, location)

    def followRedirect(self, client, *args, **kwargs):
        """
        Assert this response is a redirect and do a GET request to it.

        :returns: response of the next location...
        """
        self.assertIsRedirect()
        return client.get(self.headers["Location"], *args, **kwargs)


class TestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
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

        # Wipe all test tables...
        for t in reversed(db.metadata.sorted_tables):
            db.session.execute(t.delete())
        db.session.commit()

        # For reuse in tests, but not added to the db
        self.user1 = User(strava_id=123, email="first@strava.com")
        self.tour1 = Tour(user=self.user1, name="User1 Test Tour")
        self.user2 = User(strava_id=124, email="second@strava.com")
        self.tour2 = Tour(user=self.user2, name="User2 Test Tour", public=True)
        self.start_date1 = datetime.datetime(2017, 10, 18, 8, 30)
        self.start_date_local1 = datetime.datetime(2017, 10, 18, 10, 30)
        self.utc_offset1 = 7200
        self.distance1 = 19321
        self.moving_time1 = 3621
        self.elapsed_time1 = 5912
        self.activity1 = Activity(
            user=self.user1,
            strava_id=4321,
            type="Ride",
            name="Activity 1 of User 1",
            start_date=self.start_date1,
            start_date_local=self.start_date_local1,
            moving_time=self.moving_time1,
            elapsed_time=self.elapsed_time1,
            utc_offset=self.utc_offset1,
            summary_polyline="qpxtBkg}tQBhI_kArMka@kQshBbA_}AlZc`Boi@"
        )
        self.photos1 = ActivityPhotos(
            user=self.user1,
            activity=self.activity1,
            data=json.dumps(db_photos1_dict)
        )

        self.start_date2 = datetime.datetime(2016, 9, 26, 19, 27)
        self.start_date_local2 = datetime.datetime(2016, 9, 26, 15, 27)
        self.utc_offset2 = -14400
        self.distance2 = 10221
        self.moving_time2 = 9011
        self.elapsed_time2 = 10221
        self.activity2 = Activity(
            user=self.user2,
            strava_id=54321,
            type="Ride",
            name="Activity 2 of User 2",
            start_date=self.start_date2,
            start_date_local=self.start_date_local2,
            moving_time=self.moving_time2,
            elapsed_time=self.elapsed_time2,
            utc_offset=self.utc_offset2,
            summary_polyline="ui}qBwhwtQc]gOcGuP{HaEsXvHsXaP{n@oFygAcW"
        )

    def tearDown(self):
        super().setUp()
        try:
            db.session.rollback()
        except Exception as e:
            logger.warning("rollback in tearDown failed: %s", repr(e))

    def load_test_data(self, basename, ext):
        filename = os.path.extsep.join([basename, ext])
        path = os.path.join(__path__[0], "data", filename)
        return open(path, "r")

    def get_test_data_from_json_file(self, basename):
        with self.load_test_data(basename, "json") as fp:
            return json.load(fp)
