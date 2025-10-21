"""Utility helpers for normalization and validation."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Optional

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def normalize_lead_id(value: object) -> Optional[str]:
    """Return a normalized string lead identifier or ``None`` if missing."""
    if value is None:
        return None
    if isinstance(value, float):
        if value != value:  # NaN
            return None
        value = int(value)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(".0"):
        text = text[:-2]
    if text.startswith("lead-"):
        text = text.split("lead-", 1)[-1]
    return text


def normalize_phone(raw: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Normalize a UK phone number to E.164 format and deduce the line type."""
    if not raw:
        return None, None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None, None
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("44"):
        digits = "+" + digits
    elif digits.startswith("0"):
        digits = "+44" + digits[1:]
    elif digits.startswith("7") and len(digits) == 10:
        digits = "+44" + digits
    elif digits.startswith("1") or digits.startswith("2"):
        digits = "+44" + digits
    if not digits.startswith("+44"):
        return None, None
    line_type = None
    if digits.startswith("+447"):
        line_type = "Mobile"
    elif digits.startswith("+441") or digits.startswith("+442"):
        line_type = "Landline"
    return digits, line_type


def normalize_email(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    email = raw.strip().lower()
    if not EMAIL_REGEX.match(email):
        return None
    return email


ROLE_MAPPING = {
    "owner": "Owner/Director",
    "director": "Owner/Director",
    "managing director": "Owner/Director",
    "md": "Owner/Director",
    "marketing": "Marketing (Mgr/Head)",
    "marketing manager": "Marketing (Mgr/Head)",
    "marketing head": "Marketing (Mgr/Head)",
    "sales": "Sales (Mgr/Head)",
    "sales manager": "Sales (Mgr/Head)",
    "sales head": "Sales (Mgr/Head)",
    "general manager": "General Manager",
}


def normalize_role(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    key = text.lower()
    if key in ROLE_MAPPING:
        return ROLE_MAPPING[key]
    for candidate, mapped in ROLE_MAPPING.items():
        if candidate in key:
            return mapped
    return text.title()


WEBSITE_HINTS = ("http://", "https://", "www.")


def score_confidence(
    *,
    has_phone: bool,
    has_email: bool,
    has_active_site: bool,
    decision_maker_confirmed: bool,
) -> int:
    score = 3
    if has_phone:
        score += 2
    if has_email:
        score += 2
    if has_active_site:
        score += 2
    if decision_maker_confirmed:
        score += 1
    return max(1, min(score, 10))


def normalize_date(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def coalesce(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value:
            return value
    return None


def deduplicate_verified_rows(rows: Iterable[dict]) -> list[dict]:
    seen: set[tuple[Optional[str], Optional[str]]] = set()
    unique_rows: list[dict] = []
    for row in rows:
        signature = (row.get("owner_phone_e164"), row.get("owner_email_normalized"))
        if signature in seen and any(signature):
            continue
        if any(signature):
            seen.add(signature)
        unique_rows.append(row)
    return unique_rows
