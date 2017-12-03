import tourmap_test

from tourmap.models import User, Tour
import tourmap.views.strava
from tourmap.database import db
from tourmap.utils.strava import StravaClient, StravaBadRequest

import unittest.mock

class StravaTest(tourmap_test.TestCase):

    def setUp(self):
        super().setUp()

        self.oauth_token_response_error = {
            "message":"Bad Request",
        }
        self.oauth_strava_id = 999999999999
        self.oauth_token_response_ok = {
            'access_token': 'e4805618ba385b97c22b0055c45deb40f80bc39a',
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
                "id": self.oauth_strava_id,
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

        # self.user = User(strava_id=123)
        # db.session.add(self.user)
        # self.tour = Tour(user=self.user, name="Simple Test Tour")
        # db.session.add(self.tour)
        # db.session.commit()

    def tearDown(self):
        super().tearDown()

    def test_strava_callback_no_code(self):
        query_string = {
                "state": "CONNECT",
        }
        response = self.client.get("/strava/callback", query_string=query_string)
        response.assertStatusCode(400)

    def test_strava_callback_valid(self):
        code = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
        query_string = {
                "code": code,
                "state": "CONNECT",
        }
        self.strava_client_mock.exchange_token.return_value = self.oauth_token_response_ok
        self.strava_client_mock.exchange_token(code)
        response = self.client.get("/strava/callback", query_string=query_string)
        response.assertStatusCode(302)

        self.assertEqual(1, User.query.count())
        user = User.query.first()
        self.assertEqual(self.oauth_strava_id, user.strava_id)
        self.assertEqual("FirstTest", user.firstname)
        self.assertEqual("LastTest", user.lastname)
        self.assertEqual("Germany", user.country)

        # Follow the redirect and check if flash is there...
        response = self.client.get(response.headers["Location"])
        response.assertStatusCode(200)
        response.assertDataContains(b"Successfully connected with Strava")


    def test_strava_callback_strava_returns_error(self):
        code = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
        query_string = {
                "code": code,
                "state": "CONNECT",
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
        response.assertStatusCode(302)

        # Follow redirect and check if flash is there...
        response = self.client.get(response.headers["Location"])
        response.assertStatusCode(200)
        response.assertDataContains(b"Connect with Strava failed")
