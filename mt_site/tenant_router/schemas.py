from tenant_router.constants import constants


class TenantContext:

    def __init__(self, id, alias):
        self.id = id
        self.alias = alias

    @staticmethod
    def _get_tenant_alias(id):
        return id.replace(
            '.', constants.KEY_SEPARATOR
        ).replace('-', constants.KEY_SEPARATOR)

    @classmethod
    def from_id(cls, id):
        tenant_alias = cls._get_tenant_alias(id)
        return cls(id, tenant_alias)

    def __str__(self):
        return self.alias

    def __repr__(self):
        return self.alias
