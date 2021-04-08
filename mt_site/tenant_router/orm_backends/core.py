from django.core.cache import caches
from django.utils.module_loading import import_string

from tenant_router.conf import settings
from tenant_router.constants import constants
from tenant_router.exceptions import ImproperlyConfiguredError
from tenant_router.managers.tenant_context import tenant_context_manager
from tenant_router.orm_backends.utils import ORM_CONFIG_PREFIX_KEY
from tenant_router.pubsub.filters import uuid_filter
from tenant_router.tenant_channel_observer import (
    tenant_channel_observable, TenantLifecycleEvent
)
from tenant_router.utils import join_keys


class InvalidManagerClassError(Exception):
    pass


class _OrmSettingsParser:

    def __init__(self):
        self._DEFAULT_MANAGER_CLS_DICT = {
            'django_orm': 'tenant_router.orm_backends.django_orm.manager'
                          '.DjangoOrmManager',
        }

        self._parsed_orm_settings = {}

        self._validators = [
            self._validate_settings_key,
            self._validate_manager_cls_key,
        ]

    def _get_default_manager_cls(self, orm_key):
        return self._DEFAULT_MANAGER_CLS_DICT.get(orm_key)

    def _validate_manager_cls_key(self):
        for orm_key, orm_def in settings.TENANT_ROUTER_ORM_SETTINGS.items():
            if not orm_def.get('MANAGER')\
                    and not self._get_default_manager_cls(orm_key):

                raise ImproperlyConfiguredError(
                    '"manager_cls" key is missing in the config for "{orm_key}"'
                    'in TENANT_ROUTER_ORM_SETTINGS and a suitable default '
                    'could not be found either.'.format(
                        orm_key=orm_key
                    )
                )

    def _validate_settings_key(self):
        for orm_key, orm_def in settings.TENANT_ROUTER_ORM_SETTINGS.items():
            try:
                settings_key = orm_def['SETTINGS_KEY']
            except KeyError:
                raise ImproperlyConfiguredError(
                    '"settings_key" property in "{orm_key}" definition is '
                    'missing in TENANT_ROUTER_ORM_SETTINGS'.format(
                        orm_key=orm_key
                    )
                )

            if not getattr(settings, settings_key, None):
                raise ImproperlyConfiguredError(
                    '"{settings_key}" in "{orm_key}" defintion in '
                    'TENANT_ROUTER_ORM_SETTINGS is either missing or undefined. '
                    'Please specify a value for this attribute '
                    'in the settings module'.format(
                        settings_key=settings_key,
                        orm_key=orm_key
                    )
                )

    def _initialize(self):
        for orm_key, orm_config in settings.TENANT_ROUTER_ORM_SETTINGS.items():
            manager_cls_path = orm_config.get(
                'MANAGER', self._get_default_manager_cls(orm_key)
            )
            try:
                manager_cls = import_string(manager_cls_path)
                orm_config["MANAGER"] = manager_cls
            except ImportError as e:
                raise InvalidManagerClassError(
                    'Could not import manager class '
                    '{manager_cls_path} due to: {exc_info}'.format(
                        manager_cls_path=manager_cls_path,
                        exc_info=e
                    )
                )

            self._parsed_orm_settings[orm_key] = orm_config

    def _perform_validation(self):
        for validator in self._validators:
            validator()

    def parse(self):
        self._perform_validation()
        self._initialize()
        return self._parsed_orm_settings


