"""vasrd_scraper.py
Embedded VASRD (38 CFR Part 4) scraper using the eCFR API.
- Simplified regex
- Safe network retries
- Thread-safe SQLite
"""

import re
import sqlite3
import time
from pathlib import Path

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .vasrd_schema import create_schema

SECTION_RE = re.compile(r"§\s*4\.\s*([0-9A-Za-z]+)")
DC_RE = re.compile(r"(\d{4})\s+(.+)")
PCT_RE = re.compile(r"^\s*(100|70|60|50|40|30|20|10|0)\s*(?:%|percent)?\b", re.I)
NOTE_RE = re.compile(r"^note\s*(?:\(?(\d+)\)?)?\s*:\s*(.+)$", re.I)


class VASRDScraper:
    BASE = "https://www.ecfr.gov"
    PATH = "/api/versioner/v1/full/{date}/title-38/part-4.xml"

    def __init__(self, db_path: Path, logger=None):
        self.db_path = Path(db_path)
        self.log = logger or (lambda *_: None)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys=ON;")
        create_schema(self.conn)
        self.session = self._build_session()
        self._prep_indexes()

    def _build_session(self):
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.mount("http://", HTTPAdapter(max_retries=retry))
        return session

    def _prep_indexes(self):
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_dc_code ON diagnostic_codes(dc_code);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_rc_dc ON rating_criteria(dc_id);")
        self.conn.commit()

    def fetch_xml(self, date_str: str):
        url = self.BASE + self.PATH.format(date=date_str)
        self.log(f"Fetching eCFR XML for {date_str} ...")
        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network path
            raise RuntimeError(f"Network error fetching eCFR: {exc}") from exc

        try:
            return etree.fromstring(response.content)
        except Exception as exc:  # pragma: no cover - malformed XML path
            raise RuntimeError(f"Invalid XML returned by eCFR: {exc}") from exc

    def import_vasrd(self, date_str: str):
        root = self.fetch_xml(date_str)
        body_system_map = {
            "§ 4.71a": self.ensure_body_system("The Musculoskeletal System", "§ 4.71a"),
            "§ 4.87": self.ensure_body_system("Impairment of Auditory Acuity (Ear)", "§ 4.87"),
            "§ 4.130": self.ensure_body_system("Mental Disorders", "§ 4.130"),
        }
        default_body_system = body_system_map["§ 4.71a"]

        section_count = 0
        rating_count = 0
        last_commit = time.time()

        for head, section_node, text in self.iter_sections(root):
            section_count += 1
            match = SECTION_RE.search(head)
            if not match:
                continue
            section = f"§ 4.{match.group(1)}"

            lines = self.table_lines(section_node)
            if not lines:
                lines = [line.strip() for line in re.split(r"[\n;]+", text) if line.strip()]

            for line in lines:
                dc_match = DC_RE.search(line)
                if not dc_match:
                    continue
                dc_code = int(dc_match.group(1))
                name = dc_match.group(2).strip()
                body_system_id = body_system_map.get(section, default_body_system)
                dc_id = self.ensure_dc(dc_code, name, body_system_id, section)

                for candidate in lines:
                    pct_match = PCT_RE.match(candidate)
                    if pct_match:
                        self.add_rating(dc_id, int(pct_match.group(1)), candidate.strip())
                        rating_count += 1

                for candidate in lines:
                    note_match = NOTE_RE.match(candidate)
                    if note_match:
                        note_number = int(note_match.group(1)) if note_match.group(1) else None
                        self.add_note(dc_id, note_number, note_match.group(2))

            if time.time() - last_commit > 2:
                self.conn.commit()
                last_commit = time.time()

        self.conn.commit()
        self.log(f"Parsed sections: {section_count}; ratings added: {rating_count}")
        return rating_count

    @staticmethod
    def iter_sections(root):
        for section in root.xpath(".//DIV[starts-with(@TYPE,'SECTION') or @TYPE='SECTION']"):
            head = "".join(section.xpath(".//HEAD//text()")) or "".join(section.xpath(".//SECTNO//text()"))
            text = " ".join(section.xpath(".//P//text()"))
            yield head.strip(), section, text

    @staticmethod
    def table_lines(section_node):
        lines = []
        for row in section_node.xpath(".//TABLE//ROW"):
            text = " ".join(row.xpath(".//text()"))
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                lines.append(text)
        return lines

    def ensure_body_system(self, name, cfr_section):
        row = self.conn.execute("SELECT id FROM body_systems WHERE name=?", (name,)).fetchone()
        if row:
            return row[0]
        cursor = self.conn.execute(
            "INSERT INTO body_systems(name, cfr_section) VALUES(?, ?)",
            (name, cfr_section),
        )
        self.conn.commit()
        return cursor.lastrowid

    def ensure_dc(self, code, name, body_system_id, section):
        row = self.conn.execute("SELECT id FROM diagnostic_codes WHERE dc_code=?", (code,)).fetchone()
        if row:
            self.conn.execute(
                "UPDATE diagnostic_codes SET name=?, body_system_id=?, cfr_section=? WHERE id=?",
                (name, body_system_id, section, row[0]),
            )
            self.conn.commit()
            return row[0]
        cursor = self.conn.execute(
            "INSERT INTO diagnostic_codes(dc_code, name, body_system_id, cfr_section) VALUES(?,?,?,?)",
            (code, name, body_system_id, section),
        )
        self.conn.commit()
        return cursor.lastrowid

    def add_rating(self, dc_id, pct, text):
        cursor = self.conn.execute(
            "SELECT 1 FROM rating_criteria WHERE dc_id=? AND percentage=? AND criteria_text=?",
            (dc_id, pct, text.strip()),
        )
        if not cursor.fetchone():
            self.conn.execute(
                "INSERT INTO rating_criteria(dc_id, percentage, criteria_text) VALUES(?,?,?)",
                (dc_id, pct, text.strip()),
            )

    def add_note(self, dc_id, num, text):
        cursor = self.conn.execute(
            "SELECT 1 FROM dc_notes WHERE dc_id=? AND COALESCE(note_number,'')=COALESCE(?, '') AND note_text=?",
            (dc_id, num, text.strip()),
        )
        if not cursor.fetchone():
            self.conn.execute(
                "INSERT INTO dc_notes(dc_id, note_number, note_text) VALUES(?,?,?)",
                (dc_id, num, text.strip()),
            )

    def close(self):
        try:
            self.conn.close()
        except Exception:  # pragma: no cover - close guard
            pass
