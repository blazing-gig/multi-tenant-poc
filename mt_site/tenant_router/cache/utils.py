import logging

from tenant_router.conf import settings
from tenant_router.exceptions import DeconstructionError
from tenant_router.utils import join_keys
from tenant_router.constants import constants

CACHE_CONFIG_PREFIX_KEY = 'cache_config'
CONFIG_STORE_ALIAS = 'tenant_router_config_store'


logger = logging.getLogger(__name__)


def construct_cache_alias(
        tenant_alias, template_alias
):
    return join_keys(
        tenant_alias,
        settings.TENANT_ROUTER_SERVICE_NAME,
        CACHE_CONFIG_PREFIX_KEY,
        template_alias
    )


def deconstruct_cache_alias(normalized_cache_alias):
    service_name = settings.TENANT_ROUTER_SERVICE_NAME

    try:
        tenant_alias = normalized_cache_alias[0: normalized_cache_alias.find(
            service_name
        )].strip(
            constants.KEY_SEPARATOR
        )

        st_index = normalized_cache_alias.find(
            CACHE_CONFIG_PREFIX_KEY
        ) + len(CACHE_CONFIG_PREFIX_KEY)

        cache_alias = normalized_cache_alias[st_index:].strip(
            constants.KEY_SEPARATOR
        )

        return tenant_alias, cache_alias
    except Exception as e:
        error_obj = DeconstructionError(
            entity_name="cache alias",
            entity_value=normalized_cache_alias,
            exc_info=str(e),
            schema="<tenant_alias>_<service_name>_<cache_alias>"
        )
        logger.error(str(error_obj))
        raise error_obj
