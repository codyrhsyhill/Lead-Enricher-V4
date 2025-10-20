"""Lightweight Tkinter GUI for running the lead enrichment pipeline."""

from __future__ import annotations

import json
import threading
import queue
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .cli import build_providers
from .io import ensure_master_schema, read_csv_rows, write_csv_rows
from .pipeline import LeadEnrichmentConfig, LeadEnricher, default_output_fields


CONFIG_PATH = Path.home() / ".lead_enricher_gui.json"


@dataclass
class AppConfig:
    last_master: Optional[str] = None
    last_enriched: Optional[str] = None
    last_output_dir: Optional[str] = None
    include_unverified: bool = False

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                return cls(**data)
            except (json.JSONDecodeError, TypeError, OSError):
                return cls()
        return cls()

    def save(self) -> None:
        try:
            CONFIG_PATH.write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")
        except OSError:
            pass


class LeadEnricherApp(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        self.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.config_state = AppConfig.load()
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self._build_ui()
        self._poll_log_queue()

    def _build_ui(self) -> None:
        self.master.title("Lead Enricher (Developer Preview)")
        self.master.geometry("720x480")

        form = ttk.Frame(self)
        form.pack(fill=tk.X, pady=(0, 12))

        self.master_var = tk.StringVar(value=self.config_state.last_master or "")
        self.enriched_var = tk.StringVar(value=self.config_state.last_enriched or "")
        self.manual_var = tk.StringVar()
        self.output_var = tk.StringVar(value=self.config_state.last_output_dir or "")
        self.include_unverified = tk.BooleanVar(value=self.config_state.include_unverified)

        self._add_file_row(form, "Master CSV", self.master_var, self._browse_master)
        self._add_file_row(form, "Enriched to date", self.enriched_var, self._browse_enriched)
        self._add_file_row(form, "Manual provider CSV (optional)", self.manual_var, self._browse_manual)
        self._add_directory_row(form, "Output folder", self.output_var, self._browse_output)

        options = ttk.Frame(self)
        options.pack(fill=tk.X)
        ttk.Checkbutton(
            options,
            text="Include unverified leads",
            variable=self.include_unverified,
        ).pack(side=tk.LEFT)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, pady=(12, 6))
        self.run_button = ttk.Button(actions, text="Run enrichment", command=self._start_run)
        self.run_button.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(actions, textvariable=self.status_var).pack(side=tk.LEFT, padx=(12, 0))

        log_frame = ttk.LabelFrame(self, text="Run log")
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _add_file_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, callback) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text=label, width=28).pack(side=tk.LEFT)
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        ttk.Button(row, text="Browse", command=callback).pack(side=tk.LEFT)

    def _add_directory_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, callback) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text=label, width=28).pack(side=tk.LEFT)
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        ttk.Button(row, text="Choose", command=callback).pack(side=tk.LEFT)

    def _browse_master(self) -> None:
        path = filedialog.askopenfilename(title="Select master CSV", filetypes=[("CSV", "*.csv")])
        if path:
            self.master_var.set(path)

    def _browse_enriched(self) -> None:
        path = filedialog.askopenfilename(title="Select enriched CSV", filetypes=[("CSV", "*.csv")])
        if path:
            self.enriched_var.set(path)

    def _browse_manual(self) -> None:
        path = filedialog.askopenfilename(title="Select manual provider CSV", filetypes=[("CSV", "*.csv")])
        if path:
            self.manual_var.set(path)

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_var.set(path)

    def _start_run(self) -> None:
        master_path = self.master_var.get().strip()
        enriched_path = self.enriched_var.get().strip()
        output_dir = self.output_var.get().strip()
        if not master_path:
            messagebox.showerror("Missing input", "Please select the master CSV file.")
            return
        if not enriched_path:
            messagebox.showerror("Missing input", "Please select the enriched CSV file.")
            return
        if not output_dir:
            messagebox.showerror("Missing output", "Please choose an output folder.")
            return

        self.run_button.configure(state=tk.DISABLED)
        self.status_var.set("Running…")
        self._append_log("Starting enrichment run…")

        config = AppConfig(
            last_master=master_path,
            last_enriched=enriched_path,
            last_output_dir=output_dir,
            include_unverified=self.include_unverified.get(),
        )
        self.config_state = config
        config.save()

        manual = self.manual_var.get().strip()
        args = (master_path, enriched_path, output_dir, manual or None, self.include_unverified.get())
        threading.Thread(target=self._run_pipeline, args=args, daemon=True).start()

    def _run_pipeline(
        self,
        master_path: str,
        enriched_path: str,
        output_dir: str,
        manual_path: Optional[str],
        include_unverified: bool,
    ) -> None:
        try:
            master_rows = read_csv_rows(Path(master_path))
            ensure_master_schema(master_rows)
            enriched_csv = Path(enriched_path)
            enriched_rows = read_csv_rows(enriched_csv) if enriched_csv.exists() else []

            providers = build_providers([Path(manual_path)]) if manual_path else []
            config = LeadEnrichmentConfig(include_unverified=include_unverified)
            enricher = LeadEnricher(providers=providers, config=config)
            verified, unverified = enricher.enrich(master_rows, enriched_rows)

            output_folder = Path(output_dir)
            output_folder.mkdir(parents=True, exist_ok=True)
            combined_path = output_folder / "Completed enriched leads.csv"
            fieldnames = default_output_fields(master_rows)
            write_csv_rows(combined_path, verified, fieldnames=fieldnames)
            self.log_queue.put(f"Wrote {len(verified)} verified rows to {combined_path}")

            if include_unverified and unverified:
                unverified_path = output_folder / "Unverified leads.csv"
                write_csv_rows(unverified_path, unverified, fieldnames=fieldnames)
                self.log_queue.put(
                    f"Wrote {len(unverified)} unverified rows to {unverified_path}"
                )

            self.log_queue.put("Enrichment run completed successfully.")
            self.log_queue.put("__SUCCESS__")
        except Exception as exc:  # pragma: no cover - GUI feedback path
            self.log_queue.put(f"Error: {exc}")
            self.log_queue.put("__ERROR__")

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _poll_log_queue(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if message == "__SUCCESS__":
                self.status_var.set("Done")
                self.run_button.configure(state=tk.NORMAL)
                messagebox.showinfo("Enrichment complete", "Enrichment finished successfully.")
            elif message == "__ERROR__":
                self.status_var.set("Error")
                self.run_button.configure(state=tk.NORMAL)
            else:
                self._append_log(message)
        self.after(200, self._poll_log_queue)


def main() -> None:
    root = tk.Tk()
    LeadEnricherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
