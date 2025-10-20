"""Command line interface for the lead enrichment pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .io import ensure_master_schema, read_csv_rows, write_csv_rows
from .pipeline import LeadEnrichmentConfig, LeadEnricher, default_output_fields
from .providers.base import BaseProvider
from .providers.manual import ManualProvider


def build_providers(manual_sources: Sequence[Path]) -> list[BaseProvider]:
    providers: list[BaseProvider] = []
    for source in manual_sources:
        providers.append(ManualProvider(source))
    return providers


def run_cli(args: argparse.Namespace) -> int:
    master_path = Path(args.master_csv).expanduser().resolve()
    enriched_path = Path(args.enriched_csv).expanduser().resolve()
    output_path = Path(args.output_csv).expanduser().resolve()
    manual_sources = [Path(item).expanduser().resolve() for item in args.manual_provider]

    master_rows = read_csv_rows(master_path)
    ensure_master_schema(master_rows)
    enriched_rows = read_csv_rows(enriched_path) if enriched_path.exists() else []

    providers = build_providers(manual_sources)
    if not providers:
        print(
            "Warning: running without enrichment providers. Rows without phone or email "
            "will be marked as unverified."
        )

    config = LeadEnrichmentConfig(
        batch_size=args.batch_size,
        include_unverified=args.include_unverified,
        auto_continue=not args.pause_between_batches,
    )
    enricher = LeadEnricher(providers=providers, config=config)
    verified, unverified = enricher.enrich(master_rows, enriched_rows)

    fieldnames = default_output_fields(master_rows)
    write_csv_rows(output_path, verified, fieldnames=fieldnames)
    print(f"Wrote {len(verified)} verified rows to {output_path}")
    if config.include_unverified and unverified:
        unverified_path = output_path.with_name("Unverified leads.csv")
        write_csv_rows(unverified_path, unverified, fieldnames=fieldnames)
        print(f"Wrote {len(unverified)} unverified rows to {unverified_path}")

    if args.report_path:
        summary = {
            "verified_rows": len(verified),
            "unverified_rows": len(unverified),
            "batch_size": config.batch_size,
            "auto_continue": config.auto_continue,
        }
        Path(args.report_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Saved summary report to {args.report_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master_csv", help="Path to businesses_without_contact.csv")
    parser.add_argument("enriched_csv", help="Path to enriched_to_date.csv")
    parser.add_argument("output_csv", help="Destination for the combined enriched CSV")
    parser.add_argument(
        "--manual-provider",
        action="append",
        default=[],
        help="CSV containing enrichment data (can be passed multiple times)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of verified leads per batch",
    )
    parser.add_argument(
        "--include-unverified",
        action="store_true",
        help="Also emit an Unverified leads.csv file",
    )
    parser.add_argument(
        "--pause-between-batches",
        action="store_true",
        help="Disable auto-continue and pause after each batch",
    )
    parser.add_argument(
        "--report-path",
        help="Optional JSON file with a summary of the enrichment run",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
