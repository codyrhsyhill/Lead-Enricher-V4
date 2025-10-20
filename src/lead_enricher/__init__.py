"""Lead enrichment toolkit for UK roofing businesses."""

from .pipeline import LeadEnrichmentConfig, LeadEnricher
from .providers.base import BaseProvider, ProviderResult

__version__ = "0.1.0"

__all__ = [
    "BaseProvider",
    "LeadEnrichmentConfig",
    "LeadEnricher",
    "ProviderResult",
    "__version__",
]
