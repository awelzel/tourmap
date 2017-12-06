import os
import sys
"""
Configuration module for heroku. We simply set the whole environment
as attributes onto this module.
"""
this = sys.modules[__name__]

# Force an overwrite!
HASHIDS_SALT = None

__BOOLS = {
    "true": True,
    "yes": True,
    "false": False,
    "no": False,
}

# Copy the whole environment as attributes onto this module. Convert
# some possible bool values and integer values on the way.
for k, v in os.environ.items():
    if not k or k.startswith("_"):
        continue

    v = v.strip()
    if v.lower() in __BOOLS:
        v = __BOOLS[v.lower()]
    try:
        v = int(v)
    except ValueError:
        pass

    setattr(this, k, v)


# Check for some required settings...

if not HASHIDS_SALT:
    raise Exception("HASHIDS_SALT environment not set")
