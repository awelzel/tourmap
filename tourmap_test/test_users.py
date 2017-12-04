import tourmap_test

from tourmap.resources import db

class TestTour(tourmap_test.TestCase):

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

    def test_user_view_same_user(self):
        url = "/users/{}".format(self.user1.hashid)
        response = self.client.get(url)
        response.assertStatusCode(200)
        response.assertDataContains("{}/activities".format(self.user1.hashid).encode("ascii"))

    def test_user_view_different_user(self):
        url = "/users/{}".format(self.user2.hashid)
        response = self.client.get(url)
        response.assertStatusCode(200)
        response.assertNotDataContains("{}/activities".format(self.user2.hashid).encode("ascii"))

    def test_all_activities_different_user_403(self):
        url = "/users/{}/activities".format(self.user2.hashid)
        response = self.client.get(url)
        response.assertStatusCode(403)
