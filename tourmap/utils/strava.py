"""
Very basic wrapper around the Strava API V3.
"""
import logging
import os
from urllib.parse import urljoin, urlencode

import requests


logger = logging.getLogger(__name__)


class StravaError(Exception):
    pass


class StravaBadRequest(StravaError):

    def __init__(self, status_code, message, errors):
        super().__init__(status_code, message, errors)
        self.status_code = status_code
        self.message = message
        self.errors = errors


class StravaTimeout(StravaError):
    pass


class InvalidAccessToken(StravaError):
    """Issues with the provided access token."""
    def __init__(self, message, error_data):
        super().__init__(message, error_data)
        self.message = message
        self.error_data = error_data

class InvalidAthleteAccessToken(InvalidAccessToken):
    """Raised when an Athletes access token was invalid."""
    pass


class StravaClient(object):

    BASE_URL = "https://www.strava.com"
    DEFAULT_TIMEOUT = (10, 10)

    @staticmethod
    def from_env(environ=None):
        """
        Use some well known environment variables to initialize the client.
        """
        environ = environ or os.environ
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
        response = self.__session.post(url, *args, **kwargs)
        try:
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if 400 <= status_code <= 499:
                try:
                    data = e.response.json()
                    raise StravaBadRequest(status_code,
                                           data.get("message"),
                                           data.get("errors", []))
                except ValueError:
                    pass
            logger.exception("HTTPError doing request status=%s", status_code)
            raise StravaError(repr(e) + " --- " + response.text)
        except requests.exceptions.RequestException as e:
            logger.exception("Error doing request...")
            raise StravaError(repr(e) + " --- " + response.text)

    def authorize_redirect_url(self, redirect_uri, scope=None,
                               approval_prompt="auto", state=None):
        """
        Create an URL representing the authorize endpoint on Strava's side.
        """
        if approval_prompt and approval_prompt not in ["auto", "force"]:
            raise ValueError("Bad approval_prompt value")
        url = urljoin(self.__base_url, "oauth/authorize")
        args = {
            "client_id": self.__client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "approval_prompt": approval_prompt,
        }
        if scope:
            args["scope"] = scope
        if state:
            args["state"] = state

        return "?".join([url, urlencode(args)])

    def exchange_token(self, code):
        """
        If successful, returns Strava's athlete and token info as dict.
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

    def _handle_4xx(self, response):
        data = response.json()
        msg = data.get("message")
        error_data = {
            "response_data": data,
            "response_headers": dict(response.headers),
        }
        status_code = response.status_code
        errors = data.get("errors", [])
        for e in errors:
            if e.get("code") == "invalid" and e.get("field") == "access_token":
                if e.get("resource") == "Athlete":
                    raise InvalidAthleteAccessToken(msg, error_data)

                raise InvalidAccessToken(msg, error_data)

    def _api_v3_get_auth(self, token, url, **kwargs):
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
            raise StravaTimeout()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if 400 <= status_code <= 499:
                self._handle_4xx(e.response)
                logger.warning("_handle_4xx() fall through...")

            # _handle_4xx() should have raised something more
            # appropriate, or else we fallback to a default raise.
            raise StravaError(repr(e) + " --- " + response.text)

        except requests.exceptions.RequestException as e:
            raise StravaError(repr(e) + " --- " + response.text)

    def athlete(self, token):
        """
        Retrieve the with this token.
        """
        return self._api_v3_get_auth(token, "athlete")

    def stats(self, token, id):
        """
        Retrieve the stats of the given athlete.
        """
        return self._api_v3_get_auth(token, "athletes/{}/stats".format(id))

    def activities(self, token, before=None, after=None, page=None, per_page=None):
        """
        List activities of authenticated user
        """
        params = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before

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
