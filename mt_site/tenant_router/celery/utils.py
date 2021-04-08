import logging

from tenant_router.conf import settings
from tenant_router.exceptions import DeconstructionError
from tenant_router.utils import join_keys
from tenant_router.constants import constants


CELERY_BEAT_DB_ALIAS = 'celery_beat_db'
CELERY_BEAT_APP_LABEL = 'django_celery_beat'


logger = logging.getLogger(__name__)


def construct_schedule_name(tenant_alias, schedule_name):
    return join_keys(
        tenant_alias, settings.TENANT_ROUTER_SERVICE_NAME, schedule_name
    )


def deconstruct_schedule_name(normalized_schedule_name):
    service_name = settings.TENANT_ROUTER_SERVICE_NAME

    try:
        service_name_st_index = normalized_schedule_name.index(
            service_name
        )

        service_name_end_index = (
            service_name_st_index
            + len(service_name)
            + len(constants.KEY_SEPARATOR)
        )

        tenant_alias = normalized_schedule_name[0: service_name_st_index].strip(
            constants.KEY_SEPARATOR
        )

        schedule_name = normalized_schedule_name[service_name_end_index:]

        return (
            tenant_alias, service_name, schedule_name
        )
    except Exception as e:
        error_obj = DeconstructionError(
            entity_name="schedule name",
            entity_value=normalized_schedule_name,
            exc_info=str(e),
            schema="<tenant_alias>_<service_name>_<schedule_name>"
        )
        logger.error(str(error_obj))
        raise error_obj
