"""
All global execeptions used across the package are listed here
"""


class ImproperlyConfiguredError(Exception):
    pass


class InvalidKeyError(Exception):
    pass


class MissingKeyError(Exception):
    pass


class InvalidTypeError(Exception):
    pass


class DeconstructionError(Exception):
    exc_msg_template = (
        "Unable to deconstruct {entity_name} {entity_value} "
        "due to exception: {exc_info}. Please check whether the "
        "value conforms to the schema {schema} and try again."
    )

    def __init__(self, entity_name, entity_value, exc_info, schema):
        exc_msg = self.exc_msg_template.format(
            entity_name=entity_name,
            entity_value=entity_value,
            exc_info=exc_info,
            schema=schema
        )
        super().__init__(exc_msg)
