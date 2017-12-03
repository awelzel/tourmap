"""
Utils.
"""
import calendar
from urllib.parse import urlparse, urljoin

from flask import redirect, request, url_for

# is_safe_url should check if the url is safe for redirects.
# See http://flask.pocoo.org/snippets/62/ for an example.

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    if test_url.scheme not in ("http", "https"):
        return False
    return ref_url.netloc == test_url.netloc

def redirect_back(default_endpoint, next_candidate=None, redirect_kwargs=None,
                  **url_for_kwargs):
    redirect_kwargs = redirect_kwargs or {}

    for candidate in [next_candidate, request.args.get("next")]:
        if candidate and is_safe_url(candidate):
            return redirect(candidate, **redirect_kwargs)

    return redirect(url_for(default_endpoint, **url_for_kwargs), **redirect_kwargs)



import flask_login

class UserProxy(object):
    """
    Proxy for use with Flask-Login, so we do not pass around
    sqlalchemy model objects and do funny stuff with it.
    """
    def __init__(self, user, authenticated=True):
        self.__user = user
        self.__authenticated = True

    @property
    def url(self):
        return url_for("users.user", user_hashid=self.__user.hashid)

    @property
    def name_str(self):
        return self.__user.name_str

    def get_id(self):
        return self.__user.hashid

    @property
    def is_authenticated(self):
        """
        Could we add some timing stuff here?
        """
        return self.__authenticated

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __eq__(self, other):
        from tourmap.models import User
        """If the other thing has a hashid and looks like a User class, we compare them."""

        if isinstance(other, UserProxy):
            return self.get_id() == other.get_id()
        elif isinstance(other, User):
            return self.__user.hashid == other.hashid

        raise Exception("Bug? {!r} comparison with {!r}".format(self, other))

    def __ne__(self, other):
        return not self.__eq__(other)

def user_loader(hashid):
    from tourmap.models import User
    return UserProxy(User.get_by_hashid(hashid))


def dt2ts(dt):
    """
    Convert a datetime object into a Unix epoch value.
    """
    return calendar.timegm(dt.utctimetuple())
