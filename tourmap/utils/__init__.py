"""
Utils.
"""
import calendar
from urllib.parse import urlparse, urljoin

import gpxpy.gpx

from dateutil.relativedelta import relativedelta
from flask import Response, redirect, request, url_for
from werkzeug.utils import secure_filename


def is_safe_url(target):
    """
    is_safe_url should check if the url is safe for redirects.
    See http://flask.pocoo.org/snippets/62/ for an example.
    """
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


class UserProxy(object):
    """
    Proxy for use with Flask-Login, so we do not pass around
    sqlalchemy model objects and do funny stuff with it.
    """
    def __init__(self, user):
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
        """
        If the other thing is a user class, we compare them based on the hashids.
        """
        from tourmap.models import User

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


def seconds_to_readable_interval(seconds):
    rd = relativedelta(seconds=seconds)

    result = "{:02}:{:02}".format(rd.minutes, rd.seconds)
    if rd.hours > 0:
        result = "{}h {}".format(rd.hours, result)
    if rd.days > 0:
        result = "{}d {}".format(rd.days, result)
    return result


def meters_to_distance_str(distance):
    """
    Cycling is all about kilometers! Only cars drive miles...
    """
    if distance is None:
        return ""

    suffix = "m"
    divisor = 1.0
    if distance > 1000.0:
        suffix = "km"
        divisor = 1000.0

    return "{:.1f} {}".format(distance / divisor, suffix)


def str2bool(s):
    """
    Convert a string to a bool.

    :returns: True if the string is either one of 1, true or yes, else False
    """
    assert isinstance(s, str), "{!r} not a string?".format(s)
    if s.strip().lower() in ["1", "true", "yes"]:
        return True
    return False


def activities_to_gpx(activities, creator="tourmapp"):
    """
    Create a GPX with one track for each activity.

    :returns: str representing the gpx file
    """
    gpx = gpxpy.gpx.GPX()
    gpx.creator = creator

    for activity in activities:
        track = gpxpy.gpx.GPXTrack(name=activity.name)
        track.link = activity.strava_link
        track.source = "based on strava summary polyline"
        gpx.tracks.append(track)
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)
        for lat, lng in activity.latlngs:
            segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lng))

    return gpx.to_xml()


def flask_attachment_response(data, mimetype, filename):
    """
    Create a response with a Content-Disposition header set to attachment.

    Note: filename is filtered through werkzeug.utils.secure_filename, the
    caller does not need to bother about whitespace/slashes/etc.
    """
    resp = Response(data, mimetype=mimetype)
    resp.headers.add("Content-Disposition", "attachment",
                     filename=secure_filename(filename))
    return resp
