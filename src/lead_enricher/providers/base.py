"""Provider interfaces for lead enrichment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ProviderResult:
    """Structured enrichment data returned by a provider."""

    owner_phone_e164: Optional[str] = None
    owner_line_type: Optional[str] = None
    owner_email_normalized: Optional[str] = None
    business_location_city: Optional[str] = None
    business_location_county: Optional[str] = None
    business_location_country: Optional[str] = None
    role_normalized: Optional[str] = None
    business_confidence_score: Optional[int] = None
    notes: Optional[str] = None
    verification_urls: list[str] = field(default_factory=list)
    company_number: Optional[str] = None
    incorporation_date: Optional[str] = None
    company_type: Optional[str] = None
    is_unverified: Optional[bool] = None
    metadata: Dict[str, str] = field(default_factory=dict)


class BaseProvider:
    """Base class for enrichment providers."""

    name = "base"

    def enrich(self, lead: dict) -> ProviderResult:
        raise NotImplementedError
