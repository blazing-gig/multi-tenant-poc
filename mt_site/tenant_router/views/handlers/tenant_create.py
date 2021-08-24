import json


from tenant_router.managers import tenant_context_manager
from tenant_router.managers.tenant_context import TENANT_IDS_KEY
from tenant_router.orm_backends.core import orm_managers
from tenant_router.pubsub.proxy import pubsub_proxy
from tenant_router.tenant_channel_observer import (
    TenantLifecycleEvent,
    construct_tenant_channel_name
)
from tenant_router.views.handlers.common import BaseTenantHandler


class TenantCreateHandler(BaseTenantHandler):
    _CALLBACK_CHAIN = (
        tenant_context_manager.on_tenant_create,
        orm_managers.on_tenant_create
    )

    def __init__(self, tenant_id, request_payload):
        super().__init__(tenant_id, request_payload)
        self.final_event_payload[
            "lifecycle_event"
        ] = TenantLifecycleEvent.ON_TENANT_CREATE

    def _add_tenant_id(self):
        tenant_ids = self.config_store.get(TENANT_IDS_KEY, [])
        tenant_ids.append(self.tenant_id)
        self.config_store.set(TENANT_IDS_KEY, tenant_ids)

    def execute(self):
        self._add_tenant_id()
        self._generate_event_payload()

        self._exec_callback_chain()
        print("executing callback chain")
        self._exec_migrate()

        channel_name = construct_tenant_channel_name(
            TenantLifecycleEvent.ON_TENANT_CREATE
        )
        pubsub_proxy.publish(
            channel_name, json.dumps(self.final_event_payload)
        )
