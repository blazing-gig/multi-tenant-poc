import asyncio

from tenant_router.conf import settings
from tenant_router.tenant_channel_observer import tenant_channel_observable
from tenant_router.constants import WorkerType


class PubSubService:
    def __init__(self):
        self._is_started = False
        self._worker_type_handler = {
            WorkerType.SYNC: self._sync_handler,
            WorkerType.ASGI: self._asgi_handler
        }

    def register_event_listener(self, event_listener):
        self._event_listener = event_listener

    async def _start_async(self, *args, **kwargs):
        await self._event_listener.start(*args, **kwargs)

    def _sync_handler(self, *args, **kwargs):
        self._event_listener.start(*args, **kwargs)

    def _asgi_handler(self, *args, **kwargs):
        try:
            print("trying to get event loop...")
            loop = asyncio.get_event_loop()
            loop.create_task(
                self._start_async(*args, **kwargs)
            )
        except Exception:
            print("Unable to get a running event loop")

    def start(self, *args, **kwargs):
        if settings.TENANT_ROUTER_PUBSUB_ENABLED:
            tenant_channel_observable.bootstrap()
            self._is_started = True

            handler = self._worker_type_handler[
                settings.TENANT_ROUTER_WORKER_TYPE
            ]
            handler(*args, **kwargs)

    def stop(self, *args, **kwargs):
        if self._is_started:
            self._event_listener.stop(*args, **kwargs)


pubsub_service = PubSubService()
