import json

from django.core.cache import caches

from tenant_router.conf import settings
from tenant_router.schemas import TenantContext

from tenant_router.constants import constants
from tenant_router.managers.tenant_context import TENANT_IDS_KEY
from tenant_router.orm_backends.utils import ORM_CONFIG_PREFIX_KEY, deconstruct_conn_alias
from tenant_router.pubsub.proxy import pubsub_proxy
from tenant_router.tenant_channel_observer import (
    TenantLifecycleEvent,
    construct_tenant_channel_name
)
from tenant_router.utils import join_keys


class TenantDeleteHandler:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.tenant_context = TenantContext.from_id(tenant_id)

        self.config_store = caches[constants.CONFIG_STORE_ALIAS]
        self.final_event_payload = {
            "tenant_id": self.tenant_id,
            ORM_CONFIG_PREFIX_KEY: {},
            "lifecycle_event": TenantLifecycleEvent.ON_TENANT_DELETE
        }

    def _delete_tenant_id(self):
        tenant_ids = self.config_store.get(TENANT_IDS_KEY, [])
        try:
            tenant_ids.remove(self.tenant_id)
            self.config_store.set(
                TENANT_IDS_KEY, tenant_ids
            )
            return True
        except ValueError:
            return False

    def _orm_key_deleter(self):
        prefix = join_keys(
            self.tenant_context.alias,
            settings.TENANT_ROUTER_SERVICE_NAME,
            ORM_CONFIG_PREFIX_KEY
        )

        for key in self.config_store.iter_keys(prefix + "*"):
            _, orm_key, _ = deconstruct_conn_alias(key)

            if orm_key in self.final_event_payload[ORM_CONFIG_PREFIX_KEY]:
                self.final_event_payload[ORM_CONFIG_PREFIX_KEY][
                    orm_key
                ].append(key)
            else:
                self.final_event_payload[ORM_CONFIG_PREFIX_KEY][
                    orm_key
                ] = [key]

            self.config_store.delete(key)

    def execute(self):
        deleted = self._delete_tenant_id()
        if deleted:
            self._orm_key_deleter()

            channel_name = construct_tenant_channel_name(
                lifecycle_event=TenantLifecycleEvent.ON_TENANT_DELETE,
                tenant_context=self.tenant_context
            )
            pubsub_proxy.publish(
                channel_name,
                json.dumps(self.final_event_payload)
            )
