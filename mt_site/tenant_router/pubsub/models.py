from enum import Enum


class ChannelType(str, Enum):
    PATTERN = 'pattern'
    NORMAL = 'normal'


class PubSubEvent:
    def __init__(
            self,
            channel_name,
            channel_type,
            raw,
            data
    ):
        self.channel_name = channel_name
        self.channel_type = channel_type
        self.raw = raw
        self.data = data

    def __repr__(self):
        return ("PubSubEvent(channel_name={channel_name} "
                "channel_type={channel_type} "
                "data={data} "
                "raw={raw})").format(
            channel_name=self.channel_name,
            channel_type=self.channel_type,
            data=self.data,
            raw=self.raw
        )
