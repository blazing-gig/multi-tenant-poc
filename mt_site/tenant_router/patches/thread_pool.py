import concurrent.futures
from concurrent.futures.thread import ThreadPoolExecutor

from tenant_router.context_decorators import tenant_context_bind


class TenantAwareThreadPoolExecutor(ThreadPoolExecutor):

    def submit(self, fn, *args, **kwargs):
        # By binding the target callable to the tenant_context,
        # we make sure that the tenant context which was set in the
        # thread which received the HTTP request (by the middleware)
        # is correctly passed on to the new thread which would execute
        # the target callable from the executor.

        # NOTE:
        # Since this is a patch, if any other third party application's
        # packages/modules were to import ThreadPoolExecutor after the patch,
        # it would receive this modified version of the executor.
        # THIS BINDING WOULD NOT AFFECT THE BEHAVIOR OF ANY OF THOSE CALLABLES
        # SINCE THEY HAVE NOTHING TO DO WITH THE TENANT CONTEXT.
        fn = tenant_context_bind()(fn)
        return super().submit(fn, *args, **kwargs)


concurrent.futures.ThreadPoolExecutor = TenantAwareThreadPoolExecutor
