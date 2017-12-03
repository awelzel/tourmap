import tourmap_test

from tourmap.database import db

class TestModels(tourmap_test.TestCase):

    def setUp(self):
        super().setUp()
        db.session.add_all([self.user1, self.tour1, self.activity1])
        db.session.commit()

    def test_polyline_decode(self):
        self.assertEqual(7, len(self.activity1.latlngs))
