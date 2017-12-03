import random
import uuid
import unittest.mock

from tourmap.models import User, Tour
from tourmap.utils.strava import StravaClient, StravaBadRequest

import tourmap_test


class StravaTest(tourmap_test.TestCase):

    def setUp(self):
        super().setUp()

        self.oauth_token_response_error = {
            "message":"Bad Request",
        }
        self.strava_id = random.randint(1, 100000000)
        self.test_code = uuid.uuid4().hex
        self.test_token = uuid.uuid4().hex

        self.oauth_token_response_ok = {
            'access_token': self.test_token,
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
        self.app.extensions["strava_client"] = self.strava_client_mock

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
        self.strava_client_mock.exchange_token.return_value = self.oauth_token_response_ok
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
        self.strava_client_mock.exchange_token.return_value = self.oauth_token_response_ok
        response = self.client.get("/strava/callback", query_string=query_string)
        self.strava_client_mock.exchange_token.assert_called_with(self.test_code)

        response.assertIsRedirect(302, "/users/")
        response = response.followRedirect(self.client)
        response.assertDataContains(b"Successfully connected with Strava")

        self.assertEqual(1, User.query.count())
        user = User.query.first()
        self.assertEqual(user.token.access_token, self.test_token)

        self.assertIsNotNone(user.poll_state)
        self.assertIs(False, user.poll_state.full_fetch_completed)

    def test_strava_callback__creates_default_tour(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT",
        }
        self.strava_client_mock.exchange_token.return_value = self.oauth_token_response_ok
        response = self.client.get("/strava/callback", query_string=query_string)
        self.strava_client_mock.exchange_token.assert_called_with(self.test_code)
        response.assertIsRedirect(302, "/users/")

        self.assertEqual(1, Tour.query.count())
        tour = Tour.query.first()
        self.assertEqual("All Activities", tour.name)
        user = User.query.first()
        self.assertEqual(user.id, tour.user_id)

    def test_strava_callback__honors_next_in_state(self):
        query_string = {
                "code": self.test_code,
                "state": "state=CONNECT&next=%2Ftours%2F",
        }
        self.strava_client_mock.exchange_token.return_value = self.oauth_token_response_ok
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
        self.strava_client_mock.exchange_token.return_value = self.oauth_token_response_ok
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
                    "resource":"Application",
                    "field":"client_id",
                    "code":"invalid",
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
        response.assertDataContains(b"Connect with Strava failed")
