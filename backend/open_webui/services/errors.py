"""Normalized service-layer exceptions and HTTP mappings.

These exceptions provide a consistent way to signal configuration and
runtime errors from provider factories and implementations without
introducing HTTP framework dependencies.
"""

from __future__ import annotations


class ServiceError(RuntimeError):
    """Base class for service-related errors."""


class ProviderConfigurationError(ServiceError):
    """Raised when a provider cannot be constructed with current settings."""


class LocalFeatureDisabledError(ProviderConfigurationError):
    """Raised when a local-only feature is requested in enterprise mode."""


class UpstreamServiceError(ServiceError):
    """Raised when an upstream SaaS provider returns an error."""

