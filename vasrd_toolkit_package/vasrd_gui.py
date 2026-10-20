"""vasrd_gui.py - Clean Tkinter GUI for the VASRD Toolkit.

- Create schema, import from eCFR
- Search and view details
- CSV export
- Dark mode toggle
- Background threading with log pane
"""

import csv
import sqlite3
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .vasrd_schema import create_schema
from .vasrd_scraper import VASRDScraper


def run_gui():
    root = tk.Tk()
    VASRDGUI(root)
    root.mainloop()


class VASRDGUI:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("VASRD Toolkit")
        self.master.geometry("1100x720")

        self.db_path = Path("vasrd.db").resolve()
        self.conn = None
        self.dark = False
        self.log_buffer = []

        self._build_ui()
        self._open_db(self.db_path)
        self._poll_logs()

    def _build_ui(self):
        top = ttk.Frame(self.master, padding=8)
        top.pack(fill="x")

        self.db_label_var = tk.StringVar(value=str(self.db_path))
        ttk.Label(top, text="Database:").pack(side="left")
        ttk.Entry(top, width=60, textvariable=self.db_label_var, state="readonly").pack(side="left", padx=6)
        ttk.Button(top, text="Choose DB", command=self._choose_db).pack(side="left")
        ttk.Button(top, text="New DB", command=self._new_db).pack(side="left")
        ttk.Button(top, text="Integrity", command=self._integrity).pack(side="left")
        ttk.Button(top, text="Backup", command=self._backup).pack(side="left")
        ttk.Button(top, text="Dark Mode", command=self._toggle_dark).pack(side="right")

        mid = ttk.LabelFrame(self.master, text="Import / Schema", padding=8)
        mid.pack(fill="x", padx=8, pady=8)
        self.date_var = tk.StringVar()
        ttk.Label(mid, text="eCFR date (YYYY-MM-DD, optional):").pack(side="left")
        ttk.Entry(mid, width=12, textvariable=self.date_var).pack(side="left", padx=5)
        ttk.Button(mid, text="Create Schema", command=self._create_schema).pack(side="left")
        ttk.Button(mid, text="Import eCFR", command=self._import).pack(side="left")
        ttk.Button(mid, text="Full Reset", command=self._reset).pack(side="left")

        search = ttk.LabelFrame(self.master, text="Search", padding=8)
        search.pack(fill="x", padx=8, pady=8)
        self.search_var = tk.StringVar()
        ttk.Entry(search, width=40, textvariable=self.search_var).pack(side="left")
        ttk.Button(search, text="Search", command=self._search).pack(side="left", padx=6)
        ttk.Button(search, text="Export CSV", command=self._export_csv).pack(side="left", padx=6)

        cols = ("DC Code", "Name", "Body System", "Section", "dc_id")
        self.tree = ttk.Treeview(self.master, columns=cols, show="headings", height=19)
        for c, w in zip(cols, (100, 450, 240, 100, 1)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, stretch=(c != "dc_id"))
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.tree.bind("<Double-1>", self._open_details)

        logf = ttk.LabelFrame(self.master, text="Log", padding=6)
        logf.pack(fill="both", expand=False, padx=8, pady=(0, 8))
        self.log = tk.Text(logf, height=8, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)

    def _open_db(self, path: Path):
        if self.conn:
            self.conn.close()
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.db_path = path
        self.db_label_var.set(str(path))

    def _choose_db(self):
        path = filedialog.askopenfilename(
            title="Select database",
            filetypes=[("SQLite DB", "*.db"), ("All files", "*.*")],
        )
        if path:
            self._open_db(Path(path))

    def _new_db(self):
        path = filedialog.asksaveasfilename(
            title="Create new database",
            defaultextension=".db",
        )
        if not path:
            return
        self._open_db(Path(path))
        create_schema(self.conn)
        messagebox.showinfo("Created", f"New database created:\n{path}")

    def _backup(self):
        import shutil

        self.conn.commit()
        dst = self.db_path.with_suffix(".backup.db")
        shutil.copy2(self.db_path, dst)
        messagebox.showinfo("Backup", f"Backup saved:\n{dst}")

    def _integrity(self):
        result = self.conn.execute("PRAGMA integrity_check;").fetchone()[0]
        messagebox.showinfo("Integrity", result)

    def _create_schema(self):
        create_schema(self.conn)
        messagebox.showinfo("Schema", "Schema created/verified.")

    def _search(self):
        term = self.search_var.get().strip()
        if not term:
            return

        cur = self.conn.cursor()
        rows = cur.execute(
            """
            SELECT dc.dc_code, dc.name, COALESCE(bs.name,''), COALESCE(dc.cfr_section,''), dc.id
            FROM diagnostic_codes dc
            LEFT JOIN body_systems bs ON bs.id = dc.body_system_id
            WHERE CAST(dc.dc_code AS TEXT) LIKE ?
               OR LOWER(dc.name) LIKE LOWER(?)
               OR LOWER(COALESCE(bs.name,'')) LIKE LOWER(?)
            ORDER BY dc.dc_code
            """,
            (f"%{term}%", f"%{term}%", f"%{term}%"),
        ).fetchall()

        for i in self.tree.get_children():
            self.tree.delete(i)
        for row in rows:
            self.tree.insert("", "end", values=row)

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Save CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return

        rows = [self.tree.item(i, "values") for i in self.tree.get_children()]
        if not rows:
            messagebox.showinfo("No Data", "No rows to export.")
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["DC Code", "Name", "Body System", "CFR Section", "DC ID"])
            writer.writerows(rows)

        messagebox.showinfo("Export Complete", f"Saved to:\n{path}")

    def _open_details(self, _event):
        selection = self.tree.focus()
        if not selection:
            return
        dc, name, body_system, section, dc_id = self.tree.item(selection, "values")

        cur = self.conn.cursor()
        ratings = cur.execute(
            """
            SELECT percentage, criteria_text
            FROM rating_criteria
            WHERE dc_id=?
            ORDER BY percentage DESC
            """,
            (dc_id,),
        ).fetchall()

        notes = cur.execute(
            """
            SELECT note_number, note_text
            FROM dc_notes
            WHERE dc_id=?
            ORDER BY note_number
            """,
            (dc_id,),
        ).fetchall()

        window = tk.Toplevel(self.master)
        window.title(f"Diagnostic Code {dc}")
        window.geometry("860x600")

        text_widget = tk.Text(window, wrap="word")
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("end", f"DC: {dc}\nName: {name}\nBody System: {body_system}\nSection: {section}\n\n")
        text_widget.insert("end", "=== Rating Criteria ===\n")
        for pct, txt in ratings:
            text_widget.insert("end", f"[{pct}%] {txt}\n")
        text_widget.insert("end", "\n=== Notes ===\n")
        if notes:
            for num, txt in notes:
                label = f"Note {num}" if num else "Note"
                text_widget.insert("end", f"{label}: {txt}\n")
        else:
            text_widget.insert("end", "No notes recorded.\n")
        text_widget.config(state="disabled")

    def _toggle_dark(self):
        self.dark = not self.dark
        if self.dark:
            style = ttk.Style()
            style.theme_use("default")
            style.configure(".", background="#1e1e1e", foreground="#e5e5e5")
            style.configure("Treeview", background="#2e2e2e", fieldbackground="#2e2e2e", foreground="#e5e5e5")
            self.master.configure(background="#1e1e1e")
            self.log.configure(background="#2e2e2e", foreground="#e5e5e5")
        else:
            ttk.Style().theme_use("clam")
            self.master.configure(background=None)
            self.log.configure(background="white", foreground="black")

    def _import(self):
        self._run_task(self._do_import)

    def _reset(self):
        self._run_task(self._do_reset)

    def _run_task(self, fn):
        def worker():
            error = None
            try:
                fn()
            except Exception as exc:  # pragma: no cover - UI path only
                error = exc
                self._log(f"ERROR: {exc}")
            self.master.after(0, self._task_done, error)

        threading.Thread(target=worker, daemon=True).start()

    def _task_done(self, error):
        if error:
            messagebox.showerror("Task failed", str(error))
        else:
            messagebox.showinfo("Done", f"Database: {self.db_path}")

    def _do_import(self):
        if self.conn:
            self.conn.close()
            self.conn = None

        date_value = self.date_var.get().strip() or datetime.utcnow().strftime("%Y-%m-%d")
        self._log(f"Importing from eCFR (date={date_value}) ...")
        scraper = VASRDScraper(self.db_path, logger=self._log)
        try:
            count = scraper.import_vasrd(date_value)
            self._log(f"Import complete. Ratings added: {count}")
        finally:
            scraper.close()
        self._open_db(self.db_path)

    def _do_reset(self):
        import shutil

        self._log("Reset: backing up and recreating schema ...")
        if self.conn:
            self.conn.close()
            self.conn = None

        backup = self.db_path.with_suffix(".reset_backup.db")
        if self.db_path.exists():
            shutil.copy2(self.db_path, backup)
            self._log(f"Backup: {backup}")
            self.db_path.unlink()

        self._open_db(self.db_path)
        create_schema(self.conn)
        self._do_import()

    def _log(self, message: str):
        self.log_buffer.append(message)

    def _poll_logs(self):
        if self.log_buffer:
            self.log.config(state="normal")
            for item in self.log_buffer:
                self.log.insert("end", item + "\n")
            self.log.see("end")
            self.log.config(state="disabled")
            self.log_buffer.clear()
        self.master.after(120, self._poll_logs)
