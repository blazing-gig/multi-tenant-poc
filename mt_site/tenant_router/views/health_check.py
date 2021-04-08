import json

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

from tenant_router.orm_backends.core import orm_managers


@require_http_methods(["GET"])
def tenant_db_health_check(request):
    final_health_check_dict = {}

    for orm_manager in orm_managers:
        health_check_dict = orm_manager.perform_health_check()
        final_health_check_dict.update(health_check_dict)

    return HttpResponse(
        content=json.dumps(final_health_check_dict),
        status=200
    )
