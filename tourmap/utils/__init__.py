"""
Utils.
"""
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


class UserProxy(object):
    """
    Proxy for use with Flask-Login, so we do not pass around
    sqlalchemy model objects and do funny stuff with it.
    """
    def __init__(self, user, authenticated=True):
        self.__user = user
        self.__authenticated = True

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

    def get_id(self):
        return self.__user.hashid

def user_loader(hashid):
    from tourmap.models import User
    return UserProxy(User.get_by_hashid(hashid))
