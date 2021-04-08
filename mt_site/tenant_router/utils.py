
def singleton(cls):
    return cls()


def join_keys(*keys, separator='_'):
    return "{0}".format(separator).join(
        keys
    )


def remove_prefix(s: str, prefix: str):
    if s.startswith(prefix):
        return s[len(prefix):]
    else:
        return s[:]


def get_first_matching_prefix(key, search_space):
    for prefix_key in search_space:
        if key.startswith(prefix_key):
            return prefix_key

    raise Exception(
        'Unable to find a prefix match for key "{key}"'
        'in the given search space'.format(
            key=key
        )
    )


def get_gthread_prefix():
    from .wsgi_servers.gunicorn import CustomThreadWorker
    return CustomThreadWorker.get_gthread_prefix()
