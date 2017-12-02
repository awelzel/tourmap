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
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

def redirect_back(endpoint, redirect_kwargs=None, **url_for_kwargs):
    target = request.form.get("next")
    if not target or not is_safe_url(target):
        target = url_for(endpoint, **url_for_kwargs)

    redirect_kwargs = redirect_kwargs or {}
    return redirect(target, **redirect_kwargs)


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
        return url_for("users.user", hashid=self.__user.hashid)

    @property
    def name_str(self):
        return " ".join(filter(None, [self.__user.firstname, self.__user.lastname]))

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
