"""Custom exceptions for the Portfolio Tracker application."""


class PortfolioTrackerError(Exception):
    """Base exception for Portfolio Tracker."""

    pass


class NotFoundError(PortfolioTrackerError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: int | str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} with id {resource_id} not found")


class SyncError(PortfolioTrackerError):
    """Raised when a sync operation fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.original_error = original_error
        super().__init__(message)


class ValidationError(PortfolioTrackerError):
    """Raised when validation fails."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message)


class ConfigurationError(PortfolioTrackerError):
    """Raised when there's a configuration issue."""

    pass


class ExternalAPIError(PortfolioTrackerError):
    """Raised when an external API call fails."""

    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ):
        self.api_name = api_name
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"{api_name}: {message}")
