"""
Test the /users/{}/tours/{} endpoints
"""
import json
import tourmap_test

from tourmap.models import User, Tour, ActivityPhotos
from tourmap.resources import db
from tourmap.controllers import TourController

class TestTour(tourmap_test.TestCase):

    def setUp(self):
        super().setUp()
        self.tc = TourController()
        db.session.add_all([self.user1, self.tour1, self.activity1, self.photos1])
        db.session.add_all([self.user2, self.tour2, self.activity2])
        db.session.commit()

    def test_tour1(self):
        url = "/users/{}/tours/{}".format(self.user1.hashid, self.tour1.hashid)
        response = self.client.get(url)
        response.assertStatusCode(200)

        # print(response.data.decode())

    def test_tour_controller_activity_with_images(self):
        result = self.tc.activities_for_map(self.user1, self.tour1)
        # import pprint
        # pprint.pprint(result)
        # XXX: Do something

    def test_tour_controller_activity_none_activity_photos(self):
        result = self.tc.activities_for_map(self.user2, self.tour2)
        # import pprint
        # pprint.pprint(result)
        # XXX: Do something

    def test_tour_controller_activity_with_empty_activity_photos(self):
        activity = self.activity2
        activity.id = self.activity2.id + 1
        activity.strava_id = self.activity2.strava_id + 1
        photos = ActivityPhotos(
            user=self.user2,
            activity=activity,
            data=json.dumps({})
        )
        db.session.add_all([activity, photos])
        db.session.commit()
        result = self.tc.activities_for_map(self.user2, self.tour2)
