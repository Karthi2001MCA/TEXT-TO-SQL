"""
Custom exception classes for structured error handling.
"""

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(AppException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(
            detail=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class SQLGenerationError(AppException):
    """Raised when SQL generation fails across all LLMs."""

    def __init__(self, detail: str = "Failed to generate a valid SQL query"):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileUploadError(AppException):
    """Raised when file upload or parsing fails."""

    def __init__(self, detail: str = "File upload failed"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


