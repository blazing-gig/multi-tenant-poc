import logging
import random
from builtins import Exception

from django.core.cache import caches

from tenant_router.constants import constants
from tenant_router.pubsub.filters import uuid_filter
from tenant_router.schemas import TenantContext
from tenant_router.tenant_channel_observer import (
    tenant_channel_observable, TenantLifecycleEvent
)

TENANT_IDS_KEY = 'tenant_ids'


class TenantContextNotFound(Exception):
    pass


logger = logging.getLogger(__name__)


class _TenantContextManager:
    def __init__(self, name):
        self.name = name
        self._tenant_id_to_context_dict = None
        self._event_handler_dict = {
            TenantLifecycleEvent.ON_TENANT_CREATE: self.on_tenant_create,
            TenantLifecycleEvent.ON_TENANT_DELETE: self.on_tenant_delete
        }

    def all(self):
        return self._tenant_id_to_context_dict.values()

    def get_tenant_ids(self):
        return self._tenant_id_to_context_dict.keys()

    def get_by_id(self, tenant_id):
        try:
            return self._tenant_id_to_context_dict[
                tenant_id
            ]
        except KeyError:
            raise TenantContextNotFound(
                "Unable to find tenant context for id "
                "'{tenant_id}'".format(tenant_id=tenant_id)
            )

    def get_by_alias(self, tenant_alias):
        for tenant_context in self.all():
            if tenant_context.alias == tenant_alias:
                return tenant_context

        raise TenantContextNotFound(
            "Unable to find tenant context for alias "
            "'{tenant_alias}'".format(tenant_alias=tenant_alias)
        )

    def contains(self, tenant_identifier):
        try:
            _ = self.get_by_id(tenant_identifier)
            result = True
        except TenantContextNotFound:
            try:
                _ = self.get_by_alias(tenant_identifier)
                result = True
            except TenantContextNotFound:
                result = False

        return result

    def _init_tenant_contexts(self):
        config_store = caches[constants.CONFIG_STORE_ALIAS]
        tenant_ids = config_store.get(
            TENANT_IDS_KEY, []
        )
        if not self._tenant_id_to_context_dict:
            self._tenant_id_to_context_dict = {
                tenant_id: TenantContext.from_id(tenant_id)
                for tenant_id in tenant_ids
            }

    def get_random_context(self):
        random_id = random.choice(
            tuple(self._tenant_id_to_context_dict.keys())
        )
        return self.get_by_id(random_id)

    @uuid_filter
    def on_tenant_create(self, event):
        logger.info(
            "Executing on_tenant_create for {name} with event {event}".format(
                name=self.name,
                event=event
            )
        )
        payload = event.data
        tenant_id = payload.get("tenant_id", None)
        if tenant_id:
            self._tenant_id_to_context_dict[
                tenant_id
            ] = TenantContext.from_id(tenant_id)

    @uuid_filter
    def on_tenant_delete(self, event):
        logger.info(
            "Executing on_tenant_delete for {name} with event {event}".format(
                name=self.name,
                event=event
            )
        )
        payload = event.data
        tenant_id = payload.get("tenant_id", None)
        if tenant_id:
            self._tenant_id_to_context_dict.pop(tenant_id)

    def _perform_tenant_channel_subscription(self):
        tenant_channel_observable.subscribe(
            lifecycle_event=TenantLifecycleEvent.ON_TENANT_CREATE,
            callback=self.on_tenant_create
        )
        tenant_channel_observable.subscribe(
            lifecycle_event=TenantLifecycleEvent.ON_TENANT_DELETE,
            callback=self.on_tenant_delete
        )

    def bootstrap(self):
        self._init_tenant_contexts()
        self._perform_tenant_channel_subscription()


tenant_context_manager = _TenantContextManager("tenant_context_manager")
