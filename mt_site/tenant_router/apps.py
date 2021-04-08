from tenant_router.bootstrap import app_bootstrapper
from django.apps import AppConfig


class TenantRouterConfig(AppConfig):
    name = 'tenant_router'

    def ready(self):
        print("within ready...")
        app_bootstrapper.run()
