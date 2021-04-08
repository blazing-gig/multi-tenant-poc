import functools
import os
from enum import Enum

from tenant_router.conf import settings
from tenant_router.schemas import TenantContext
from tenant_router.event_queue.manager import event_queue_manager
from tenant_router.event_queue.schemas import ProcessSpecificEvent
from tenant_router.pubsub.proxy import pubsub_proxy
from tenant_router.utils import join_keys


class TenantLifecycleEvent(str, Enum):
    ON_TENANT_CREATE = 'on_tenant_create'
    ON_TENANT_UPDATE = 'on_tenant_update'
    ON_TENANT_DELETE = 'on_tenant_delete'

    POST_TENANT_CREATE = 'post_tenant_create'
    POST_TENANT_UPDATE = 'post_tenant_update'
    POST_TENANT_DELETE = 'post_tenant_delete'

    @classmethod
    def get_tenant_bound_events(cls):
        return {cls.ON_TENANT_UPDATE, cls.ON_TENANT_DELETE}


def construct_tenant_channel_name(
        lifecycle_event, tenant_context=None
):
    if lifecycle_event in TenantLifecycleEvent.get_tenant_bound_events():
        return join_keys(
            tenant_context.alias,
            settings.TENANT_ROUTER_SERVICE_NAME,
            lifecycle_event
        )
    else:
        return lifecycle_event


class _TenantChannelObservable:
    def __init__(self):
        self._lifecycle_event_callbacks = {
            TenantLifecycleEvent.ON_TENANT_CREATE: [],
            TenantLifecycleEvent.ON_TENANT_UPDATE: [],
            TenantLifecycleEvent.ON_TENANT_DELETE: [],
            TenantLifecycleEvent.POST_TENANT_CREATE: [],
            TenantLifecycleEvent.POST_TENANT_UPDATE: [],
            TenantLifecycleEvent.POST_TENANT_DELETE: []
        }

        self._event_scheduler_dict = {
            TenantLifecycleEvent.ON_TENANT_CREATE: self._tenant_create_event_scheduler,
            TenantLifecycleEvent.ON_TENANT_UPDATE: self._tenant_update_event_scheduler,
            TenantLifecycleEvent.ON_TENANT_DELETE: self._tenant_delete_event_scheduler
        }

        self._internal_event_handler_dict = {
            TenantLifecycleEvent.ON_TENANT_CREATE: self._on_tenant_create,
            TenantLifecycleEvent.ON_TENANT_DELETE: self._on_tenant_delete
        }

    @property
    def event_queue(self):
        return event_queue_manager.queue

    def _on_tenant_create(self, event):
        tenant_id = event.data['tenant_id']
        tenant_context = TenantContext.from_id(tenant_id)
        subscription_dict = {
            construct_tenant_channel_name(
                lifecycle_event,
                tenant_context=tenant_context
            ): self.event_scheduler
            for lifecycle_event in TenantLifecycleEvent.get_tenant_bound_events()
        }
        pubsub_proxy.subscribe(subscription_dict)

    def _on_tenant_delete(self, event):
        try:
            tenant_id = event.data['tenant_id']
            tenant_context = TenantContext.from_id(tenant_id)
            channel_names = (
                construct_tenant_channel_name(lifecycle_event, tenant_context)
                for lifecycle_event in TenantLifecycleEvent.get_tenant_bound_events()
            )
            pubsub_proxy.unsubscribe(channel_names)
        except Exception as e:
            print("EXC is ", e)

    def subscribe(self, lifecycle_event, callback):
        self._lifecycle_event_callbacks[lifecycle_event].insert(
            0, callback
        )

    def _event_handler(self, callback_list):
        for callback in callback_list:
            callback()

    def _tenant_create_event_scheduler(self, event):
        final_callbacks_list = []

        on_tenant_create_callbacks = self._lifecycle_event_callbacks[
            TenantLifecycleEvent.ON_TENANT_CREATE
        ]
        post_tenant_create_callbacks = self._lifecycle_event_callbacks[
            TenantLifecycleEvent.POST_TENANT_CREATE
        ]

        for callback in on_tenant_create_callbacks:
            bound_callback = functools.partial(callback, event)
            final_callbacks_list.append(bound_callback)

        for callback in post_tenant_create_callbacks:
            bound_callback = functools.partial(callback, event)
            final_callbacks_list.append(bound_callback)

        tenant_create_event = ProcessSpecificEvent(
            name='tenant_create_event',
            callback=functools.partial(
                self._event_handler, final_callbacks_list
            )
        )
        print("appending create event ", os.getpid())
        self.event_queue.append(tenant_create_event)

    def _tenant_update_event_scheduler(self, event):
        final_callbacks_list = []

        on_tenant_update_callbacks = self._lifecycle_event_callbacks[
            TenantLifecycleEvent.ON_TENANT_UPDATE
        ]
        # print("on_update callbacks is ", on_tenant_update_callbacks)
        post_tenant_update_callbacks = self._lifecycle_event_callbacks[
            TenantLifecycleEvent.POST_TENANT_UPDATE
        ]
        print("post callbacks is ", post_tenant_update_callbacks)

        for callback in on_tenant_update_callbacks:
            bound_callback = functools.partial(callback, event)
            final_callbacks_list.append(bound_callback)

        for callback in post_tenant_update_callbacks:
            bound_callback = functools.partial(callback, event)
            final_callbacks_list.append(bound_callback)

        tenant_update_event = ProcessSpecificEvent(
            name='tenant_update_event',
            callback=functools.partial(
                self._event_handler, final_callbacks_list
            )
        )
        print("appending update event ", os.getpid())
        self.event_queue.append(tenant_update_event)

    def _tenant_delete_event_scheduler(self, event):
        final_callbacks_list = []

        on_tenant_delete_callbacks = self._lifecycle_event_callbacks[
            TenantLifecycleEvent.ON_TENANT_DELETE
        ]
        post_tenant_delete_callbacks = self._lifecycle_event_callbacks[
            TenantLifecycleEvent.POST_TENANT_DELETE
        ]

        for callback in on_tenant_delete_callbacks:
            bound_callback = functools.partial(callback, event)
            final_callbacks_list.append(bound_callback)

        for callback in post_tenant_delete_callbacks:
            bound_callback = functools.partial(callback, event)
            final_callbacks_list.append(bound_callback)

        tenant_delete_event = ProcessSpecificEvent(
            name='tenant_delete_event',
            callback=functools.partial(
                self._event_handler, final_callbacks_list
            )
        )
        print("appending delete event ", os.getpid())
        self.event_queue.append(tenant_delete_event)

    def event_scheduler(self, event):
        lifecycle_event = event.data["lifecycle_event"]

        internal_event_handler = self._internal_event_handler_dict.get(
            lifecycle_event, None
        )
        if internal_event_handler:
            internal_event_handler(event)

        event_scheduler = self._event_scheduler_dict[lifecycle_event]
        event_scheduler(event)

    def _observe_tenant_channels(self):
        from tenant_router.managers import tenant_context_manager
        subscription_dict = {
            construct_tenant_channel_name(
                TenantLifecycleEvent.ON_TENANT_CREATE
            ): self.event_scheduler
        }

        for tenant_context in tenant_context_manager.all():
            for event_type in TenantLifecycleEvent.get_tenant_bound_events():
                subscription_dict[
                    construct_tenant_channel_name(
                        event_type,
                        tenant_context=tenant_context
                    )
                ] = self.event_scheduler

        pubsub_proxy.subscribe(subscription_dict)

    def bootstrap(self):
        self._observe_tenant_channels()


tenant_channel_observable = _TenantChannelObservable()
