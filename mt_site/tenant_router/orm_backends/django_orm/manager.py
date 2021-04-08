import dj_database_url

from django.db import close_old_connections, DEFAULT_DB_ALIAS, connections
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from tenant_router.exceptions import ImproperlyConfiguredError
from tenant_router.management.commands.migrate import Command as TenantMigrateCommand
from tenant_router.orm_backends.base.manager import BaseOrmManager

from tenant_router.orm_backends.django_orm.\
    migration_assistant import DjangoOrmMigrationAsst

from tenant_router.orm_backends.django_orm.router import DjangoOrmRouter
from tenant_router.orm_backends.django_orm.test_util import TenantAwareTestRunner
from tenant_router.orm_backends.utils import deconstruct_conn_alias


class DjangoOrmManager(BaseOrmManager):
    ORM_KEY = 'django_orm'
    DEFAULT_CONN_ALIAS = DEFAULT_DB_ALIAS
    MIGRATION_ASST_CLS = DjangoOrmMigrationAsst
    ROUTER_CLS = DjangoOrmRouter

    # Class specific attributes
    reserved_aliases = set()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        options = kwargs.get(
            'settings_dict', {}
        ).pop('OPTIONS', {})

        self._update_reserved_conn_aliases(options)
        self._flush_template_defs()
        self._setup_test_util()
        self._setup_migrate_cmd()

    def _update_reserved_conn_aliases(self, options_dict):
        reserved_conn_aliases = options_dict.pop(
            'RESERVED_CONN_ALIASES', set()
        )

        if not isinstance(reserved_conn_aliases, set):
            raise TypeError(
                "'RESERVED_CONN_ALIASES' is expected to be be of type 'set'."
                "Got type '{type_}' instead.".format(
                    type_=type(reserved_conn_aliases)
                )
            )

        self.__class__.reserved_aliases.update(
            reserved_conn_aliases
        )

    def _flush_template_defs(self):
        for alias in tuple(
                self._conn_handler.databases.keys()
        ):
            # if the alias is present in the
            # `template_aliases` set, then it's a
            # template alias. Removing it so that
            # it doesn't pollute the `databases` attribute.
            if alias in self.template_aliases \
                    and alias != self.DEFAULT_CONN_ALIAS:
                self._conn_handler.databases.pop(alias)

    def _setup_test_util(self):
        TenantAwareTestRunner.set_manager(self)

    def _setup_migrate_cmd(self):
        TenantMigrateCommand.set_manager(self)

    def _is_conn_created(self, alias):
        return hasattr(
            self._conn_handler._connections, alias
        )

    @property
    def _conn_handler(self):
        return connections

    @cached_property
    def template_aliases(self):
        return (
            super().template_aliases
            - self.reserved_aliases
        )

    @property
    def conn_aliases(self):
        aliases = (
            set(self._conn_handler.databases.keys())
            - self.template_aliases
        )

        if self.DEFAULT_CONN_ALIAS in aliases \
                and self.DEFAULT_CONN_ALIAS not in self.reserved_aliases:
            # if 'default' alias is neither a template nor a reserved alias
            # then it points to the `DUMMY` db conf and so removing it.
            aliases.remove(self.DEFAULT_CONN_ALIAS)

        return aliases

    def setup_router(self, router_opts):
        mig_strategy_path = router_opts.get(
            'MIGRATE_STRATEGY', ''
        )

        if mig_strategy_path:
            try:
                mig_strategy_callable = import_string(mig_strategy_path)
                self.ROUTER_CLS.set_migrate_strategy(mig_strategy_callable)
            except ImportError:
                raise ImproperlyConfiguredError(
                    "Unable to import 'ROUTER_MIGRATE_STRATEGY' callable. "
                    "Please provide a valid import path and try again."
                )

        return self.ROUTER_CLS

    def register_config(
            self,
            conn_alias,
            db_config
    ):
        _, _, template_alias = deconstruct_conn_alias(conn_alias)
        template_config = self.get_template_config(
            template_alias
        )
        final_db_config = {**template_config, **db_config}

        if conn_alias in self.reserved_aliases:
            raise Exception(
                "Unexpected conn alias `{conn_alias}` encountered "
                "while registering configuration {final_db_config} "
                "from remote KV store".format(
                    conn_alias=conn_alias,
                    final_db_config=final_db_config
                )
            )

        self._conn_handler.databases[conn_alias] = final_db_config

    def update_config(self, conn_alias, updated_db_config):
        self.register_config(
            conn_alias, db_config=updated_db_config
        )
        if self._is_conn_created(conn_alias):
            print("removing old ", conn_alias)
            self._conn_handler[conn_alias].close()
            del self._conn_handler[conn_alias]

    def delete_config(self, conn_alias):
        self._conn_handler.databases.pop(conn_alias)

        if self._is_conn_created(conn_alias):
            print("removing deleted ", conn_alias)
            self._conn_handler[conn_alias].close()
            del self._conn_handler[conn_alias]

    def refresh_stale_connections(self):
        close_old_connections()

    def format_conn_url(self, conn_url):
        config_dict = dj_database_url.parse(conn_url)
        config_dict.pop('ENGINE')
        return config_dict

    def get_current_db_config(self, template_alias=DEFAULT_CONN_ALIAS):
        return self._conn_handler.databases[
            self.get_current_conn_alias(template_alias)
        ]

    def get_all_db_config(self):
        # This does not return a direct reference to the underlying
        # config dict, rather returns a point in time view of all
        # items in the dict since this is thread_safe against
        # any mutation that might happen to the dict in
        # another thread
        return {
            conn_alias: self._conn_handler.databases[conn_alias]
            for conn_alias in self.conn_aliases
        }.items()

    def _check_health(self, conn_alias):
        result = True
        msg = ''
        connection = self._conn_handler[conn_alias]
        connection.ensure_connection()

        if not connection.is_usable():
            result = False
            msg = 'Unable to connect to the database for ' \
                  'alias {conn_alias}'.format(conn_alias=conn_alias)

        return result, msg

    def perform_health_check(self):
        health_check_dict = {}

        for conn_alias in self.conn_aliases:
            result, msg = self._check_health(conn_alias)
            health_check_dict[conn_alias] = {
                'result': result,
                'msg': msg
            }

        return health_check_dict
