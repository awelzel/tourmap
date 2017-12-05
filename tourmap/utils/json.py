import json
import datetime


class DateTimeAwareJsonEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        return super().default(o)

def dumps(*args, **kwargs):
    kwargs.setdefault("cls", DateTimeAwareJsonEncoder)
    return json.dumps(*args, **kwargs)

def dump(*args, **kwargs):
    kwargs.setdefault("cls", DateTimeAwareJsonEncoder)
    return json.dump(*args, **kwargs)

def load(*args, **kwargs):
    return json.load(*args, **kwargs)

def loads(*args, **kwargs):
    return json.loads(*args, **kwargs)
