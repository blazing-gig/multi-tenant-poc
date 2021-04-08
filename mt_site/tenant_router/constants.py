import uuid
from enum import Enum

from django.utils.functional import cached_property
from tenant_router.conf import settings
from tenant_router.utils import join_keys


class WorkerType(str, Enum):
    SYNC = 'sync'
    ASGI = 'asgi'


class _Constants:

    @cached_property
    def KEY_SEPARATOR(self):
        return "_"

    @cached_property
    def BASE_TENANT(self):
        return "__base__"

    @cached_property
    def TENANT_METADATA(self):
        return "tenant_metadata"

    @cached_property
    def MAPPING_METADATA(self):
        return "mapping_metadata"

    @cached_property
    def NORMALIZED_MAPPING_METADATA(self):
        return join_keys(
            settings.TENANT_ROUTER_SERVICE_NAME,
            self.MAPPING_METADATA
        )

    @cached_property
    def CONFIG_STORE_ALIAS(self):
        return "tenant_router_config_store"

    @cached_property
    def PROC_UUID(self):
        return str(uuid.uuid4())


constants = _Constants()
