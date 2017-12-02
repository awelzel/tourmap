import datetime
import uuid

import tourmap_test
from tourmap.models import User, Tour, PollState, Token
import tourmap.views.strava
from tourmap.database import db
from tourmap.utils.strava import StravaClient, StravaBadRequest
from tourmap.utils import dt2ts

from tourmap.tasks.strava_poller import StravaPoller

import unittest.mock

class StravaPollerTest(tourmap_test.TestCase):

    def setUp(self):
        super().setUp()
        self.session = db.session

        self.strava_client_mock = unittest.mock.Mock(spec=StravaClient)
        self.user = User(strava_id=123, email="auser@strava.com")
        self.buser = User(strava_id=124, email="buser@strava.com")
        self.cuser = User(strava_id=125, email="cuser@strava.com")
        self.tour = Tour(user=self.user, name="Simple Test Tour")
        self.token = Token(user=self.user, access_token=uuid.uuid4().hex)
        self.poll_state = PollState(user=self.user)
        self.session.add_all([self.user, self.buser, self.cuser, self.token, self.tour, self.poll_state])
        self.session.commit()

        def sc_constructor():
            return self.strava_client_mock
        self.strava_poller = StravaPoller(db.session, sc_constructor)

    def tearDown(self):
        super().tearDown()

    def test_get_states__no_states_in_db(self):
        self.session.delete(self.poll_state)
        self.session.commit()

        states = list(self.strava_poller._get_poll_states())
        self.assertEqual(0, len(states))

    def test_get_poll_states__single_state(self):
        states = list(self.strava_poller._get_poll_states())
        self.assertEqual(1, len(states))


    # def test_get_poll_states__exclude_submitted_states(self):
    #    self.strava_poller._add_submitted_state(self.poll_state)
    #    states = list(self.strava_poller._get_poll_states())
    #    self.assertEqual(0, len(states))

    def test_get_poll_states__full_fetch_completed_states(self):
        poll_state1 = PollState(user=self.buser, full_fetch_completed=True)
        poll_state2 = PollState(
            user=self.cuser,
            full_fetch_completed=True,
            last_fetch_completed_at=datetime.datetime.utcnow(), # This should not show up
        )
        self.session.add_all([poll_state1, poll_state2])
        self.session.commit()
        states = list(self.strava_poller._get_poll_states())
        self.assertEqual(2, len(states))


    def test_fetch_activities__full_fetch_mode(self):
        self.strava_client_mock.activities.return_value = []
        result = self.strava_poller.fetch_activities(self.user, self.token, self.poll_state)
        self.strava_client_mock.activities.assert_called_once_with(
            page=1,
            per_page=4,
            token=self.token.access_token
        )

        self.assertTrue(result["state_update"]["full_fetch_completed"])
        self.assertEqual(2, result["state_update"]["full_fetch_next_page"])
        self.assertEqual(4, result["state_update"]["full_fetch_per_page"])
        self.assertIsInstance(
            result["state_update"]["last_fetch_completed_at"],
            datetime.datetime
        )

    def test_fetch_activities__latest_fetch_mode(self):
        last_fetch_completed_at = datetime.datetime(2017, 7, 1)
        self.poll_state.last_fetch_completed_at = last_fetch_completed_at
        self.poll_state.full_fetch_completed = True
        self.session.add(self.poll_state)
        self.session.commit()

        expected_after_ts = dt2ts(last_fetch_completed_at - datetime.timedelta(days=14))
        self.strava_client_mock.activities.return_value = []
        result = self.strava_poller.fetch_activities(self.user, self.token, self.poll_state)
        self.strava_client_mock.activities.assert_called_once_with(
            after=expected_after_ts,
            token=self.token.access_token,
            per_page=50
        )

        self.assertTrue(result["state_update"]["total_fetches"])
        self.assertIsInstance(
            result["state_update"]["last_fetch_completed_at"],
            datetime.datetime
        )
