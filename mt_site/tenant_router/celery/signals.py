import logging

from celery.signals import \
    worker_process_init, \
    task_prerun, \
    before_task_publish, \
    worker_process_shutdown, task_postrun

from tenant_router.bootstrap import on_worker_init, on_worker_exit
from tenant_router.event_queue.manager import event_queue_manager
from tenant_router.managers.tenant_context import tenant_context_manager
from tenant_router.orm_backends.core import orm_managers
from tenant_router.managers.task_local import tls_tenant_manager


logger = logging.getLogger(__name__)


@worker_process_init.connect
def init_worker(**kwargs):
    logger.debug("Celery worker init called")
    for orm_manager in orm_managers:
        orm_manager.refresh_stale_connections()

    logger.debug("Starting pubsub service in worker")
    on_worker_init()


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    logger.debug("Celery worker shutdown called")
    on_worker_exit()


@before_task_publish.connect
def receiver_before_task_publish(
        sender=None, headers=None, body=None, **kwargs
):
    logger.info(
        "Celery signal before_task_publish fired "
        "with headers {headers}".format(headers=headers)
    )

    if not headers.get('tenant_id'):
        headers[
            'tenant_id'
        ] = tls_tenant_manager.current_tenant_context.id


@task_prerun.connect
def task_pre_run_handler(**kwargs):
    task = kwargs['task']

    logger.info(
        "Celery signal task_pre_run_handler fired "
        "with tenant id {tenant_id}".format(
            tenant_id=task.request.tenant_id
        )
    )

    event_queue_manager.process_queue()

    tls_tenant_manager.push_tenant_context(
        tenant_context_manager.get_by_id(
            tenant_id=task.request.tenant_id
        )
    )


@task_postrun.connect
def task_post_run_handler(**kwargs):
    logger.debug("Celery signal task_postrun fired")
    event_queue_manager.process_queue()
