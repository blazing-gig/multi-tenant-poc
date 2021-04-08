from contextlib import ContextDecorator

from tenant_router.schemas import TenantContext
from tenant_router.managers.tenant_context import (
    tenant_context_manager,
    TenantContextNotFound
)
from tenant_router.managers.tls import tls_tenant_manager


class tenant_context_bind(ContextDecorator):
    def __init__(self, tenant_identifier=None):
        self.context = tls_tenant_manager.current_tenant_context

        if tenant_identifier:
            self.context = self._resolve_tenant_identifier(
                tenant_identifier
            )

    @staticmethod
    def _resolve_tenant_identifier(tenant_identifier):
        if isinstance(tenant_identifier, TenantContext):
            context = tenant_identifier
        else:
            try:
                context = tenant_context_manager.get_by_id(
                    tenant_id=tenant_identifier
                )
            except TenantContextNotFound:
                try:
                    context = tenant_context_manager.get_by_alias(
                        tenant_alias=tenant_identifier
                    )
                except TenantContextNotFound:
                    raise

        return context

    def __enter__(self):
        tls_tenant_manager.push_tenant_context(self.context)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        tls_tenant_manager.pop_tenant_context()
