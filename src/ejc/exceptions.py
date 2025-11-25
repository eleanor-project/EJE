"""Custom exception hierarchy for the Ethical Jurisprudence Core (EJC)
    Part of the Mutual Intelligence Framework (MIF)"""


class EJEException(Exception):
    """Base exception for all EJE-related errors"""
    pass


class CriticException(EJEException):
    """Raised when a critic fails to evaluate a case"""
    pass


class ValidationException(EJEException):
    """Raised when input validation fails"""
    pass


class ConfigurationException(EJEException):
    """Raised when configuration is invalid or missing"""
    pass


class PrecedentException(EJEException):
    """Raised when precedent storage/retrieval fails"""
    pass


class AggregationException(EJEException):
    """Raised when result aggregation fails"""
    pass


class PluginException(EJEException):
    """Raised when plugin loading or execution fails"""
    pass


class APIException(EJEException):
    """Raised when external API calls fail"""
    pass
