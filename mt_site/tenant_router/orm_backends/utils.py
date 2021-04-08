import logging

from tenant_router.conf import settings
from tenant_router.exceptions import DeconstructionError
from tenant_router.utils import join_keys
from tenant_router.constants import constants


ORM_CONFIG_PREFIX_KEY = "orm_config"


logger = logging.getLogger(__name__)


def deconstruct_orm_key_template_alias(orm_key_template_alias):
    for orm_key in settings.TENANT_ROUTER_ORM_SETTINGS:
        if orm_key_template_alias.startswith(orm_key):
            try:
                template_alias = orm_key_template_alias[len(orm_key):].strip(
                    '_'
                )
                return orm_key, template_alias

            except Exception as e:
                error_obj = DeconstructionError(
                    entity_name="orm key with template alias",
                    entity_value=orm_key_template_alias,
                    exc_info=str(e),
                    schema="<orm_key>_<template_alias>"
                )
                logger.error(str(error_obj))
                raise error_obj


def deconstruct_conn_alias(conn_alias):
    try:
        service_name = settings.TENANT_ROUTER_SERVICE_NAME

        tenant_alias = conn_alias[0: conn_alias.find(service_name)].strip(
            constants.KEY_SEPARATOR
        )

        st_index = conn_alias.find(ORM_CONFIG_PREFIX_KEY) + len(ORM_CONFIG_PREFIX_KEY)

        orm_key_with_template = conn_alias[st_index:].strip(constants.KEY_SEPARATOR)

        orm_key, template_alias = deconstruct_orm_key_template_alias(
            orm_key_with_template
        )

        return (
            tenant_alias, orm_key, template_alias
        )
    except Exception as e:
        error_obj = DeconstructionError(
            entity_name="conn alias",
            entity_value=conn_alias,
            exc_info=str(e),
            schema="<tenant_alias>_<service_name>_<orm_key>_"
                   "<template_alias>"
        )
        logger.error(str(error_obj))
        raise error_obj


def construct_conn_alias(
        tenant_alias, orm_key, template_alias
):
    return join_keys(
        tenant_alias,
        settings.TENANT_ROUTER_SERVICE_NAME,
        ORM_CONFIG_PREFIX_KEY,
        orm_key,
        template_alias,
        separator=constants.KEY_SEPARATOR
    )
