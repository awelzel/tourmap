import tourmap_test

from tourmap.models import User, Tour
from tourmap.database import db

class TourTest(tourmap_test.TestCase):

    def setUp(self):
        super().setUp()

        self.user = User(strava_id=123, email="tester@strava.com")
        db.session.add(self.user)
        self.tour = Tour(user=self.user, name="Simple Test Tour")
        db.session.add(self.tour)
        db.session.commit()

    def tearDown(self):
        super().tearDown()

    def test_tours_index(self):
        response = self.client.get("/tours")
        response.assertStatusCode(200)

    def test_users_tours_get_new(self):
        response = self.client.get("/users/{}/tours/new".format(self.user.hashid))
        response.assertStatusCode(200)

    def test_users_create_tour_ok(self):
        form = {
            "name": "Another test tour",
            "start_date": "2017-11-30",
            "end_date": "2017-12-24",
            "description": "Small description about this tour.",
        }
        url = "/users/{}/tours".format(self.user.hashid)

        # Check that POST-REDIRECT-GET works properly.
        response = self.client.post(url, data=form)
        response.assertStatusCode(303)
        self.assertIn("Location", response.headers)
        tour_url = response.headers["Location"]
        response = self.client.get(tour_url)
        response.assertStatusCode(200)
        *_, tour_hashid = tour_url.rsplit("/")

        # Check that we have one tour more in the DB!
        self.assertEqual(2, len(Tour.query.all()))
        tour = Tour.get_by_hashid(tour_hashid)
        self.assertEqual("Another test tour", tour.name)
        self.assertEqual(self.user.id, tour.user_id)
        self.assertEqual("2017-11-30", tour.start_date_str)
        self.assertEqual("2017-12-24", tour.end_date_str)

    def test_users_create_tour_twice_same_name(self):
        form = {
            "name": "TOUR_NAME",
        }
        url = "/users/{}/tours".format(self.user.hashid)

        response = self.client.post(url, data=form)
        response.assertStatusCode(303)

        response = self.client.post(url, data=form)
        response.assertStatusCode(200)
        response.assertDataContains(b"already exists")

        # Only one new Tour!!
        self.assertEqual(2, len(Tour.query.all()))

    def test_users_create_tour_twice_same_name_extra_erros(self):
        form = {
            "name": "TOUR_NAME",
        }
        url = "/users/{}/tours".format(self.user.hashid)

        response = self.client.post(url, data=form)
        response.assertStatusCode(303)

        form = {
            "name": "TOUR_NAME",
            "start_date": "invalid date",
        }
        response = self.client.post(url, data=form)
        response.assertStatusCode(200)
        response.assertDataContains(b"already exists")
        response.assertDataContains(b"Not a valid date value")

        # Only one new Tour!!
        self.assertEqual(2, len(Tour.query.all()))

    def test_users_create_tour_twice_same_name_whitespace(self):
        form = {
            "name": "TOUR_NAME",
        }
        url = "/users/{}/tours".format(self.user.hashid)

        response = self.client.post(url, data=form)
        response.assertStatusCode(303)

        form = {
            "name": "  TOUR_NAME  ",
        }
        response = self.client.post(url, data=form)
        response.assertStatusCode(200)
        response.assertDataContains(b"already exists")

        # Only one new Tour!!
        self.assertEqual(2, len(Tour.query.all()))

    def test_create_tour_blank_name(self):
        form = {
            "name": "",
            "start_date": "2017-11-30",
            "end_date": "2017-12-24",
        }
        url = "/users/{}/tours".format(self.user.hashid)
        # other support: query_string, or file-like object
        response = self.client.post(url, data=form)
        response.assertStatusCode(200)

        # No new object!
        self.assertEqual(1, len(Tour.query.all()))

    def test_create_tour_bad_format(self):
        form = {
            "name": "TEST",
            "start_date": "TEST",
            "end_date": "TEST",
        }
        url = "/users/{}/tours".format(self.user.hashid)
        # other support: query_string, or file-like object
        response = self.client.post(url, data=form)
        response.assertStatusCode(200)

        # No new object!
        self.assertEqual(1, len(Tour.query.all()))
