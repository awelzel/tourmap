import tourmap_test

from tourmap.models import User, Tour
from tourmap.resources import db

class TestTour(tourmap_test.TestCase):

    def _get_app_config(self):
        config = super()._get_app_config()
        config["LOGIN_DISABLED"] = True
        return config

    def setUp(self):
        super().setUp()
        db.session.add_all([self.user1, self.user2, self.tour1])
        db.session.commit()

        # Set the user_id into the session. This implies that for each
        # of the tests, we are logged in...
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1.hashid

    def test_tours_index(self):
        response = self.client.get("/tours")
        response.assertStatusCode(200)

    def test_users_tours_get_new_anonymous(self):
        # Wipe the session!
        with self.client.session_transaction() as sess:
            sess.pop("user_id")
        response = self.client.get("/users/{}/tours/new".format(self.user1.hashid))
        response.assertStatusCode(403)

    def test_users_tours_get_new(self):
        response = self.client.get("/users/{}/tours/new".format(self.user1.hashid))
        response.assertStatusCode(200)

    def test_users_create_tour_ok(self):
        form = {
            "name": "Another test tour",
            "start_date": "2017-11-30",
            "end_date": "2017-12-24",
            "description": "Small description about this tour.",
        }
        url = "/users/{}/tours".format(self.user1.hashid)

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
        self.assertEqual(self.user1.id, tour.user_id)
        self.assertEqual("2017-11-30", tour.start_date_str)
        self.assertEqual("2017-12-24", tour.end_date_str)

    def test_users_create_tour_twice_same_name(self):
        form = {
            "name": "TOUR_NAME",
        }
        url = "/users/{}/tours".format(self.user1.hashid)

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
        url = "/users/{}/tours".format(self.user1.hashid)

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
        url = "/users/{}/tours".format(self.user1.hashid)

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
        url = "/users/{}/tours".format(self.user1.hashid)
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
        url = "/users/{}/tours".format(self.user1.hashid)
        # other support: query_string, or file-like object
        response = self.client.post(url, data=form)
        response.assertStatusCode(200)

        # No new object!
        self.assertEqual(1, len(Tour.query.all()))

    def test_delete_tour_http_delete(self):
        url = "/users/{}/tours/{}/delete".format(self.user1.hashid, self.tour1.hashid)
        response = self.client.post(url)
        response.assertIsRedirect(302, "/users/{}".format(self.user1.hashid))

    def test_delete_tour_http_delete_twice(self):
        url = "/users/{}/tours/{}/delete".format(self.user1.hashid, self.tour1.hashid)
        response = self.client.post(url)
        response.assertIsRedirect(302, "/users/{}".format(self.user1.hashid))
        response = self.client.post(url)
        response.assertStatusCode(404)

        self.assertFalse(Tour.query.count())

    def test_delete_tour_of_wrong_user(self):
        db.session.add(self.tour2)
        db.session.commit()

        url = "/users/{}/tours/{}/delete".format(self.user2.hashid, self.tour2.hashid)
        response = self.client.post(url)
        response.assertStatusCode(403)

        self.assertEqual(2, Tour.query.count())
