from django.core.cache import caches
from django.core.management import call_command

from tenant_router.conf import settings
from tenant_router.schemas import TenantContext
from tenant_router.orm_backends.core import orm_managers
from tenant_router.orm_backends.utils import (
    ORM_CONFIG_PREFIX_KEY,
    deconstruct_orm_key_template_alias
)
from tenant_router.utils import (
    remove_prefix, join_keys
)
from tenant_router.constants import constants


class HttpEvent:
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return "HttpEvent(data={data})".format(
            data=self.data
        )


class BaseTenantHandler:
    _CALLBACK_CHAIN = None

    def __init__(self, tenant_id, request_payload):
        self.tenant_id = tenant_id
        self.should_migrate = request_payload.get("should_migrate", True)
        self.deploy_info = request_payload["deploy_info"]

        self.config_store = caches[constants.CONFIG_STORE_ALIAS]

        self._setup_mapping_metadata()
        self.tenant_context = TenantContext.from_id(self.tenant_id)

        self.final_event_payload = {
            'tenant_id': self.tenant_id,
            ORM_CONFIG_PREFIX_KEY: {},
        }

    @staticmethod
    def _resolve_metadata_key(mapping_key):
        if mapping_key.startswith(ORM_CONFIG_PREFIX_KEY):
            return ORM_CONFIG_PREFIX_KEY
        else:
            raise Exception(
                "Unable to resolve mapping key "
                "{key}".format(key=mapping_key)
            )

    def _exec_callback_chain(self):
        event = HttpEvent(data=self.final_event_payload)
        for callback in self._CALLBACK_CHAIN:
            callback(event)

        self.final_event_payload["proc_uuid"] = constants.PROC_UUID

    def _exec_migrate(self):
        if self.should_migrate:
            print("calling migrate...")
            try:
                call_command("migrate_all", tenant_id=self.tenant_id)
            except Exception as e:
                print("exc is ", e)

    def _setup_mapping_metadata(self):
        self.mapping_metdata = self.config_store.get(
            constants.NORMALIZED_MAPPING_METADATA
        )
        if not self.mapping_metdata:
            raise Exception(
                "'mapping_metadata' key is missing in config store. "
                "Provide a valid value and try again."
            )

    def _orm_key_handler(self, mapping_key, value):
        orm_key_template_alias = remove_prefix(
            mapping_key,
            prefix=ORM_CONFIG_PREFIX_KEY
        ).strip(constants.KEY_SEPARATOR)

        orm_key, _ = deconstruct_orm_key_template_alias(
            orm_key_template_alias
        )

        orm_manager = orm_managers[orm_key]

        final_key = join_keys(
            TenantContext.from_id(self.tenant_id).alias,
            settings.TENANT_ROUTER_SERVICE_NAME,
            mapping_key
        )
        final_config = orm_manager.format_conn_url(value)

        self.config_store.set(final_key, final_config)
        self.final_event_payload[ORM_CONFIG_PREFIX_KEY][orm_key] = {
            final_key: final_config
        }

    def _generate_event_payload(self):
        for key, value in self.deploy_info.items():
            mapping_key = self.mapping_metdata[key]
            resolved_value = self._resolve_metadata_key(mapping_key)

            if resolved_value == ORM_CONFIG_PREFIX_KEY:
                self._orm_key_handler(mapping_key, value)
