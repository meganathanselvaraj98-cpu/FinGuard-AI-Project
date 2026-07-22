"""Domain exceptions used across the FinGuard service layer."""


class FinGuardError(Exception):
    """Base application error."""


class ValidationError(FinGuardError, ValueError):
    """Raised when user-provided data is invalid."""


class DuplicateRecordError(FinGuardError, ValueError):
    """Raised when a protected duplicate is detected."""


class AuthorizationError(FinGuardError, PermissionError):
    """Raised when a user attempts to access another user's record."""
