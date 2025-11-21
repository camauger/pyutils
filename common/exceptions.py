"""Shared exception classes for pyutils."""

from __future__ import annotations


class PyUtilsError(Exception):
    """Base exception for all pyutils errors."""

    pass


class FileOperationError(PyUtilsError):
    """Error during file operations."""

    pass


class ImageProcessingError(PyUtilsError):
    """Error during image processing."""

    pass


class ValidationError(PyUtilsError):
    """Input validation error."""

    pass


class DependencyError(PyUtilsError):
    """Missing required dependency."""

    pass


class APIError(PyUtilsError):
    """External API call error."""

    pass

