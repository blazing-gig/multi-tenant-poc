

class ProcessSpecificEvent:
    def __init__(self, name, callback=None):
        self._name = name
        self._callback = callback
        self._exhausted = False

    def get_callback(self):
        self._exhausted = True
        return self._callback

    @property
    def exhausted(self):
        return self._exhausted

    def __repr__(self):
        return "ProcessSpecificEvent(name={name})".format(
            name=self._name
        )


# class ThreadSpecificEvent:
#     # def __init__(self, callback):
#     #     self._event_dict = self._construct_event_dict(
#     #         callback
#     #     )
#     #
#     # def _construct_event_dict(self, callback):
#     #     gthread_prefix = get_gthread_prefix()
#     #     print("gthread prefix within event_dict is ", gthread_prefix)
#     #     event_dict = {
#     #         thread.ident: callback
#     #         for thread in threading.enumerate()
#     #             if thread.name.startswith(gthread_prefix)
#     #     }
#     #     print("event_dict is ", event_dict)
#     #     return event_dict
#     #
#     # def get_callback(self, thread_id):
#     #     try:
#     #         return self._event_dict.pop(thread_id)
#     #     except KeyError:
#     #         return None
#     #
#     # @property
#     # def exhausted(self):
#     #     # print("event_dict is ", self._event_dict)
#     #     return True if not self._event_dict else False
