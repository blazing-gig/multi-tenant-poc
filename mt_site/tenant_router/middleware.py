from django.urls import resolve
from django.utils.module_loading import import_string

from tenant_router.conf import settings
from tenant_router.exceptions import ImproperlyConfiguredError
from tenant_router.managers.tenant_context import tenant_context_manager
from tenant_router.managers.tls import tls_tenant_manager


WHITELIST_ROUTES = 'WHITELIST_ROUTES'
TENANT_ID_RESOLVER = 'TENANT_ID_RESOLVER'


class TenantIdResolveError(Exception):
    pass


class TenantContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._whitelist_routes = {
            'tenant_router:tenant_create_view',
            'tenant_router:tenant_detail_view',
            'tenant_router:tenant_db_health_check'
        }
        # One-time configuration and initialization.
        self._parse_middleware_settings()

    def _set_whitelist_routes(self, routes):
        if not isinstance(routes, set):
            raise ImproperlyConfiguredError(
                "Expected '{WHITELIST_ROUTES}' value to be of type 'set'."
                " Got type {type_} instead".format(
                    type_=type(routes),
                    WHITELIST_ROUTES=WHITELIST_ROUTES
                )
            )

        self._whitelist_routes.update(routes)

    def _set_tenant_id_resolver(self, resolver):
        self._tenant_id_resolver = None
        if resolver:
            try:
                self._tenant_id_resolver = import_string(resolver)
            except ImportError:
                raise ImproperlyConfiguredError(
                    "Unable to import path specified for "
                    "'{TENANT_ID_RESOLVER}'. Please specify a valid "
                    "import path to the callable.".format(
                        TENANT_ID_RESOLVER=TENANT_ID_RESOLVER
                    )
                )

    def _parse_middleware_settings(self):
        settings_dict = settings.TENANT_ROUTER_MIDDLEWARE_SETTINGS
        self._set_whitelist_routes(
            settings_dict.pop(WHITELIST_ROUTES, set())
        )
        self._set_tenant_id_resolver(
            settings_dict.pop(TENANT_ID_RESOLVER, '')
        )

    def _is_route_whitelisted(self, path):
        resolved_obj = resolve(path)
        if resolved_obj._func_path in self._whitelist_routes:
            return True

        if resolved_obj.url_name in self._whitelist_routes:
            return True

        if resolved_obj.route in self._whitelist_routes:
            return True

        if resolved_obj.view_name in self._whitelist_routes:
            return True

        return False

    def _get_tenant_id(self, request):
        if self._tenant_id_resolver:
            return self._tenant_id_resolver(request)

        try:
            tenant_id = request.headers["x-tenant-id"]
        except KeyError:
            raise TenantIdResolveError(
                "Unable to resolve tenant id from "
                "request"
            )

        return tenant_id

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        should_clear_ctxt = False

        if not self._is_route_whitelisted(request.path):
            tenant_id = self._get_tenant_id(request)

            tls_tenant_manager.push_tenant_context(
                tenant_context_manager.get_by_id(
                    tenant_id=tenant_id
                )
            )

            should_clear_ctxt = True

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        if should_clear_ctxt:
            tls_tenant_manager.pop_tenant_context()

        return response

    # def process_view(self, request, view_func, view_args, view_kwargs):
    #     view_func = wrap_in_current_tenant_context(vi ew_func)
    #     return None