class _OrmManager:

    def __init__(self, name):
        self.name = name
        self._orm_key_to_manager_dict = None
        self._event_handler_dict = {
            TenantLifecycleEvent.ON_TENANT_CREATE: self.on_tenant_create,
            TenantLifecycleEvent.ON_TENANT_UPDATE: self.on_tenant_update,
            TenantLifecycleEvent.ON_TENANT_DELETE: self.on_tenant_delete
        }

    def __getitem__(self, orm_key):
        return self._orm_key_to_manager_dict[orm_key]

    def get(self, orm_key, default=None):
        return self._orm_key_to_manager_dict.get(
            orm_key, default
        )

    def items(self):
        return self._orm_key_to_manager_dict.items()

    def keys(self):
        return self._orm_key_to_manager_dict.keys()

    def __iter__(self):
        return iter(self._orm_key_to_manager_dict.values())

    @staticmethod
    def _construct_orm_config(orm_keys):
        orm_config = {}
        service_name = settings.TENANT_ROUTER_SERVICE_NAME
        config_store = caches[constants.CONFIG_STORE_ALIAS]

        for tenant_context in tenant_context_manager.all():
            for orm_key in orm_keys:
                prefix_key = join_keys(
                    tenant_context.alias,
                    service_name,
                    ORM_CONFIG_PREFIX_KEY,
                    orm_key
                )

                for conn_alias in config_store.iter_keys(prefix_key + "*"):
                    db_config = config_store.get(conn_alias)
                    if orm_key in orm_config:
                        orm_config[orm_key][conn_alias] = db_config
                    else:
                        orm_config[orm_key] = {
                            conn_alias: db_config
                        }

        return orm_config

    @staticmethod
    def _perform_config_registration(orm_config, orm_manager):
        for conn_alias, db_config in orm_config.items():
            orm_manager.register_config(
                conn_alias=conn_alias,
                db_config=db_config
            )

    def _init_managers(self, parsed_orm_settings, orm_config):
        self._orm_key_to_manager_dict = {}

        for orm_key, parsed_settings_dict in parsed_orm_settings.items():
            manager_cls = parsed_settings_dict.pop('MANAGER')

            manager_instance = manager_cls(
                settings_dict=parsed_settings_dict
            )

            self._perform_config_registration(
                orm_config.get(orm_key, {}),
                orm_manager=manager_instance
            )

            self._orm_key_to_manager_dict[orm_key] = manager_instance

    @uuid_filter
    def on_tenant_create(self, event):
        payload = event.data
        orm_config_block = payload.get(ORM_CONFIG_PREFIX_KEY, {})
        if orm_config_block:
            for orm_key, config in orm_config_block.items():
                print("orm key is ", orm_key)
                orm_manager = self.get(orm_key)
                for conn_alias, db_config in config.items():
                    orm_manager.register_config(conn_alias, db_config)

    @uuid_filter
    def on_tenant_update(self, event):
        payload = event.data
        orm_config_block = payload.get(ORM_CONFIG_PREFIX_KEY, {})
        if orm_config_block:
            for orm_key, config in orm_config_block.items():
                orm_manager = self.get(orm_key)
                for conn_alias, db_config in config.items():
                    orm_manager.update_config(conn_alias, db_config)

    @uuid_filter
    def on_tenant_delete(self, event):
        payload = event.data
        orm_config_block = payload.get(ORM_CONFIG_PREFIX_KEY, [])
        if orm_config_block:
            for orm_key, config in orm_config_block.items():
                orm_manager = self.get(orm_key)
                for conn_alias in config:
                    orm_manager.delete_config(conn_alias)

    def _perform_tenant_channel_subscription(self):
        tenant_channel_observable.subscribe(
            lifecycle_event=TenantLifecycleEvent.ON_TENANT_CREATE,
            callback=self.on_tenant_create
        )
        tenant_channel_observable.subscribe(
            lifecycle_event=TenantLifecycleEvent.ON_TENANT_UPDATE,
            callback=self.on_tenant_update
        )
        tenant_channel_observable.subscribe(
            lifecycle_event=TenantLifecycleEvent.ON_TENANT_DELETE,
            callback=self.on_tenant_delete
        )

    def bootstrap(self):
        parsed_orm_settings = _OrmSettingsParser().parse()
        orm_config = self._construct_orm_config(
            orm_keys=parsed_orm_settings.keys()
        )
        self._init_managers(
            parsed_orm_settings,
            orm_config
        )
        self._perform_tenant_channel_subscription()


orm_managers = _OrmManager("orm_managers")
