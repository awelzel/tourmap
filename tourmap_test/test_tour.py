import tourmap_test

from tourmap.models import User, Tour
from tourmap.database import db


class TourTest(tourmap_test.TestCase):

    def setUp(self):
        super().setUp()

        self.app.app_context().push()
        self.user = User(strava_id=123)
        db.session.add(self.user)
        self.tour = Tour(user=self.user, name="Simple Test Tour")
        db.session.add(self.tour)
        db.session.commit()

    def tearDown(self):
        # self.app.app_context().pop()
        pass

    def test_tours_index(self):
        response = self.client.get("/tours")
        response.assert_status_code(200)

    def test_create_tour_good(self):
        response = self.client.post("/users/{}/tours".format(self.user.hashid))
        response.assert_status_code(303)
        self.assertIn("Location", response.headers)
        response = self.client.get(response.headers["Location"])
        response.assert_status_code(200)
