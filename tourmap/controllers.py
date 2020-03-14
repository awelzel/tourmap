import logging

from flask import current_app, url_for
from tourmap.utils import meters_to_distance_str, seconds_to_readable_interval


logger = logging.getLogger(__name__)

MAPBOX_ATTRIBUTION = (
    'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, '
    '<a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, '
    'Imagery &copy <a href="http://mapbox.com">Mapbox</a>'
)


class TourController(object):

    def _pdict(self, p):
        return {
            "url": p["url"],
            "height": p["height"],
            "width": p["width"],
        }

    def _prepare_photos(self, activity):
        """
        Create a list of activities to be displayed by the UI.
        """
        result = []

        if not activity.photos:
            return result

        photos = activity.photos.get_photos()
        keys = list(photos.keys())
        if not keys:
            return result

        if len(keys) != 2:
            logger.warning("Got weird sizes %s for %s", repr(keys), activity)

        large = max(keys)
        small = min(keys)
        large_dict = {p["unique_id"]: self._pdict(p) for p in photos[large]}
        result = []
        for p in photos[small]:
            pdict = self._pdict(p)
            pdict["large"] = large_dict[p["unique_id"]]
            pdict["caption"] = p.get("caption")
            result.append(pdict)
        return result

    def prepare_activities_for_map(self, tour):
        """
        Prepare activity data to be displayed on a map.
        """
        activities = []
        total_distance = 0
        total_elevation_gain = 0
        total_moving_time = 0
        for a in tour.activities:
            latlngs = list(a.latlngs)
            if not latlngs:
                continue

            photos = self._prepare_photos(a)
            activities.append({
                "name": a.name,
                "strava_id": str(a.strava_id),
                "date": a.start_date_local.date().isoformat(),
                "distance_str": a.distance_str,
                "elapsed_time_str": a.elapsed_time_str,
                "moving_time_str": a.moving_time_str,
                "strava_link": a.strava_link,
                "summary_gpx_link": url_for("user_activities.summary_gpx",
                                            user_hashid=a.user.hashid,
                                            activity_hashid=a.hashid),
                "latlngs": latlngs,
                "photos": photos,
            })
            total_distance += (a.distance or 0)
            total_elevation_gain += (a.total_elevation_gain or 0)
            total_moving_time += (a.moving_time or 0)

        return {
            "activities": activities,
            "totals": {
                "distance_str": meters_to_distance_str(total_distance),
                "moving_time_str": seconds_to_readable_interval(total_moving_time),
                "elevation_gain_str": "{:.1f} m".format(total_elevation_gain),
            }
        }

    def _find_bounds(self, prepared_activities):
        """
        Helper to find corner1 and corner2 values

        TODO: Put this into prepare_activities_for_map() and store it there.
        """
        lat_min, lat_max = (90, -90)
        lng_min, lng_max = (180, -180)
        for a in prepared_activities:
            if not a["latlngs"]:
                continue

            latlngs = a["latlngs"]
            lat_min = min(lat_min, min([ll[0] for ll in latlngs]))
            lat_max = max(lat_max, max([ll[0] for ll in latlngs]))
            lng_min = min(lng_min, min([ll[1] for ll in latlngs]))
            lng_max = max(lng_max, max([ll[1] for ll in latlngs]))

        return [(lat_min, lng_min), (lat_max, lng_max)]

    def get_map_settings(self, tour, prepared_activities):
        result = {}

        mapbox_url = ("https://api.mapbox.com/styles/v1/{id}"
                      "/tiles/{z}/{x}/{y}?access_token={access_token}")
        tile_layer_id = "mapbox/streets-v11"
        polyline_color = tour.polyline_color or "red"
        polyline_weight = tour.polyline_weight or 5
        marker_positioning = tour.marker_positioning or "end"
        marker_enable_clusters = True if tour.marker_enable_clusters else False

        result["tile_layer"] = {
            "provider": "mapbox",
            "url_template": mapbox_url,
            "options": {
                "access_token": current_app.config["MAPBOX_ACCESS_TOKEN"],
                "max_zoom": 18,
                "attribution": MAPBOX_ATTRIBUTION,
                "id": tile_layer_id,
            }
        }
        corner1, corner2 = self._find_bounds(prepared_activities)
        result["bounds"] = {
            "corner1": corner1,
            "corner2": corner2,
        }

        result["markers"] = {
            "positioning": marker_positioning,
            "enable_clusters": marker_enable_clusters,
        }

        # Compute max bounds as percentage of the difference and some
        # other heuristics, cough...
        max_wiggle = 0.10
        lat_wiggle = max(abs(corner1[0] - corner2[0]) * max_wiggle, 3.0)
        lng_wiggle = max(abs(corner1[1] - corner2[1]) * max_wiggle, 3.0)
        result["max_bounds"] = {
            "corner1": (corner1[0] - lat_wiggle, corner1[1] - lng_wiggle),
            "corner2": (corner2[0] + lat_wiggle, corner2[1] + lng_wiggle),
        }

        result["polyline"] = {
            "options": {
                "color": polyline_color,
                "weight": polyline_weight,
            }
        }

        result["links"] = {
            "summary_gpx_link": url_for("user_tours.summary_gpx",
                                        user_hashid=tour.user.hashid,
                                        tour_hashid=tour.hashid),
        }

        result["totals"] = {
            "distance_str": "0 km",
            "moving_time_str": "0 d",
        }
        return result
