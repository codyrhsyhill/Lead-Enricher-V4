"""Provider implementations for the lead enricher."""

from .base import BaseProvider, ProviderResult
from .manual import ManualProvider

__all__ = ["BaseProvider", "ManualProvider", "ProviderResult"]
