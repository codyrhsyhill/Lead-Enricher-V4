"""PyInstaller-friendly launcher that boots the Lead Enricher GUI."""

from __future__ import annotations

from lead_enricher.gui import main


if __name__ == "__main__":  # pragma: no cover - GUI bootstrap
    main()
