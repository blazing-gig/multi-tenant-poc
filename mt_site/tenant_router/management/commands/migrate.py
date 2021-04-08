import os

from django.core.management import CommandError
from django.core.management.commands.migrate import Command as MigrateCommand

from tenant_router.context_decorators import tenant_context_bind
from tenant_router.managers import tenant_context_manager
from tenant_router.managers.tenant_context import TenantContextNotFound
from tenant_router.orm_backends.utils import construct_conn_alias, deconstruct_conn_alias


class Command(MigrateCommand):

    @classmethod
    def set_manager(cls, manager):
        cls._manager = manager

    @property
    def manager(self):
        return self._manager

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--tenant-id", type=str,
            help="Performs migrate only to databases of the specified tenant. Can "
                 "also be specified by the environment variable 'TENANT_ID'"
        )

    def _get_tenant_context(self, tenant_id):
        try:
            return tenant_context_manager.get_by_id(tenant_id)
        except TenantContextNotFound as e:
            raise CommandError(
                "An unexpected error occurred while performing migrate: "
                "{exc_info}".format(exc_info=e)
            )

    def handle(self, *args, **options):
        tenant_id = options["tenant_id"] or os.getenv("TENANT_ID")
        db_alias = options["database"]

        if db_alias:

            if db_alias in self.manager.reserved_aliases:
                if tenant_id:
                    self.stdout.write(
                        self.style.WARNING(
                            "Since the given db alias is a 'reserved alias' "
                            "the '--tenant' option will be ignored."
                        )
                    )
                super().handle(*args, **options)

            elif db_alias in self.manager.template_aliases:
                if not tenant_id:
                    raise CommandError(
                        "The db alias specified is a 'template alias'. "
                        "Please specify a tenant with the '--tenant' option "
                        "to proceed."
                    )

                conn_alias = construct_conn_alias(
                    tenant_alias=self._get_tenant_context(tenant_id).alias,
                    orm_key=self.manager.ORM_KEY,
                    template_alias=db_alias
                )
                options["database"] = conn_alias

                with tenant_context_bind(tenant_id):
                    super().handle(*args, **options)

            elif db_alias in self.manager.conn_aliases:
                tenant_alias, _, _ = deconstruct_conn_alias(db_alias)
                with tenant_context_bind(tenant_alias):
                    super().handle(*args, **options)

            else:
                raise CommandError(
                    "Unable to recognise the specified database as a valid "
                    "db alias. Please check whether the value is present "
                    "in 'DATABASES' key in settings.py and try again."
                )
