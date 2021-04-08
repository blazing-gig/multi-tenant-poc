
class BaseMigrationAsst:
    def __init__(self, manager, **options):
        self._manager = manager

    @property
    def manager(self):
        return self._manager

    def perform_migrate(self, tenant_ids, **kwargs):
        raise NotImplementedError('Subclasses must define this method')
