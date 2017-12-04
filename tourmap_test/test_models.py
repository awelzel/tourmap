import tourmap_test

from tourmap.models import Activity
from tourmap.resources import db

class TestModels(tourmap_test.TestCase):

    def setUp(self):
        super().setUp()
        db.session.add_all([self.user1, self.tour1])
        db.session.commit()

    def test_polyline_decode(self):
        self.assertEqual(7, len(self.activity1.latlngs))

    def test_activity_update_from_strava(self):
        activity_dict = self.get_test_data_from_json_file("test_activity1")
        activity = Activity(user=self.user1, strava_id=activity_dict["id"])
        activity.update_from_strava(activity_dict)
        db.session.add(activity)
        db.session.commit()
        self.assertEqual(1, Activity.query.count())

    def test_activity_update_twice(self):
        activity_dict = self.get_test_data_from_json_file("test_activity1")
        activity = Activity(user=self.user1, strava_id=activity_dict["id"])
        activity.update_from_strava(activity_dict)
        db.session.add(activity)
        db.session.commit()
        self.assertEqual(1, Activity.query.count())
        db.session.close()
        activity = Activity.query.first()
        activity.update_from_strava(activity_dict)
        db.session.commit()

        activity = Activity.query.first()
        activity_dict["name"] = "updated name"
        activity.update_from_strava(activity_dict)
        db.session.commit()

        activity = Activity.query.first()
        self.assertEqual("updated name", activity.name)
