import json

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from tenant_router.tenant_channel_observer import TenantLifecycleEvent
from tenant_router.views.handlers.tenant_delete import TenantDeleteHandler
from tenant_router.views.handlers.tenant_update import TenantUpdateHandler


@method_decorator(csrf_exempt, name='dispatch')
class TenantDetailView(View):
    def put(self, request, tenant_id):
        payload = json.loads(request.body)

        handler = TenantUpdateHandler(
            tenant_id=tenant_id,
            request_payload=payload
        )
        handler.execute()

        return HttpResponse(
            content=json.dumps(
                {
                    "tenant_id": tenant_id,
                    "lifecycle_event": TenantLifecycleEvent.ON_TENANT_UPDATE
                }
            ),
            status=200
        )

    def delete(self, request, tenant_id):
        handler = TenantDeleteHandler(
            tenant_id=tenant_id
        )
        handler.execute()
        return HttpResponse(
            content=json.dumps(
                {
                    "tenant_id": tenant_id,
                    "lifecycle_event": TenantLifecycleEvent.ON_TENANT_DELETE
                }
            ),
            status=200
        )
