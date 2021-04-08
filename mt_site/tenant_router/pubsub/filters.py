import os
from functools import wraps

from tenant_router.constants import constants


def uuid_filter(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        event = args[1]
        proc_uuid = event.data.get("proc_uuid", None)
        if proc_uuid != constants.PROC_UUID:
            print("running callbacks for ", os.getpid())
            return func(*args, **kwargs)

    return wrapper
