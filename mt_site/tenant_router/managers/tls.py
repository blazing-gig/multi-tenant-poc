import contextvars
from tenant_router.schemas import TenantContext


class _TLSTenantManager:

    _tenant_context_var = contextvars.ContextVar(
        'tenant_id_ctx_var', default=[TenantContext.from_id("__base__")]
    )

    def _get_tenant_stack(self):
        return self._tenant_context_var.get()

    def push_tenant_context(self, context):
        if not context:
            raise Exception("A context must be specified")

        self._get_tenant_stack().append(context)

    def pop_tenant_context(self):
        return self._get_tenant_stack().pop()

    @property
    def current_tenant_context(self):
        return self._get_tenant_stack()[-1]


tls_tenant_manager = _TLSTenantManager()
