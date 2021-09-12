import concurrent.futures
from concurrent.futures import ProcessPoolExecutor

from tenant_router.context_decorators import tenant_context_bind
from tenant_router.managers.task_local import tls_tenant_manager


class MissingTenantId(Exception):
    pass


class tenant_aware_fn:
    def __init__(self, fn):
        self._fn = fn

    def __call__(self, *args, **kwargs):
        tenant_id = kwargs.pop('tenant_id', None)
        if not tenant_id:
            raise MissingTenantId(
                "Something"
            )
        with tenant_context_bind(tenant_id):
            return self._fn(*args, **kwargs)


class TenantAwareProcessPoolExecutor(ProcessPoolExecutor):

    def submit(self, fn, *args, **kwargs):
        # By binding the target callable to the tenant_context,
        # we make sure that the tenant context which was set in the
        # thread which received the HTTP request (by the middleware)
        # is correctly passed on to the new thread which would execute
        # the target callable from the executor.

        # NOTE:
        # Since this is a patch, if any other third party application's
        # packages/modules were to import ProcessPoolExecutor after the patch
        # is run, it would receive this modified version of the executor.
        # THIS BINDING WOULD NOT AFFECT THE BEHAVIOR OF ANY OF THOSE CALLABLES
        # SINCE THEY HAVE NOTHING TO DO WITH THE TENANT CONTEXT.
        kwargs['tenant_id'] = tls_tenant_manager.current_tenant_context.id
        tenant_aware_func = tenant_aware_fn(fn)

        return super().submit(
            tenant_aware_func, *args, **kwargs
        )


concurrent.futures.ProcessPoolExecutor = TenantAwareProcessPoolExecutor
