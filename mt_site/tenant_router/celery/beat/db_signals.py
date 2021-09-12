import json
import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask

from tenant_router.celery.utils import (
    construct_schedule_name,
    deconstruct_schedule_name
)
from tenant_router.managers import tenant_context_manager
from tenant_router.managers.task_local import tls_tenant_manager


logger = logging.getLogger(__name__)


def _is_valid_schedule_name(schedule_name):

    # First try to deconstruct the schedule name to check if
    # its already normalized
    try:
        tenant_alias, _, _ = deconstruct_schedule_name(
            schedule_name
        )
    except Exception:
        return False

    # Check if the `tenant_alias` is actually valid.
    return tenant_context_manager.contains(tenant_alias)


@receiver(pre_save, sender=PeriodicTask)
def periodic_task_normalizer(sender, **kwargs):
    instance = kwargs['instance']
    tenant_context = tls_tenant_manager.current_tenant_context

    if not _is_valid_schedule_name(instance.name):
        instance.name = construct_schedule_name(
            tenant_alias=tenant_context.alias,
            schedule_name=instance.name
        )

    headers = json.loads(instance.headers)

    if not headers.get('tenant_id'):
        headers["tenant_id"] = tenant_context.id

    instance.headers = json.dumps(headers)

    logger.info(
        "PeriodicTask pre-save called. Final task name "
        "and headers is {task_name}: {headers}".format(
            task_name=instance.name,
            headers=instance.headers
        )
    )
