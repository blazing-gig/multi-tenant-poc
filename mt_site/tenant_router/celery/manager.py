from copy import deepcopy
from importlib import import_module

from django.conf import settings

from tenant_router.managers import tenant_context_manager
from tenant_router.celery.utils import construct_schedule_name


class _CeleryManager:

    def __init__(self, name):
        self.name = name

    def _is_celery_installed(self):
        try:
            import celery # noqa
            return True
        except ImportError:
            return False

    def _is_db_scheduler_installed(self):
        try:
            import django_celery_beat # noqa
            return True
        except ImportError:
            return False

    def _patch_celery_beat_schedule(self):
        if getattr(settings, 'CELERY_BEAT_SCHEDULE', None):
            final_beat_schedule_dict = {}
            for schedule_name, schedule_dict in settings.CELERY_BEAT_SCHEDULE.items():

                for tenant_context in tenant_context_manager.all():
                    final_schedule_name = construct_schedule_name(
                        tenant_alias=tenant_context.alias,
                        schedule_name=schedule_name
                    )

                    copy_schedule_dict = deepcopy(schedule_dict)

                    options_dict = copy_schedule_dict.get('options', {})

                    if options_dict:
                        options_dict['headers'][
                            'tenant_id'
                        ] = tenant_context.id

                    else:
                        copy_schedule_dict['options'] = {
                            "headers": {
                                "tenant_id": tenant_context.id
                            }
                        }

                    final_beat_schedule_dict[final_schedule_name] = copy_schedule_dict

            settings.CELERY_BEAT_SCHEDULE = final_beat_schedule_dict

    def _register_celery_signals(self):
        import_module('.signals', package='tenant_router.celery')

    def _register_db_signal_handlers(self):
        import_module('.db_signals', package='tenant_router.celery.beat')

    def bootstrap(self):
        if self._is_celery_installed():
            self._register_celery_signals()

            self._patch_celery_beat_schedule()

            if self._is_db_scheduler_installed():
                self._register_db_signal_handlers()


celery_manager = _CeleryManager("celery_manager")
