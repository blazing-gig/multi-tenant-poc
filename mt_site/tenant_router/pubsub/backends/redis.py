import json
from json import JSONDecodeError
from threading import Thread, Event
import time

from asgiref.sync import sync_to_async
from redis import Redis

from tenant_router.conf import settings
from tenant_router.pubsub.backends.base import BaseEventListener, BasePubSub
from tenant_router.pubsub.models import ChannelType, PubSubEvent
from tenant_router.pubsub.service import pubsub_service
from tenant_router.constants import WorkerType


class RedisEventListener(BaseEventListener):
    def __init__(self, pubsub):
        self._pubsub = pubsub
        self._pubsub_thread = None
        self._is_stopped = Event()

    def _service_loop(self):
        msg_counter = 0
        try:
            while not self._is_stopped.is_set():
                self._pubsub.get_message(
                    ignore_subscribe_messages=True
                )
                msg_counter += 1

                if msg_counter == 5:
                    msg_counter = 0
                    time.sleep(1)

        except Exception as e:
            print("Exception occurred in thread {name}: {exc_info}".format(
                name=self.__class__.__name__,
                exc_info=e
            ))
            self._is_stopped.set()
        finally:
            self._pubsub.close()

    def start(self, *args, **kwargs):
        if self._pubsub:
            self._pubsub_thread = Thread(
                target=self._service_loop,
                daemon=True
            )
            self._pubsub_thread.start()
        else:
            raise Exception(
                "Attempted to start {cls_name} before initializing"
                "the pubsub layer.".format(
                    cls_name=self.__class__.__name__
                )
            )

    def stop(self, *args, **kwargs):
        if self._pubsub_thread:
            self._is_stopped.set()
            if self._pubsub_thread.is_alive():
                self._pubsub_thread.join(timeout=3)
                print("joined....")


class AsyncRedisEventListener(BaseEventListener):
    def __init__(self, pubsub):
        self._pubsub = pubsub
        self._is_stopped = False

    async def start(self, *args, **kwargs):
        async_get_msg = sync_to_async(
            self._pubsub.get_message, thread_sensitive=False
        )
        while not self._is_stopped:
            await async_get_msg(
                ignore_subscribe_messages=True,
                timeout=5.0
            )
        self._pubsub.close()

    def stop(self, *args, **kwargs):
        self._is_stopped = True


class RedisPubSub(BasePubSub):
    # Currently only mainstream notifs are supported
    _NORMAL_KEY_TEMPLATE = '{channel_name}'
    _PREFIX_KEY_TEMPLATE = _NORMAL_KEY_TEMPLATE + '*'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._worker_type_to_event_listener_map = {
            WorkerType.SYNC: RedisEventListener,
            WorkerType.ASGI: AsyncRedisEventListener
        }

        settings_dict = args[0]
        options = settings_dict.pop('OPTIONS', {})

        client_kwargs = options.pop('CLIENT_KWARGS', {})

        self._ensure_defaults(client_kwargs)
        self._process_server_location(
            client_kwargs
        )

        self._client = Redis(**client_kwargs)

        self._pubsub = self._client.pubsub(
            ignore_subscribe_messages=True
        )
        self._register_event_listener()

    @staticmethod
    def _ensure_defaults(client_kwargs):
        client_kwargs.setdefault('decode_responses', True)
        client_kwargs.setdefault('host', 'localhost')
        client_kwargs.setdefault('port', 6379)

    def _process_server_location(self, client_kwargs):
        if self.server_location:
            if self.server_location.get('HOST'):
                client_kwargs['host'] = self.server_location['HOST']

            if self.server_location.get('PORT'):
                client_kwargs['port'] = int(
                    self.server_location['PORT']
                )

    def _register_event_listener(self):
        cls = self._worker_type_to_event_listener_map[
            settings.TENANT_ROUTER_WORKER_TYPE
        ]
        event_listener = cls(self._pubsub)
        pubsub_service.register_event_listener(event_listener)

    def _construct_channel_name(
            self,
            raw_channel_name,
            channel_type
    ):
        key_type_template = self._PREFIX_KEY_TEMPLATE \
            if channel_type == ChannelType.PATTERN \
            else self._NORMAL_KEY_TEMPLATE

        return key_type_template.format(channel_name=raw_channel_name)

    def _perform_subscription(self, subscription_dict, channel_type):
        if channel_type == ChannelType.PATTERN:
            self._pubsub.psubscribe(
                **subscription_dict
            )
        else:
            self._pubsub.subscribe(
                **subscription_dict
            )

    def subscribe(self, subscription_dict, channel_type):
        transformed_subscription_dict = {
            self._construct_channel_name(
                raw_channel_name=raw_channel_name,
                channel_type=channel_type,
            ): callback
            for raw_channel_name, callback in subscription_dict.items()
        }

        self._perform_subscription(
            transformed_subscription_dict, channel_type
        )

    def unsubscribe(self, channel_names):
        return self._pubsub.unsubscribe(channel_names)

    def publish(self, channel_name, payload):
        return self._client.publish(channel_name, payload)

    def _get_channel_type(self, raw_channel_type):
        if raw_channel_type == 'pmessage':
            return ChannelType.PATTERN

        return ChannelType.NORMAL

    def _get_parsed_data(self, raw_data):
        try:
            return json.loads(raw_data)
        except JSONDecodeError:
            return raw_data

    def normalize_event(self, raw_event):
        print("raw_event is ", raw_event)

        channel_type = self._get_channel_type(raw_event['type'])

        return PubSubEvent(
            channel_name=raw_event['channel'],
            channel_type=channel_type,
            data=self._get_parsed_data(raw_event['data']),
            raw=raw_event
        )
