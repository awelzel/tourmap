import logging
import os
import requests

from urllib.parse import urljoin, urlencode, urlunparse

logger = logging.getLogger(__name__)


class StravaError(Exception):
    pass


class Timeout(StravaError):
    pass


class StravaClient(object):

    BASE_URL = "https://www.strava.com"
    DEFAULT_TIMEOUT = (10, 10)

    @staticmethod
    def from_env(environ=os.environ):
        """
        Use some well known environment variables to initialize the client.
        """
        client_id = environ["STRAVA_CLIENT_ID"]
        client_secret = environ["STRAVA_CLIENT_SECRET"]
        base_url = environ.get("STRAVA_CLIENT_BASE_URL", StravaClient.BASE_URL)
        return StravaClient(client_id, client_secret, base_url=base_url)

    def __init__(self, client_id, client_secret, base_url=BASE_URL,
                 timeout=DEFAULT_TIMEOUT):
        self.__client_id = client_id
        self.__client_secret = client_secret

        self.__base_url = base_url
        self.__api_base_url = urljoin(self.__base_url, "/api/v3/")
        self.__timeout = timeout
        self.__session = requests.Session()

    def _post(self, url, *args, **kwargs):
        url = urljoin(self.__base_url, url)

        if "timeout" not in kwargs:
            kwargs["timeout"] = self.__timeout
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
        Create an URL representing the authorize endpoint on Strava's side.
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
        If successful, returns Athlete and token info.

                {'access_token': 'XXXXXXXXXXXXXXXXXXXXXXXXXXX53039e7735974',
                 'athlete': {'badge_type_id': 0,
                  'city': 'Hechingen',
                  'country': 'Germany',
                  'created_at': '2015-09-04T01:47:39Z',
                  'email': 'arne.welzel@gmail.com',
                  'firstname': 'Arne',
                  'follower': None,
                  'friend': None,
                  'id': 11176987,
                  ...
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

    def _api_v3_get_auth(self, token, url, *args, **kwargs):
        """
        Helper for an API v3 request.
        """
        url = urljoin(self.__api_base_url, url)
        headers = {
            "Authorization": "Bearer {}".format(token),
        }

        if "timeout" not in kwargs:
            kwargs["timeout"] = self.__timeout

        try:
            response = self.__session.get(
                url=url,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            raise Timeout()
        except requests.exceptions.RequestException as e:
            logger.exception("Error doing request...")
            raise StravaError(repr(e) + " --- " + response.text)
        except Exception as e:
            print("CRAP", str(e), type(e))
            raise

    def athlete(self, token):
        """
        Retrieve the with this token.
        """
        return self._api_v3_get_auth(token, "athlete")

    def activities(self, token, page=None, per_page=None):
        """
        List activities of authenticated user
        """
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page

        return self._api_v3_get_auth(token, "athlete/activities", params=params)

    def activity(self, token, id):
        """
        List activities of authenticated user
        """
        return self._api_v3_get_auth(token, "activities/{}".format(id))

    def activity_photos(self, token, id, size=None):
        params = {
            "photo_sources": True,
        }
        if size is not None:
            params["size"] = size
        url = "activities/{}/photos".format(id)
        return self._api_v3_get_auth(token, url, params=params)