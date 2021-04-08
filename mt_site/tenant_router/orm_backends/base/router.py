
class BaseOrmRouter:
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls, *args, **kwargs)

        # The reason for the manager instance being set
        # this way is because router classes could either be instantiated
        # by the `orm_manager` or internally by the underlying
        # orm library. But we expect router instances to access their
        # respective `orm_manager` instances using the `manager` property.
        instance._manager = cls._manager
        return instance

    @classmethod
    def set_manager(cls, manager):
        cls._manager = manager

    @property
    def manager(self):
        return self._manager
