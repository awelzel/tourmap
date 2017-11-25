import logging
import requests
from urllib.parse import urljoin, urlencode, urlunparse

logger = logging.getLogger(__name__)

class StravaError(Exception):
    pass

class StravaClient(object):

    def __init__(self, client_id, client_secret, base_url="https://www.strava.com"):
        self.__client_id = client_id
        self.__client_secret = client_secret

        self.__base_url = base_url
        self.__session = requests.Session()

    def _post(self, url, *args, **kwargs):
        url = urljoin(self.__base_url, url)
        print("URL", url)
        response = self.__session.post(url, *args, **kwargs)
        try:
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.exception("Error doing request...")
            raise StravaError(repr(e) + " --- " + response.text)

    def authorize_redirect_url(self, redirect_uri, state=None):
        """
        """
        url = urljoin(self.__base_url, "oauth/authorize")
        args = {
            "client_id": self.__client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "approval_prompt": "auto",  # could be force
            "scope": "view_private",
            "state": state,
        }
        return "?".join([url, urlencode(args)])

    def exchange_token(self, code):
        """
        If successful, returns Athlete information.

                {'access_token': '5621ddc668f3dcefc319a095fed53039e7735974',
                 'athlete': {'badge_type_id': 0,
                  'city': 'Hechingen',
                  'country': 'Germany',
                  'created_at': '2015-09-04T01:47:39Z',
                  'email': 'arne.welzel@gmail.com',
                  'firstname': 'Arne',
                  'follower': None,
                  'friend': None,
                  'id': 11176987,
                  'lastname': 'Welzel',
                  'premium': False,
                  'profile': 'https://dgalywyr863hv.cloudfront.net/pictures/athletes/11176987/4136348/3/large.jpg',
                  'profile_medium': 'https://dgalywyr863hv.cloudfront.net/pictures/athletes/11176987/4136348/3/medium.jpg',
                  'resource_state': 2,
                  'sex': 'M',
                  'state': 'Baden-Württemberg',
                  'updated_at': '2017-11-23T00:00:06Z',
                  'username': 'arnewelzel'},
                 'token_type': 'Bearer'}
                        """
        response = self._post(
            url="oauth/token",
            data={
                "client_id": self.__client_id,
                "client_secret": self.__client_secret,
                "code": code,
            }
        )
        return response.json()

