from tenant_router.orm_backends.base.router import BaseOrmRouter
from tenant_router.orm_backends.utils import construct_conn_alias
from tenant_router.managers.task_local import tls_tenant_manager


class DjangoOrmRouter(BaseOrmRouter):
    _migrate_strategy = None
    APP_LABELS_TO_EXCLUDE = {
        'django_celery_beat'
    }

    @classmethod
    def set_migrate_strategy(cls, migrate_strategy):
        cls._migrate_strategy = migrate_strategy

    def db_for_read(self, model, **hints):
        # print("read db called")
        context = tls_tenant_manager.current_tenant_context
        return construct_conn_alias(
            tenant_alias=context.alias,
            orm_key=self.manager.ORM_KEY,
            template_alias=self.manager.DEFAULT_CONN_ALIAS
        )

    def db_for_write(self, model, **hints):
        # print("write db called")
        context = tls_tenant_manager.current_tenant_context
        return construct_conn_alias(
            tenant_alias=context.alias,
            orm_key=self.manager.ORM_KEY,
            template_alias=self.manager.DEFAULT_CONN_ALIAS
        )

    def allow_relation(self, *args, **kwargs):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # print("allow migrate called")
        if db in self.manager.conn_aliases:
            if app_label in self.APP_LABELS_TO_EXCLUDE:
                return False

            if self._migrate_strategy:
                return self._migrate_strategy(
                    db, app_label, model_name=model_name, **hints
                )

            return None
        else:
            return False
