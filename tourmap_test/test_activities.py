import tourmap_test

from tourmap.resources import db


class TestActivities(tourmap_test.TestCase):

    def _get_app_config(self):
        config = super()._get_app_config()
        config["LOGIN_DISABLED"] = True
        return config

    def setUp(self):
        super().setUp()
        db.session.add_all([self.user1, self.user2, self.tour1,
                            self.activity1, self.activity2])
        db.session.commit()

        # Set the user_id into the session. This implies that for each
        # of the tests, we are logged in...
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1.hashid

    def test_all_activities(self):
        url = "/users/{}/activities".format(self.user1.hashid)
        response = self.client.get(url)
        response.assertStatusCode(200)
        response.assertDataContains(b"Temperature")

    def test_all_activities_different_user_403(self):
        url = "/users/{}/activities".format(self.user2.hashid)
        response = self.client.get(url)
        response.assertStatusCode(403)

    def test_activity_1_gpxroute(self):
        url = "/users/{}/activities/{}/summary_gpx".format(self.user1.hashid, self.activity1.hashid)
        response = self.client.get(url)
        response.assertStatusCode(200)
        self.assertIn("application/gpx+xml", response.headers["Content-Type"])
        self.assertIn(b"trkseg", response.data)
        self.assertIn(b"97.96637", response.data)
        self.assertIn("attachment; filename=20171018_Activity_1_of_User_1.gpx",
                      response.headers["Content-Disposition"])

    def test_activity_1_gpxroute_different_user(self):
        url = "/users/{}/activities/{}/summary_gpx".format(self.user2.hashid, self.activity2.hashid)
        response = self.client.get(url)
        response.assertStatusCode(200)
        self.assertIn("application/gpx+xml", response.headers["Content-Type"])
        self.assertIn(b"trkseg", response.data)
        self.assertIn(b"97.9444", response.data)
        self.assertIn("attachment; filename=20160926_Activity_2_of_User_2.gpx",
                      response.headers["Content-Disposition"])
