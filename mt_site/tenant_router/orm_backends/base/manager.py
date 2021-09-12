from copy import copy

from django.conf import settings
from django.utils.module_loading import import_string

from tenant_router.orm_backends.base.migration_assistant import BaseMigrationAsst
from tenant_router.orm_backends.base.router import BaseOrmRouter
from tenant_router.orm_backends.utils import construct_conn_alias
from tenant_router.managers.task_local import tls_tenant_manager


class InvalidMigrationAsstClassError(Exception):
    pass


class InvalidRouterClassError(Exception):
    pass


class BaseOrmManager:
    ORM_KEY = None
    DEFAULT_CONN_ALIAS = None

    MIGRATION_ASST_CLS = None
    ROUTER_CLS = None

    def __init__(self, settings_dict=None):
        # setting up template config
        template_key = settings_dict.pop('SETTINGS_KEY')
        self._setup_template_config(template_key)

        # unpacking options
        options = settings_dict.get('OPTIONS', {})
        self._migration_asst = self._setup_migration_asst(options)

        # setting up router
        self._router = self._setup_router(options)

    def _setup_migration_asst(self, options_dict):
        migration_asst_dict = options_dict.pop('MIGRATION_ASST', {})
        mig_asst_cls = self.MIGRATION_ASST_CLS
        mig_asst_cls_opts = {}

        if migration_asst_dict:
            mig_asst_cls_path = migration_asst_dict.get('CLASS', '')
            mig_asst_cls_opts = migration_asst_dict.get('OPTIONS', mig_asst_cls_opts)

            if mig_asst_cls_path:
                try:
                    mig_asst_cls = import_string(mig_asst_cls_path)
                except ImportError as e:
                    raise InvalidMigrationAsstClassError(
                        'Could not import class '
                        '{mig_asst_cls_path}: {exc_info}'.format(
                            mig_asst_cls_path=mig_asst_cls_path,
                            exc_info=e
                        )
                    )

        if mig_asst_cls:
            if not issubclass(mig_asst_cls, BaseMigrationAsst):
                raise TypeError(
                    "All migration asst classes must be subclasses of "
                    "'tenant_router.orm_backends.base.migration_assistant"
                    ".BaseMigrationAsst'"
                )

            return mig_asst_cls(self, **mig_asst_cls_opts)

    def _setup_router(self, options_dict):
        if self.ROUTER_CLS:
            if not issubclass(self.ROUTER_CLS, BaseOrmRouter):
                raise InvalidRouterClassError(
                    "Router class must be a subclass of "
                    "'tenant_router.orm_backends.base.router.BaseRouter'"
                )

            self.ROUTER_CLS.set_manager(self)
            return self.setup_router(
                options_dict.pop('ROUTER_OPTS', {})
            )

    def _setup_template_config(self, template_key):
        self._template_config = copy(
            getattr(settings, template_key)
        )

        self._template_aliases = set(
            self._template_config.keys()
        )

    @property
    def migration_asst(self):
        return self._migration_asst

    @property
    def router(self):
        return self._router

    @property
    def template_aliases(self):
        return self._template_aliases

    def conn_aliases_for_tenant(self, tenant_alias):
        return {
            conn_alias
            for conn_alias in self.conn_aliases
            if conn_alias.startswith(tenant_alias)
        }

    @property
    def conn_aliases(self):
        raise NotImplementedError('Subclasses must define this property')

    def setup_router(self, router_opts):
        """
        Subclasses can override this method to customise the behavior of
        how the router should be setup
        """
        return self.ROUTER_CLS

    def unpack_options(self, options_dict):
        """
        Subclasses can override this method to handle custom
        options passed in the 'OPTIONS' parameter of the settings_dict
        """
        pass

    def register_config(self, conn_alias, db_config):
        raise NotImplementedError('Subclasses must define this method')

    def update_config(self, conn_alias, updated_db_config):
        raise NotImplementedError('Subclasses must define this method')

    def delete_config(self, conn_alias):
        raise NotImplementedError('Subclasses must define this method')

    def refresh_stale_connections(self):
        raise NotImplementedError('Subclasses must define this method')

    def format_conn_url(self, conn_url):
        return conn_url

    def perform_health_check(self):
        raise NotImplementedError('Subclasses must define this method')

    def get_current_conn_alias(self, template_alias):
        tenant_alias = tls_tenant_manager.current_tenant_context.alias

        conn_alias = construct_conn_alias(
            tenant_alias=tenant_alias,
            orm_key=self.ORM_KEY,
            template_alias=template_alias
        )

        return conn_alias

    def get_current_db_config(self, template_alias=DEFAULT_CONN_ALIAS):
        raise NotImplementedError('Subclasses must define this method')

    def get_all_db_config(self):
        raise NotImplementedError('Subclasses must define this method')

    def get_template_config(self, template_alias):
        try:
            return self._template_config[template_alias]
        except KeyError:
            raise Exception(
                'Unable to find a matching template for key {template_alias}.'
                'Check whether a definition has been provided for the same'
                'in the corresponding "settings" key template'.format(
                    template_alias=template_alias,
                )
            )

    def get_all_template_config(self):
        return self._template_config.items()
