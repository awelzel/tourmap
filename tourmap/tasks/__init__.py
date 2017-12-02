import logging
import dateutil.parser

from tourmap import database
from tourmap.utils import strava

logger = logging.getLogger(__name__)

def sync_activities(user_id, environ=None):
    """
    If we want to re-implement this, strava_poller may need to be
    restructured such that the proper functions can be picked out.
    """
    user = database.User.query.filter_by(id=user_id).one()
    token = user.token.access_token
    client = strava.StravaClient.from_env(environ=environ)
    raise NotImplementedError()
