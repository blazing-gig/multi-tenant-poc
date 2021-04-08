from django.utils.module_loading import import_string

from tenant_router.conf import settings
from tenant_router.exceptions import ImproperlyConfiguredError
from tenant_router.pubsub.backends.base import PubSubInterface
from tenant_router.pubsub.models import ChannelType
from tenant_router.pubsub.exceptions import InvalidPubSubBackend
from tenant_router.utils import get_first_matching_prefix


class _PubSubProxy(PubSubInterface):

    def __init__(self, name):
        self.name = name
        self._channel_to_subscriber_dict = {}
        self._pubsub_backend = None

    def event_handler(self, raw_event):
        normalized_event = self._pubsub_backend.normalize_event(
            raw_event
        )

        if normalized_event.channel_type == ChannelType.PATTERN:
            subscriber = self._channel_to_subscriber_dict[
                get_first_matching_prefix(
                    key=normalized_event.channel_name,
                    search_space=self._channel_to_subscriber_dict.keys()
                )
            ]
        else:
            subscriber = self._channel_to_subscriber_dict[
                normalized_event.channel_name
            ]

        subscriber(normalized_event)

    def subscribe(
            self,
            subscription_dict,
            channel_type=ChannelType.NORMAL
    ):
        self._channel_to_subscriber_dict.update(subscription_dict)

        subscribers_dict = {
            channel_name: self.event_handler
            for channel_name in subscription_dict
        }

        self._pubsub_backend.subscribe(
            subscribers_dict, channel_type
        )

    def unsubscribe(self, channel_names):
        self._pubsub_backend.unsubscribe(channel_names)

    def publish(self, channel_name, payload):
        return self._pubsub_backend.publish(channel_name, payload)

    def _get_backend_cls(self, settings_dict):
        backend_cls_str = settings_dict.pop('BACKEND', None)

        if not backend_cls_str:
            raise ImproperlyConfiguredError(
                "Value for key 'BACKEND' in TENANT_ROUTER_PUBSUB_SETTINGS "
                "is invalid. Please specify a full dotted path to the "
                "respective backend class."
            )

        try:
            return import_string(backend_cls_str)
        except ImportError:
            raise InvalidPubSubBackend(
                'Could not import {backend_cls_str}'.format(
                    backend_cls_str=backend_cls_str
                )
            )

    def _init_pubsub_backend(self):
        settings_dict = settings.TENANT_ROUTER_PUBSUB_SETTINGS
        backend_cls = self._get_backend_cls(settings_dict)

        self._pubsub_backend = backend_cls(settings_dict)

    def bootstrap(self):
        self._init_pubsub_backend()


pubsub_proxy = _PubSubProxy("pubsub_proxy")
