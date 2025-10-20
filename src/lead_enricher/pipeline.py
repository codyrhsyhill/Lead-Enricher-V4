"""Batch enrichment pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .io import ensure_master_schema
from .providers.base import BaseProvider, ProviderResult
from .utils import (
    deduplicate_verified_rows,
    normalize_email,
    normalize_lead_id,
    normalize_phone,
    normalize_role,
    normalize_date,
    score_confidence,
)

ENRICHED_COLUMNS = [
    "owner_phone_e164",
    "owner_line_type",
    "owner_email_normalized",
    "business_location_city",
    "business_location_county",
    "business_location_country",
    "role_normalized",
    "business_confidence_score",
    "notes",
    "verification_urls",
    "company_number",
    "incorporation_date",
    "company_type",
    "is_unverified",
]


@dataclass
class LeadEnrichmentConfig:
    batch_size: int = 20
    include_unverified: bool = False
    auto_continue: bool = True


@dataclass
class LeadEnricher:
    providers: Sequence[BaseProvider]
    config: LeadEnrichmentConfig = field(default_factory=LeadEnrichmentConfig)

    def select_pending(self, master_rows: Sequence[dict], enriched_rows: Sequence[dict]) -> List[dict]:
        ensure_master_schema(master_rows)
        enriched_lead_ids = {
            normalize_lead_id(row.get("lead_id")) for row in enriched_rows
        }
        enriched_pairs = {
            (
                (row.get("business_name") or "").strip().lower(),
                (row.get("postcode") or "").strip().lower(),
            )
            for row in enriched_rows
        }
        pending: List[dict] = []
        for row in master_rows:
            lead_id = normalize_lead_id(row.get("lead_id"))
            key = (
                (row.get("business_name") or "").strip().lower(),
                (row.get("postcode") or "").strip().lower(),
            )
            if lead_id and lead_id in enriched_lead_ids:
                continue
            if key in enriched_pairs and any(key):
                continue
            pending.append(row)
        return pending

    def enrich(self, master_rows: Sequence[dict], enriched_rows: Sequence[dict]) -> tuple[list[dict], list[dict]]:
        pending = self.select_pending(master_rows, enriched_rows)
        verified: List[dict] = []
        unverified: List[dict] = []
        index = 0
        while index < len(pending):
            batch_verified: List[dict] = []
            batch_unverified: List[dict] = []
            while index < len(pending) and len(batch_verified) < self.config.batch_size:
                row = pending[index]
                enriched = self._process_row(row)
                if enriched.get("is_unverified"):
                    batch_unverified.append(enriched)
                else:
                    batch_verified.append(enriched)
                index += 1
            verified.extend(batch_verified)
            unverified.extend(batch_unverified)
            if not self.config.auto_continue:
                break
        verified = deduplicate_verified_rows(verified)
        if not self.config.include_unverified:
            unverified = []
        return verified, unverified

    def _process_row(self, row: dict) -> dict:
        merged = {
            key: row.get(key)
            for key in row.keys()
        }
        collected_urls: list[str] = []
        best_notes: list[str] = []
        for provider in self.providers:
            result = provider.enrich(row)
            merged = self._merge_result(merged, result)
            collected_urls.extend(url for url in result.verification_urls if url)
            if result.notes:
                best_notes.append(result.notes)
        phone, line_type = normalize_phone(merged.get("owner_phone_e164"))
        email = normalize_email(merged.get("owner_email_normalized"))
        role = normalize_role(merged.get("role_normalized"))
        incorporation_date = normalize_date(merged.get("incorporation_date"))
        merged.update(
            owner_phone_e164=phone,
            owner_line_type=line_type,
            owner_email_normalized=email,
            role_normalized=role,
            incorporation_date=incorporation_date,
        )
        merged["business_location_country"] = merged.get(
            "business_location_country"
        ) or "United Kingdom"
        merged["verification_urls"] = ";".join(dict.fromkeys(collected_urls))
        has_phone = bool(phone)
        has_email = bool(email)
        merged["notes"] = "; ".join(dict.fromkeys(best_notes)) or merged.get("notes")
        decision_maker_confirmed = bool(merged.get("role_normalized"))
        has_active_site = bool(
            merged.get("verification_urls")
            or (merged.get("website") or "").startswith("http")
        )
        merged["business_confidence_score"] = merged.get("business_confidence_score") or score_confidence(
            has_phone=has_phone,
            has_email=has_email,
            has_active_site=has_active_site,
            decision_maker_confirmed=decision_maker_confirmed,
        )
        if not has_phone and not has_email:
            merged["is_unverified"] = True
        else:
            merged["is_unverified"] = bool(merged.get("is_unverified"))
        for key in ENRICHED_COLUMNS:
            merged.setdefault(key, None)
        return merged

    def _merge_result(self, current: dict, result: ProviderResult) -> dict:
        def take(existing: Optional[str], new_value: Optional[str]) -> Optional[str]:
            return existing or new_value

        merged = current.copy()
        merged["owner_phone_e164"] = take(current.get("owner_phone_e164"), result.owner_phone_e164)
        merged["owner_line_type"] = take(current.get("owner_line_type"), result.owner_line_type)
        merged["owner_email_normalized"] = take(current.get("owner_email_normalized"), result.owner_email_normalized)
        merged["business_location_city"] = take(current.get("business_location_city"), result.business_location_city)
        merged["business_location_county"] = take(current.get("business_location_county"), result.business_location_county)
        merged["business_location_country"] = take(current.get("business_location_country"), result.business_location_country)
        merged["role_normalized"] = take(current.get("role_normalized"), result.role_normalized)
        merged["business_confidence_score"] = result.business_confidence_score or current.get("business_confidence_score")
        merged["notes"] = take(current.get("notes"), result.notes)
        merged["company_number"] = take(current.get("company_number"), result.company_number)
        merged["incorporation_date"] = take(current.get("incorporation_date"), result.incorporation_date)
        merged["company_type"] = take(current.get("company_type"), result.company_type)
        merged["is_unverified"] = result.is_unverified if result.is_unverified is not None else current.get("is_unverified")
        return merged


def default_output_fields(master_rows: Sequence[dict]) -> List[str]:
    if not master_rows:
        return list(ENRICHED_COLUMNS)
    fields = list(master_rows[0].keys())
    for column in ENRICHED_COLUMNS:
        if column not in fields:
            fields.append(column)
    return fields
