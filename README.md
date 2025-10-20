# Lead Enricher V4 (Developer Preview)

This repository provides a Python-based scaffolding for enriching UK roofing business leads
in batches of 20 verified contacts. It does **not** ship the zero-code macOS desktop
application requested in the original brief. Instead, it offers a reproducible foundation for
building the enrichment logic that such an application would embed.

## What is included?

- A pluggable enrichment pipeline (`LeadEnricher`) that enforces the resume, batching, and
  deduplication rules described in the brief.
- CSV I/O utilities with schema validation and atomic writes.
- Normalisation helpers for lead IDs, UK phone numbers, email addresses, roles, and key
  Companies House fields.
- A provider interface plus a reference `ManualProvider` that can source enrichment data from
  a user-maintained CSV (useful for dry runs or manual QA).
- A command line interface that ties the pieces together so you can test the workflow without
  a GUI.

## What is not included?

- No Electron/Tauri frontend or macOS packaging.
- No automated data sourcing from live services (websites, GBP, Companies House, etc.).
- No code signing or notarisation.

These omissions are deliberate—producing a notarised macOS build and automating proprietary
data sourcing is outside the scope of what can be delivered here. The provided code aims to be
transparent and easy to extend so a dedicated team can implement the missing components.

## Quick start (CLI)

```bash
# 1. Clone the repo (if you have not already) and enter it
git clone https://github.com/codyrhsyhill/Lead-Enricher-V4.git
cd Lead-Enricher-V4

# 2. Confirm the system exposes a "python3" interpreter (required on macOS)
which python3

# 3. Create and activate a virtual environment with that interpreter
python3 -m venv .venv
source .venv/bin/activate

# 4. Install the project **from inside the cloned repo**
python3 -m pip install --upgrade pip
python3 -m pip install -e .

# 5. Run the enrichment CLI (module form avoids PATH issues)
python3 -m lead_enricher.cli \
  businesses_without_contact.csv enriched_to_date.csv output.csv \
  --manual-provider my_enrichment.csv --include-unverified
```

> **Troubleshooting:**
>
> - If you see `zsh: command not found: python`, macOS only exposes `python3`; the
>   quick-start commands above use `python3` everywhere to avoid that error.
> - If you receive `ERROR: file:///Users/<name> does not appear to be a Python` it
>   means `python3 -m pip install -e .` was executed outside the repository root.
>   Run `pwd` to verify you are inside `Lead-Enricher-V4` before retrying.
> - After installation you *may* call the convenience script `lead-enricher …` from
>   the virtual environment, but the module form (`python3 -m lead_enricher.cli …`)
>   always works even if your shell does not expose the script on `PATH`.

### Optional desktop-friendly launcher (Tkinter)

If you prefer a basic point-and-click experience, you can run the experimental Tkinter
wrapper after installing the package:

```bash
python3 -m lead_enricher.gui
```

The window lets you browse for the master and progress CSV files, choose an output folder,
toggle whether unverified rows should be exported, and review the run log. The GUI remembers
your last-used file locations between runs via `~/.lead_enricher_gui.json`.

Arguments:

- `businesses_without_contact.csv`: The master lead list.
- `enriched_to_date.csv`: Any previous progress (optional; pass an empty file if none).
- `output.csv`: Destination for the combined, verified rows.
- `--manual-provider`: One or more CSV files that contain enrichment columns. These feed the
  `ManualProvider` and act as stand-ins for automated lookups.
- `--include-unverified`: Also write an `Unverified leads.csv` file next to the main output.
- `--pause-between-batches`: Disable auto-continue to inspect each batch manually.

The CLI prints a summary once the run completes. You can also provide `--report-path` to emit a
JSON summary (batch size, auto-continue state, counts).

### Build a double-clickable macOS app bundle (PyInstaller)

If you want a Finder-friendly app you can launch like any other macOS application, use the
provided build helper on an Apple machine:

```bash
# From inside the cloned repo, with your virtual environment active
python3 -m pip install --upgrade pip
python3 -m pip install -e .
python3 -m pip install pyinstaller

# Create Lead Enricher.app under dist/ and a ready-to-share ZIP alongside the repo
python3 scripts/build_mac_app.py
```

The script invokes PyInstaller in windowed mode, producing `dist/Lead Enricher.app` and
`Lead-Enricher-mac.zip`. Drag the `.app` into `/Applications` (or any folder you prefer) and
double-click it to launch the GUI. Because the bundle is unsigned, the first launch may require
Control-click → Open to confirm you trust the app.

After the first run the GUI remembers the last-used CSV paths and output folder so subsequent
launches are one-click.

## Extending the pipeline

1. Implement custom providers by inheriting from `lead_enricher.providers.base.BaseProvider` and
   returning a `ProviderResult`.
2. Wire the provider into the CLI (or your GUI) similarly to how `ManualProvider` is registered.
3. Replace the CLI with a GUI front-end (Electron/Tauri) that calls into the same pipeline.
4. Implement macOS packaging, signing, and notarisation around the finished app.

## Testing notes

Unit tests are not included, but the code is intentionally modular to simplify future test
coverage. Focus on mocking provider responses to exercise the batching and deduplication rules.
