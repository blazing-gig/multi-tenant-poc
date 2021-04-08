import json

from tenant_router.orm_backends.core import orm_managers
from tenant_router.pubsub.proxy import pubsub_proxy
from tenant_router.tenant_channel_observer import (
    TenantLifecycleEvent,
    construct_tenant_channel_name
)
from tenant_router.views.handlers.common import BaseTenantHandler


class TenantUpdateHandler(BaseTenantHandler):
    _CALLBACK_CHAIN = (
        orm_managers.on_tenant_update
    )

    def __init__(self, tenant_id, request_payload):
        super().__init__(tenant_id, request_payload)
        self.final_event_payload[
            "lifecycle_event"
        ] = TenantLifecycleEvent.ON_TENANT_UPDATE

    def execute(self):
        self._generate_event_payload()

        self._exec_callback_chain()
        self._exec_migrate()

        channel_name = construct_tenant_channel_name(
            TenantLifecycleEvent.ON_TENANT_UPDATE, self.tenant_context
        )
        pubsub_proxy.publish(
            channel_name, json.dumps(self.final_event_payload)
        )
