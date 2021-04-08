import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, BaseCommand

from tenant_router.config_loader import tenant_config_loader


class Command(BaseCommand):

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-f", "--file", type=str,
            help=(
                "Specify an alternate configuration file. If the value is a filename, "
                "then it has to be present at settings.BASE_DIR. Else it has to be an "
                "absolute file path. "
                "(default: tenant_config.json)"
            ),
            default="tenant_config.json"
        )
        parser.add_argument(
            '--include-tenant-metadata',
            action='store_true',
            help="Syncs the value for the key 'tenant_metadata' to the config store. "
                 "Note that this overrides the value for a key if it's already present "
                 "in the config store.",
        )
        parser.add_argument(
            '--flush-all',
            action='store_true',
            help="Flushes all keys present before populating the config store. Note "
                 "that this is a destructive operation and cannot be undone. Typically "
                 "this flag should be used only during development.",
        )

    def _is_file_path(self, may_be_path):
        return Path(may_be_path).is_absolute()

    def handle(self, *args, **options):
        file_identifier = options["file"]

        if self._is_file_path(file_identifier):
            file_path = file_identifier
        else:
            file_path = os.path.join(
                os.sep, settings.BASE_DIR, file_identifier
            )

        self.stdout.write(
            "Attempting to load file at path: {file_path}".format(
                file_path=file_path
            )
        )
        try:
            with open(file_path, "r") as f:
                config_json = json.load(f)
        except Exception:
            raise CommandError(
                "Unable to read file '{file_identifier}'. Please "
                "check if the specified value is a valid filename/path "
                "and try again.".format(
                    file_identifier=file_identifier
                )
            )

        tenant_config_loader.load(config_json, **options)
