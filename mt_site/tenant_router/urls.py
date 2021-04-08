from django.urls import path

from tenant_router.views.health_check import tenant_db_health_check
from tenant_router.views.tenant_create import TenantCreateView
from tenant_router.views.tenant_detail import TenantDetailView

urlpatterns = [
    path(
        "health-check/",
        tenant_db_health_check,
        name='tenant_db_health_check'
    ),
    path(
        "tenant/",
        TenantCreateView.as_view(),
        name='tenant_create_view'
    ),
    path(
        "tenant/<str:tenant_id>/",
        TenantDetailView.as_view(),
        name='tenant_detail_view'
    )
]

app_name = 'tenant_router'
