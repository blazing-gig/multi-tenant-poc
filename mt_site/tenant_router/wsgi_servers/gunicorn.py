from concurrent.futures import ThreadPoolExecutor

from django.utils.crypto import get_random_string
from gunicorn.workers.gthread import ThreadWorker


class CustomThreadWorker(ThreadWorker):
    _GTHREAD_PREFIX = ''

    @classmethod
    def get_gthread_prefix(cls):
        if not cls._GTHREAD_PREFIX:
            cls._GTHREAD_PREFIX = '_tenant_router_gthread_prefix_{0}'.format(
                get_random_string()
            )

        return cls._GTHREAD_PREFIX

    def get_thread_pool(self):
        prefix = self.get_gthread_prefix()
        print("gthread prefix is ", prefix)
        return ThreadPoolExecutor(
            thread_name_prefix=prefix,
            max_workers=self.cfg.threads
        )
