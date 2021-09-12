import logging
from copy import copy

import django.core.cache
import django_cache_url
from django.core.cache import caches
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from tenant_router.cache.utils import (
    deconstruct_cache_alias,
    CACHE_CONFIG_PREFIX_KEY,
    CONFIG_STORE_ALIAS
)
from tenant_router.conf import settings
from tenant_router.exceptions import InvalidTypeError
from tenant_router.managers import tenant_context_manager
from tenant_router.pubsub.filters import uuid_filter
from tenant_router.tenant_channel_observer import (
    tenant_channel_observable, TenantLifecycleEvent
)
from tenant_router.utils import join_keys


logger = logging.getLogger(__name__)


class _CacheConfigManager:
    _DEFAULT_CACHE_KEY = "default"
    _DEFAULT_CACHE_BACKEND = 'django.core.' \
                             'cache.backends.' \
                             'locmem.LocMemCache'

    _RESERVED_ALIASES = {CONFIG_STORE_ALIAS}

    def __init__(self, name):
        self.name = name
        self._event_handler_dict = {
            TenantLifecycleEvent.ON_TENANT_CREATE: self.on_tenant_create,
            TenantLifecycleEvent.ON_TENANT_UPDATE: self.on_tenant_update,
            TenantLifecycleEvent.ON_TENANT_DELETE: self.on_tenant_delete
        }

    @property
    def _cache_config(self):
        return settings.CACHES

    @_cache_config.setter
    def _cache_config(self, value):
        settings.CACHES = value

    @cached_property
    def template_aliases(self):
        return set(
            self._template_config.keys()
        ) - self._RESERVED_ALIASES

    @property
    def reserved_aliases(self):
        return self._RESERVED_ALIASES

    def all(self):
        return self._cache_config.items()

    def _apply_patch(self):
        cache_handler_cls = import_string(
            'tenant_router.cache.patch.TenantAwareCacheHandler'
        )

        django.core.cache.caches = \
            self._cache_handler = cache_handler_cls(manager=self)

    def _get_template_config(self, alias):
        try:
            return self._template_config[alias]
        except KeyError:
            raise Exception(
                "Unable to find a matching template for alias '{alias}'"
                " in CACHES dict".format(
                    alias=alias
                )
            )

    def _register_config(self, cache_alias, cache_config):
        _, template_alias = deconstruct_cache_alias(cache_alias)
        template_config = self._get_template_config(
            template_alias
        )
        final_cache_config = {**template_config, **cache_config}
        self._cache_config[cache_alias] = final_cache_config

    @uuid_filter
    def on_tenant_create(self, event):
        logger.info(
            "Executing on_tenant_create for {name} with event {event}".format(
                name=self.name,
                event=event
            )
        )
        payload = event.data.get(CACHE_CONFIG_PREFIX_KEY, {})
        for cache_alias, cache_config in payload.items():
            self._register_config(cache_alias, cache_config)

    @uuid_filter
    def on_tenant_update(self, event):
        logger.info(
            "Executing on_tenant_update for {name} with event {event}".format(
                name=self.name,
                event=event
            )
        )
        payload = event.data.get(CACHE_CONFIG_PREFIX_KEY, {})
        for cache_alias, updated_cache_config in payload.items():
            self._register_config(cache_alias, updated_cache_config)

            if cache_alias in self._cache_handler:
                logger.debug(
                    "Removing old cache connection with "
                    "alias {cache_alias}".format(
                        cache_alias=cache_alias
                    )
                )
                self._cache_handler[cache_alias].close()
                del self._cache_handler[cache_alias]

    @uuid_filter
    def on_tenant_delete(self, event):
        logger.info(
            "Executing on_tenant_delete for {name} with event {event}".format(
                name=self.name,
                event=event
            )
        )
        payload = event.data.get(CACHE_CONFIG_PREFIX_KEY, ())
        for cache_alias in payload:
            self._cache_config.pop(cache_alias)
            if cache_alias in self._cache_handler:
                self._cache_handler[cache_alias].close()
                del self._cache_handler[cache_alias]

    def _fill_reserved_aliases(self):
        for alias in self.reserved_aliases:
            self._cache_config[alias] = self._get_template_config(alias)

    def _fill_template_aliases(self):
        service_name = settings.TENANT_ROUTER_SERVICE_NAME

        for tenant_context in tenant_context_manager.all():
            cache_prefix = join_keys(
                tenant_context.alias,
                service_name,
                CACHE_CONFIG_PREFIX_KEY
            )

            for cache_alias in self._config_store.iter_keys(
                    cache_prefix + '*'
            ):
                cache_config = self._config_store.get(cache_alias)
                self._register_config(cache_alias, cache_config)

    def _init_caches(self):
        self._cache_config = {}
        self._fill_reserved_aliases()
        self._fill_template_aliases()

        # since Django expects the 'default' cache backend to
        # be present always, if it's not present even after filling
        # both template and reserved aliases, fill it with the default
        # `backend` class
        if self._DEFAULT_CACHE_KEY not in self._cache_config:
            self._cache_config[self._DEFAULT_CACHE_KEY] = {
                "BACKEND": self._DEFAULT_CACHE_BACKEND
            }

    def _update_reserved_aliases(self, settings_dict):
        reserved_aliases = settings_dict.get('RESERVED_ALIASES', set())
        if not isinstance(reserved_aliases, set):
            raise InvalidTypeError(
                "'RESERVED_ALIASES' is expected to be of type 'set'."
                "Got {type_} instead".format(
                    type_=type(reserved_aliases)
                )
            )
        self.__class__._RESERVED_ALIASES.update(reserved_aliases)

    def _parse_cache_settings(self):
        cache_settings = settings.TENANT_ROUTER_CACHE_SETTINGS
        self._update_reserved_aliases(cache_settings)
        self._should_apply_patch = cache_settings.get('APPLY_PATCH', True)

    def format_conn_url(self, conn_url):
        cache_config = django_cache_url.parse(conn_url)
        cache_config.pop('BACKEND')
        return cache_config

    def _init_template_config(self):
        self._template_config = copy(self._cache_config)

    def _perform_tenant_channel_subscription(self):
        tenant_channel_observable.subscribe(
            lifecycle_event=TenantLifecycleEvent.ON_TENANT_CREATE,
            callback=self.on_tenant_create
        )
        tenant_channel_observable.subscribe(
            lifecycle_event=TenantLifecycleEvent.ON_TENANT_UPDATE,
            callback=self.on_tenant_update
        )
        tenant_channel_observable.subscribe(
            lifecycle_event=TenantLifecycleEvent.ON_TENANT_DELETE,
            callback=self.on_tenant_delete
        )

    def bootstrap(self):
        self._config_store = caches[CONFIG_STORE_ALIAS]
        self._parse_cache_settings()
        self._init_template_config()

        if self._should_apply_patch:
            self._apply_patch()

        self._init_caches()
        self._perform_tenant_channel_subscription()


cache_config_manager = _CacheConfigManager("cache_config_manager")
