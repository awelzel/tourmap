"""
Test the /users/{}/tours/{} endpoints
"""
import json
import tourmap_test

from tourmap.models import User, Tour, ActivityPhotos
from tourmap.resources import db
from tourmap.controllers import TourController

class TestTourMap(tourmap_test.TestCase):

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

    def test_tour_controller_activity_with_images(self):
        result = self.tc.prepare_activities_for_map(self.tour1)
        self.assertEqual(1, len(result))
        a = result[0]
        self.assertIn("date", a)
        self.assertIn("photos", a)
        self.assertEqual(4, len(a["photos"]))
        self.assertIn("name", a)
        self.assertIn("latlngs", a)

    def test_tour_controller_activity_none_activity_photos(self):
        result = self.tc.prepare_activities_for_map(self.tour2)
        self.assertEqual(1, len(result))
        a = result[0]
        self.assertIn("date", a)
        self.assertIn("photos", a)
        self.assertEqual(0, len(a["photos"]))
        self.assertIn("name", a)
        self.assertIn("latlngs", a)

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
        result = self.tc.prepare_activities_for_map(self.tour2)
        self.assertEqual(1, len(result))
        a = result[0]
        self.assertIn("photos", a)
        self.assertEqual(0, len(a["photos"]))

    def test_tour_controller_activity_with_empty_activity_photos(self):
        prepared_activities = self.tc.prepare_activities_for_map(self.tour1)
        settings = self.tc.get_map_settings(self.tour1, prepared_activities)

        self.assertIn("tile_layer", settings)
        self.assertIn("polyline", settings)
        self.assertIn("bounds", settings)
        corner1, corner2 = settings["bounds"]["corner1"], settings["bounds"]["corner2"]
        self.assertLess(corner1, corner2)
