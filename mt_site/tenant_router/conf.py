from django.conf import settings as django_settings
from django.utils.functional import cached_property

from tenant_router.exceptions import ImproperlyConfiguredError


class _WrappedSettings:

    def __getattr__(self, item):
        return getattr(django_settings, item)

    def __setattr__(self, key, value):
        if key in self.__dict__:
            raise ValueError("Item assignment is not supported")

        setattr(django_settings, key, value)

    @cached_property
    def TENANT_ROUTER_SERVICE_NAME(self):
        if not (
                getattr(django_settings, 'TENANT_ROUTER_SERVICE_NAME', None)
                and django_settings.TENANT_ROUTER_SERVICE_NAME
        ):
            raise ImproperlyConfiguredError(
                "Key 'TENANT_ROUTER_SERVICE_NAME' missing in settings. Please provide "
                "an appropriate value."
            )

        return django_settings.TENANT_ROUTER_SERVICE_NAME

    @cached_property
    def TENANT_ROUTER_ORM_SETTINGS(self):
        if not (
                getattr(django_settings, 'TENANT_ROUTER_ORM_SETTINGS', None)
                and django_settings.TENANT_ROUTER_ORM_SETTINGS
        ):
            raise ImproperlyConfiguredError(
                "Key 'TENANT_ROUTER_ORM_SETTINGS' is either missing or improperly "
                "configured in settings.py. Please provide an appropriate value."
            )

        return django_settings.TENANT_ROUTER_ORM_SETTINGS

    @cached_property
    def TENANT_ROUTER_PUBSUB_SETTINGS(self):
        if not (
                getattr(django_settings, 'TENANT_ROUTER_PUBSUB_SETTINGS', None)
                and django_settings.TENANT_ROUTER_PUBSUB_SETTINGS
        ):
            raise ImproperlyConfiguredError(
                "Key 'TENANT_ROUTER_PUBSUB_SETTINGS' is either missing or improperly "
                "configured in settings.py. Please provide an appropriate value."
            )

        return django_settings.TENANT_ROUTER_PUBSUB_SETTINGS

    @cached_property
    def TENANT_ROUTER_WORKER_TYPE(self):
        from tenant_router.constants import WorkerType
        if not (
                getattr(django_settings, 'TENANT_ROUTER_WORKER_TYPE', None)
        ):
            return WorkerType.SYNC

        try:
            return WorkerType(
                django_settings.TENANT_ROUTER_WORKER_TYPE
            )
        except ValueError:
            raise ImproperlyConfiguredError(
                "Key 'TENANT_ROUTER_WORKER_TYPE' is invalid. Please provide "
                "an appropriate value from {worker_type} and try again.".format(
                    worker_type=WorkerType.__members__.values()
                )
            )

    @cached_property
    def TENANT_ROUTER_PUBSUB_ENABLED(self):
        return getattr(
            django_settings, 'TENANT_ROUTER_PUBSUB_ENABLED', False
        )

    @cached_property
    def TENANT_ROUTER_BOOTSTRAP_SETTINGS(self):
        return getattr(
            django_settings, 'TENANT_ROUTER_BOOTSTRAP_SETTINGS', ()
        )

    @cached_property
    def TENANT_ROUTER_CACHE_SETTINGS(self):
        return getattr(
            django_settings, 'TENANT_ROUTER_CACHE_SETTINGS', {}
        )

    @cached_property
    def TENANT_ROUTER_MIDDLEWARE_SETTINGS(self):
        return getattr(
            django_settings, 'TENANT_ROUTER_MIDDLEWARE_SETTINGS', {}
        )


settings = _WrappedSettings()
