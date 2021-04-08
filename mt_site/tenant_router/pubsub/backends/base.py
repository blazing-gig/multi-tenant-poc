class PubSubInterface:

    # def subscribe_keyspace_events(self, subscription_dict, channel_type):
    #     raise NotImplementedError('Subclasses must override this method')

    def subscribe(self, subscription_dict, channel_type):
        raise NotImplementedError('Subclasses must override this method')

    def unsubscribe(self, channel_names):
        raise NotImplementedError('Subclasses must override this method')

    def normalize_event(self, raw_event):
        raise NotImplementedError('Subclasses must override this method')

    def publish(self, channel_name, payload):
        raise NotImplementedError('Subclasses must override this method')


class BasePubSub(PubSubInterface):
    def __init__(self, settings_dict):
        self._server_location = settings_dict.get('LOCATION', {})

    @property
    def server_location(self):
        return self._server_location


class BaseEventListener:
    def start(self, *args, **kwargs):
        raise NotImplementedError('Subclasses must override this method')

    def stop(self, *args, **kwargs):
        raise NotImplementedError('Subclasses must override this method')
