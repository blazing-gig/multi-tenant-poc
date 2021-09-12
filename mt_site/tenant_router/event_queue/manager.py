import logging
from collections import deque

from django.core import signals

from tenant_router.constants import constants
from tenant_router.event_queue.schemas import ProcessSpecificEvent

logger = logging.getLogger(__name__)


class EventQueueManager:
    def __init__(self, name):
        self.name = name
        self._event_queue = deque(maxlen=50)

    @property
    def queue(self):
        return self._event_queue

    def process_queue(self, **kwargs):
        logger.info(
            "Processing event queue of length {queue_len} "
            "in process {proc_uid}".format(
                queue_len=len(self.queue),
                proc_uid=constants.PROC_UUID
            )
        )
        while True:
            try:
                event = self.queue.popleft()
            except IndexError:
                break

            if isinstance(event, ProcessSpecificEvent):
                callback = event.get_callback()
            else:
                logger.error(
                    "Unknown event of type {event_type} "
                    "detected".format(event_type=type(event))
                )
                callback = None

            if callback:
                try:
                    callback()
                except Exception:
                    logger.exception(
                        "Event {event} raised an exception".format(
                            event=event
                        )
                    )

    def bootstrap(self):
        signals.request_started.connect(self.process_queue)
        signals.request_finished.connect(self.process_queue)


event_queue_manager = EventQueueManager("event_queue_manager")
