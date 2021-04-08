from django.core.cache import caches

from tenant_router.schemas import TenantContext
from tenant_router.constants import constants


class _TenantConfigLoader:

    def _load_mapping_metadata(self, config_json):
        mapping_metadata = config_json.get(constants.MAPPING_METADATA, None)
        if mapping_metadata:
            self.cache.set(
                constants.NORMALIZED_MAPPING_METADATA, mapping_metadata
            )

    def _load_tenant_metadata(self, config_json):
        from tenant_router.orm_backends.utils import (
            ORM_CONFIG_PREFIX_KEY, construct_conn_alias
        )
        from tenant_router.managers.tenant_context import TENANT_IDS_KEY

        all_tenant_metadata = config_json.get(constants.TENANT_METADATA, None)

        if all_tenant_metadata:
            final_config = {}

            for tenant_id, tenant_metadata in all_tenant_metadata.items():
                tenant_alias = TenantContext.from_id(tenant_id).alias

                for service_name, service_config in tenant_metadata.items():
                    for component_name, component_config in service_config.items():

                        if component_name == ORM_CONFIG_PREFIX_KEY:
                            for orm_key, orm_config in component_config.items():
                                for template_alias, db_config in orm_config.items():
                                    conn_alias = construct_conn_alias(
                                        tenant_alias=tenant_alias,
                                        orm_key=orm_key,
                                        template_alias=template_alias
                                    )

                                    final_config[conn_alias] = db_config

            for key, value in final_config.items():
                self.cache.set(key, value)

            self.cache.set(
                TENANT_IDS_KEY,
                list(all_tenant_metadata.keys())
            )

    def load(self, config_json, **options):
        if config_json:
            self.cache = caches[constants.CONFIG_STORE_ALIAS]

            if options["flush_all"]:
                self.cache.clear()

            self._load_mapping_metadata(config_json)

            if options["include_tenant_metadata"]:
                self._load_tenant_metadata(config_json)


tenant_config_loader = _TenantConfigLoader()
