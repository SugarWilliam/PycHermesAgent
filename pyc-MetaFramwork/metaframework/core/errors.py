"""Structured MetaFramework errors."""


class MetaFrameworkError(Exception):
    """Base MetaFramework error."""


class UnknownCapabilityError(MetaFrameworkError):
    """Capability id is not registered."""


class DependencyUnavailableError(MetaFrameworkError):
    """Required dependency is unavailable."""


class ValidationError(MetaFrameworkError):
    """Input data validation failed."""


class ExecutionError(MetaFrameworkError):
    """Engine execution failed."""
