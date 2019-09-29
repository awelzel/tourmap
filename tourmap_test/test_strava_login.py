import datetime
import random
import time
import uuid
import unittest.mock

from tourmap.models import User, Token, Tour
from tourmap.utils.strava import StravaClient, StravaBadRequest

import tourmap.flask_strava as flask_strava

import tourmap_test


class StravaLoginTest(tourmap_test.TestCase):

    def setUp(self):
        super().setUp()

        self.oauth_token_response_error = {
            "message": "Bad Request",
        }
        self.strava_id = random.randint(1, 100000000)
        self.test_code = uuid.uuid4().hex
        self.test_token = uuid.uuid4().hex
        self.test_refresh_token = uuid.uuid4().hex
        self.test_expires_at = int(time.time()) + 21600
        self.test_expires_at_dt = datetime.datetime.utcfromtimestamp(self.test_expires_at)

        self.oauth_token_response_ok = {
            'access_token': self.test_token,
            'expires_at': self.test_expires_at,
            'expires_in': 21600,
            'refresh_token': self.test_refresh_token,
            'token_type': 'Bearer',
            'athlete': {
                "friend": None,
                "resource_state": 2,
                "firstname": "FirstTest",
                "email": "no.spam@gmail.com",
                "sex": "M",
                "follower": None,
                "updated_at": "2017-11-29T17:13:12Z",
                "lastname": "LastTest",
                "username": "testuser",
                "id": self.strava_id,
                "premium": False,
                "country": "Germany",
                "profile_medium": "https://dgalywyr863hv.cloudfront.net/pictures/athletes/11176987/4136348/3/medium.jpg",
                "created_at": "2015-09-04T01:47:39Z",
                "badge_type_id": 0,
                "state": "Baden-Württemberg",
                "profile": "https://dgalywyr863hv.cloudfront.net/pictures/athletes/11176987/4136348/3/large.jpg"
            }
        }
        assert "strava_client" in self.app.extensions
        self.strava_client_mock = unittest.mock.Mock(spec=StravaClient)
        # Patch the extension so it returns the Mock object to us.
        self.app.extensions["strava_client"] = flask_strava.StravaState(
            cfn=lambda: self.strava_client_mock
        )
        self.strava_client_mock.exchange_token.return_value = self.oauth_token_response_ok

    def test_strava_callback_no_code(self):
        query_string = {
                "state": "state=CONNECT",
        }
        response = self.client.get("/strava/callback", query_string=query_string)
        response.assertStatusCode(400)

    def test_strava_callback_valid__creates_user(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT",
        }
        response = self.client.get("/strava/callback", query_string=query_string)
        self.strava_client_mock.exchange_token.assert_called_with(self.test_code)
        response.assertStatusCode(302)

        self.assertEqual(1, User.query.count())
        user = User.query.first()
        self.assertEqual(self.strava_id, user.strava_id)
        self.assertEqual("FirstTest", user.firstname)
        self.assertEqual("LastTest", user.lastname)
        self.assertEqual("Germany", user.country)

        # Check if we are redirected to the user
        self.assertIn("/users/{}".format(user.hashid), response.headers["Location"])

        # Follow the redirect and check if flash is there...
        response = self.client.get(response.headers["Location"])
        response.assertStatusCode(200)
        response.assertDataContains(b"Successfully connected with Strava")

    def test_strava_callback__creates_token_and_poll_state(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT",
        }
        response = self.client.get("/strava/callback", query_string=query_string)
        self.strava_client_mock.exchange_token.assert_called_with(self.test_code)

        response.assertIsRedirect(302, "/users/")
        response = response.followRedirect(self.client)
        response.assertDataContains(b"Successfully connected with Strava")

        self.assertEqual(1, User.query.count())
        user = User.query.first()
        self.assertEqual(user.token.access_token, self.test_token)
        self.assertEqual(user.token.refresh_token, self.test_refresh_token)
        self.assertEqual(user.token.expires_at, self.test_expires_at_dt)

        self.assertIsNotNone(user.poll_state)
        self.assertIs(False, user.poll_state.full_fetch_completed)

    def test_strava_callback__creates_default_tour(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT",
        }
        response = self.client.get("/strava/callback", query_string=query_string)
        self.strava_client_mock.exchange_token.assert_called_with(self.test_code)
        response.assertIsRedirect(302, "/users/")

        self.assertEqual(1, Tour.query.count())
        tour = Tour.query.first()
        self.assertEqual("All Activities", tour.name)
        self.assertTrue(tour.marker_enable_clusters)
        self.assertEqual("middle", tour.marker_positioning)
        user = User.query.first()
        self.assertEqual(user.id, tour.user_id)

    def test_strava_callback__honors_next_in_state(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT&next=%2Ftours%2F",
        }
        response = self.client.get("/strava/callback", query_string=query_string)
        self.strava_client_mock.exchange_token.assert_called_with(self.test_code)

        response.assertIsRedirect(302, "/tours/")
        response = response.followRedirect(self.client)
        response.assertDataContains(b"Successfully connected with Strava")

    def test_strava_callback__logging_in_twice(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT",
        }
        response = self.client.get("/strava/callback", query_string=query_string)

        response.assertIsRedirect(302, "/users/")
        response = response.followRedirect(self.client)
        response.assertDataContains(b"Successfully connected with Strava")

        response = self.client.get("/strava/callback", query_string=query_string)
        response.assertIsRedirect(302, "/users/")
        response = response.followRedirect(self.client)
        response.assertNotDataContains(b"Successfully connected with Strava")

    def test_strava_callback_strava_returns_error(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT",
        }

        self.strava_client_mock.exchange_token.side_effect = StravaBadRequest(
            status_code=400,
            message="Bad Request",
            errors=[
                {
                    "resource": "Application",
                    "field": "client_id",
                    "code": "invalid",
                }
            ]
        )
        response = self.client.get("/strava/callback", query_string=query_string)
        self.strava_client_mock.exchange_token.assert_called_with(self.test_code)
        response.assertIsRedirect(302, location_contains="/strava/login")

        # Follow redirect and check if flash is there informing about the error
        response = self.client.get(response.headers["Location"])
        response.assertStatusCode(200)
        response.assertDataContains(b"alert-danger")
        response.assertDataContains(b"Token exchange with Strava failed")

    def test_strava_callback__clears_error_and_starts(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT",
        }
        response = self.client.get("/strava/callback", query_string=query_string)
        self.strava_client_mock.exchange_token.assert_called_with(self.test_code)
        response.assertIsRedirect(302, "/users/")

        user = User.query.first()
        user.poll_state.set_error("Fake poll state error", {"fake": "fake"})
        user.poll_state.stop()
        tourmap_test.db.session.commit()
        tourmap_test.db.session.expunge_all()

        response = self.client.get("/strava/callback", query_string=query_string)
        self.strava_client_mock.exchange_token.assert_called_with(self.test_code)
        response.assertIsRedirect(302, "/users/")

        user = User.query.first()
        self.assertFalse(user.poll_state.error_happened)
        self.assertFalse(user.poll_state.error_message)
        self.assertFalse(user.poll_state.stopped)

    def test_strava_callback__no_email(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT",
        }
        del self.oauth_token_response_ok["athlete"]["email"]
        response = self.client.get("/strava/callback", query_string=query_string)
        self.strava_client_mock.exchange_token.assert_called_with(self.test_code)
        response.assertIsRedirect(302, "/users/")

        user = User.query.first()
        self.assertIsNone(user.email)

    def test_strava_callback__expires_at_in_past(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT",
        }
        self.oauth_token_response_ok["expires_at"] = int(time.time()) - 3600

        with self.assertRaisesRegex(ValueError, "expires_at in past"):
            self.client.get("/strava/callback", query_string=query_string)

        user = User.query.first()
        self.assertEqual(self.strava_id, user.strava_id)
        token = Token.query.first()
        self.assertIsNone(token)

    def test_strava_callback__missing_refresh_token(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT",
        }
        del self.oauth_token_response_ok["refresh_token"]

        with self.assertRaisesRegex(KeyError, "refresh_token"):
            self.client.get("/strava/callback", query_string=query_string)
        self.assertIsNone(User.query.first())
