import logging
logger = logging.getLogger(__name__)

class TourController(object):


    def _pdict(self, p):
        return {
            "url": p["url"],
            "height": p["height"],
            "width": p["width"],
        }

    def _prepare_photos(self, activity):
        """
        Create a list with entries:

        [
            {
                "url": ...
                "width": ...
                "height": ...
                "caption": ...
                "large": {
                    "url": ...
                    "width": ...
                    "height": ...
                }
            }
        ]
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


    def activities_for_map(self, user, tour):
        """
        Prepare activity data to be displayed on a map.

        # Naive sampling:
        # "latlngs": [latlngs[0]] + latlngs[8:-7:8] + [latlngs[-1]],
        """
        activities = []
        for a in tour.activities:
            latlngs = list(a.latlngs)
            if not latlngs:
                continue

            photos = self._prepare_photos(a)
            activities.append({
                "name": a.name,
                "date": a.start_date_local.date().isoformat(),
                "latlngs": latlngs,
                "photos": photos,
            })
        return activities
