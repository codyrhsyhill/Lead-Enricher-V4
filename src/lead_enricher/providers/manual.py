"""Manual provider that sources data from a pre-enriched CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional, Tuple

from .base import BaseProvider, ProviderResult
from ..utils import normalize_lead_id


class ManualProvider(BaseProvider):
    """Lookup enrichment values from a user-supplied CSV.

    The CSV must contain the ``lead_id`` column and any of the enrichment columns.
    If multiple rows contain the same ``lead_id`` the first occurrence wins.
    """

    name = "manual"

    def __init__(self, csv_path: Path) -> None:
        self._data: Dict[str, Dict[str, str]] = {}
        self._fallback: Dict[Tuple[str, str], Dict[str, str]] = {}
        self._load(csv_path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                lead_id = normalize_lead_id(row.get("lead_id"))
                business_name = (row.get("business_name") or "").strip().lower()
                postcode = (row.get("postcode") or "").strip().lower()
                if lead_id and lead_id not in self._data:
                    self._data[lead_id] = row
                key = (business_name, postcode)
                if any(key) and key not in self._fallback:
                    self._fallback[key] = row

    def enrich(self, lead: dict) -> ProviderResult:
        lead_id = normalize_lead_id(lead.get("lead_id"))
        business_name = (lead.get("business_name") or "").strip().lower()
        postcode = (lead.get("postcode") or "").strip().lower()
        row: Optional[Dict[str, str]] = None
        if lead_id and lead_id in self._data:
            row = self._data[lead_id]
        elif (business_name, postcode) in self._fallback:
            row = self._fallback[(business_name, postcode)]
        if not row:
            return ProviderResult()
        verification_urls = row.get("verification_urls") or ""
        url_list = [part.strip() for part in verification_urls.split(";") if part.strip()]
        return ProviderResult(
            owner_phone_e164=row.get("owner_phone_e164") or None,
            owner_line_type=row.get("owner_line_type") or None,
            owner_email_normalized=row.get("owner_email_normalized") or None,
            business_location_city=row.get("business_location_city") or None,
            business_location_county=row.get("business_location_county") or None,
            business_location_country=row.get("business_location_country") or None,
            role_normalized=row.get("role_normalized") or None,
            business_confidence_score=int(row["business_confidence_score"])
            if row.get("business_confidence_score")
            else None,
            notes=row.get("notes") or None,
            verification_urls=url_list,
            company_number=row.get("company_number") or None,
            incorporation_date=row.get("incorporation_date") or None,
            company_type=row.get("company_type") or None,
            is_unverified=(row.get("is_unverified") or "").lower() == "true",
        )
