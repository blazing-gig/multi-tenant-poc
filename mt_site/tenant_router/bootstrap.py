import logging
from importlib import import_module

from tenant_router.conf import settings

from tenant_router.event_queue.manager import event_queue_manager
from tenant_router.exceptions import ImproperlyConfiguredError
from tenant_router.celery.manager import celery_manager
from tenant_router.orm_backends.core import orm_managers
from tenant_router.managers.tenant_context import tenant_context_manager
from tenant_router.pubsub.proxy import pubsub_proxy
from tenant_router.pubsub.service import pubsub_service


logger = logging.getLogger(__name__)


def on_worker_init():
    pubsub_service.start()


def on_worker_exit():
    pubsub_service.stop()


class _BootstrapSettingsParser:
    def __init__(self):
        self._bootstrap_seq = []

    def _validate_type(self):
        bootstrap_seq = settings.TENANT_ROUTER_BOOTSTRAP_SETTINGS
        if not (
                isinstance(bootstrap_seq, list)
                or isinstance(bootstrap_seq, tuple)
        ):
            raise ImproperlyConfiguredError(
                'TENANT_ROUTER_BOOTSTRAP_SETTINGS should either be '
                'a `list` or a `tuple`'
            )

        if not all(
                isinstance(bootstrap_cls, str)
                for bootstrap_cls in bootstrap_seq
        ):
            raise ImproperlyConfiguredError(
                'TENANT_ROUTER_BOOTSTRAP_SETTINGS should contain only '
                'strings'
            )

        return True

    def _initialize_bootstrap_seq(self):
        for bootstrap_cls in settings.TENANT_ROUTER_BOOTSTRAP_SETTINGS:
            klass = import_module(bootstrap_cls)
            self._bootstrap_seq.append(klass())

    def parse(self):
        if self._validate_type():
            self._initialize_bootstrap_seq()

        return self._bootstrap_seq


_bootstrap_settings_parser = _BootstrapSettingsParser()


class _AppBootStrapper:

    def __init__(self):
        self._patches = [
            'tenant_router.patches.thread_pool',
            'tenant_router.patches.process_pool',
        ]

        self._bootstrap_sequence = [
            tenant_context_manager,
            orm_managers,
            celery_manager,
            pubsub_proxy,
            event_queue_manager
        ]

    def _init_bootstrap_sequence(self):
        external_bootstrap_seq = _bootstrap_settings_parser.parse()
        self._bootstrap_sequence.extend(external_bootstrap_seq)

    def _run_patches(self):
        for patch in self._patches:
            try:
                import_module(patch)
            except Exception as e:
                raise Exception(
                    "Unable to import patch module {patch} due "
                    "to: {exc_info}".format(
                        patch=patch,
                        exc_info=e
                    )
                )

    def _run_bootstrap_sequence(self):
        for component in self._bootstrap_sequence:
            logger.debug(
                "Bootstrapping component {component_name}".format(
                    component_name=component.name
                )
            )
            component.bootstrap()

    def run(self):
        self._init_bootstrap_sequence()
        self._run_patches()
        self._run_bootstrap_sequence()


app_bootstrapper = _AppBootStrapper()
