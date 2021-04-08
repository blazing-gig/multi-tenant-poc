import os

from django.core.management import BaseCommand

from tenant_router.managers import tenant_context_manager
from tenant_router.orm_backends.core import orm_managers


class Command(BaseCommand):

    @classmethod
    def set_manager(cls, manager):
        cls._manager = manager

    @property
    def manager(self):
        return self._manager

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id", type=str,
            help="Performs migrate only to databases of the specified tenant. Can "
                 "also be specified by the environment variable 'TENANT_ID'"
        )
        parser.add_argument(
            "--exclude-reserved-aliases", action='store_true',
            help="Excludes 'reserved aliases' from migration. Currently "
                 "pertains only to the 'django orm'"
        )

    def handle(self, *args, **options):
        tenant_id = options["tenant_id"] or os.getenv("TENANT_ID")
        exclude_reserved_aliases = options["exclude_reserved_aliases"]

        if tenant_id:
            tenant_ids_to_migrate = (tenant_id, )
        else:
            tenant_ids_to_migrate = tuple(
                tenant_context_manager.get_tenant_ids()
            )

        for orm_manager in orm_managers:
            if orm_manager.migration_asst:
                orm_manager.migration_asst.perform_migrate(
                    tenant_ids_to_migrate,
                    exclude_reserved_aliases=exclude_reserved_aliases
                )
