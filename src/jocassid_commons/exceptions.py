
from typing import Any


class NoSubclassImplementationError(NotImplementedError):

    def __init__(self, superclass_instance: Any, message: str = ''):
        if not message:
            message = (
                f"Subclass of {superclass_instance.__class__.__name__} "
                f"must implement this method"
            )
        super().__init__(message)
