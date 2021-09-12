import logging

from django.core.cache import CacheHandler

from tenant_router.cache.utils import construct_cache_alias
from tenant_router.managers.task_local import tls_tenant_manager


logger = logging.getLogger(__name__)


class TenantAwareCacheHandler(CacheHandler):

    def __init__(self, *args, **kwargs):
        self._manager = kwargs.pop('manager')
        super().__init__(*args, **kwargs)

    def __getitem__(self, alias):
        tenant_alias = tls_tenant_manager.current_tenant_context.alias
        cache_alias = alias

        if alias in self._manager.template_aliases:
            cache_alias = construct_cache_alias(
                tenant_alias=tenant_alias,
                template_alias=alias
            )

        logger.debug(
            "Trying to fetch cache for alias {cache_alias}".format(
                cache_alias=cache_alias
            )
        )

        return super().__getitem__(cache_alias)

    def __delitem__(self, key):
        logger.debug(
            "Called del on {cls_name} with key {key}".format(
                cls_name=self.__class__.__name__,
                key=key
            )
        )
        if key in self:
            self._caches.caches.pop(key)

    def __contains__(self, item):
        caches = getattr(self._caches, 'caches', {})
        return item in caches
