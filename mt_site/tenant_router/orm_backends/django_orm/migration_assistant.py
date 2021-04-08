from django.core.management import call_command, CommandError

from tenant_router.orm_backends.base.migration_assistant import BaseMigrationAsst


class DjangoOrmMigrationAsst(BaseMigrationAsst):

    def _perform_migrate(self, template_alias, tenant_id=None):
        try:
            call_command(
                "migrate",
                database=template_alias,
                tenant_id=tenant_id
            )
        except CommandError:
            print(
                "Migration failed for database alias '{template_alias}' "
                "for tenant '{tenant_id}'".format(
                    template_alias=template_alias,
                    tenant_id=tenant_id
                )
            )

    def perform_migrate(self, tenant_ids, **kwargs):
        for tenant_id in tenant_ids:
            self._perform_migrate(
                template_alias=self.manager.DEFAULT_CONN_ALIAS,
                tenant_id=tenant_id
            )
        exclude_reserved_aliases = kwargs.get("exclude_reserved_aliases", False)
        if not exclude_reserved_aliases:
            for alias in self.manager.reserved_aliases:
                self._perform_migrate(alias)
