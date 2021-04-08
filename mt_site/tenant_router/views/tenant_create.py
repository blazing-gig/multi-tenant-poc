import json

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from tenant_router.tenant_channel_observer import TenantLifecycleEvent
from tenant_router.views.handlers.tenant_create import TenantCreateHandler


@method_decorator(csrf_exempt, name='dispatch')
class TenantCreateView(View):
    def post(self, request):
        payload = json.loads(request.body)

        handler = TenantCreateHandler(
            tenant_id=payload['tenant_id'],
            request_payload=payload
        )
        handler.execute()

        return HttpResponse(
            content=json.dumps(
                {
                    "tenant_id": payload['tenant_id'],
                    "lifecycle_event": TenantLifecycleEvent.ON_TENANT_CREATE
                }
            ),
            status=201
        )
