from django.core.exceptions import FieldError


class InvalidActionError(Exception):
    """Exception raised when an action that should not be attempted is called."""
    pass


class MultilingualFieldError(FieldError):
    pass