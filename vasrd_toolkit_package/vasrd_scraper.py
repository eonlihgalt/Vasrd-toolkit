"""
vasrd_scraper.py
Embedded VASRD (38 CFR Part 4) scraper using the eCFR API.
- Simplified regex
- Safe network retries
- Thread-safe SQLite
"""

from pathlib import Path
import re
import sqlite3
import time

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from vasrd_schema import create_schema

SECTION_RE = re.compile(r"§\s*4\.\s*([0-9A-Za-z]+)")
DC_RE      = re.compile(r"(\d{4})\s+(.+)")
PCT_RE     = re.compile(r"^\s*(100|70|60|50|40|30|20|10|0)", re.I)
NOTE_RE    = re.compile(r"^note\s*(?:\(?(\d+)\)?)?\s*:\s*(.+)$", re.I)

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
        s = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504], allowed_methods=["GET"])
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))
        return s

    def _prep_indexes(self):
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_dc_code ON diagnostic_codes(dc_code);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_rc_dc ON rating_criteria(dc_id);")
        self.conn.commit()

    def fetch_xml(self, date_str: str):
        url = self.BASE + self.PATH.format(date=date_str)
        self.log(f"Fetching eCFR XML for {date_str} …")
        try:
            r = self.session.get(url, timeout=60)
            r.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Network error fetching eCFR: {e}")
        try:
            return etree.fromstring(r.content)
        except Exception as e:
            raise RuntimeError(f"Invalid XML returned by eCFR: {e}")

    def import_vasrd(self, date_str: str):
        root = self.fetch_xml(date_str)
        bs_map = {
            "§ 4.71a": self.ensure_body_system("The Musculoskeletal System", "§ 4.71a"),
            "§ 4.87":  self.ensure_body_system("Impairment of Auditory Acuity (Ear)", "§ 4.87"),
            "§ 4.130": self.ensure_body_system("Mental Disorders", "§ 4.130"),
        }
        default_bs = bs_map["§ 4.71a"]

        sec_count = 0
        crit_count = 0
        last_commit = time.time()

        for head, sec, text in self.iter_sections(root):
            sec_count += 1
            m = SECTION_RE.search(head)
            if not m:
                continue
            section = f"§ 4.{m.group(1)}"

            lines = self.table_lines(sec)
            if not lines:
                lines = [ln.strip() for ln in re.split(r"[
;]+", text) if ln.strip()]

            for line in lines:
                dcm = DC_RE.search(line)
                if not dcm:
                    continue
                dc_code = int(dcm.group(1))
                name = dcm.group(2).strip()
                bs_id = bs_map.get(section, default_bs)

                dc_id = self.ensure_dc(dc_code, name, bs_id, section)

                for ln in lines:
                    pct = PCT_RE.match(ln)
                    if pct:
                        self.add_rating(dc_id, int(pct.group(1)), ln)
                        crit_count += 1

                for ln in lines:
                    nm = NOTE_RE.match(ln)
                    if nm:
                        num = int(nm.group(1)) if nm.group(1) else None
                        self.add_note(dc_id, num, nm.group(2))

            if time.time() - last_commit > 2:
                self.conn.commit()
                last_commit = time.time()

        self.conn.commit()
        self.log(f"Parsed sections: {sec_count}; ratings added: {crit_count}")
        return crit_count

    @staticmethod
    def iter_sections(root):
        for sec in root.xpath(".//DIV[starts-with(@TYPE,'SECTION') or @TYPE='SECTION']"):
            head = "".join(sec.xpath(".//HEAD//text()")) or "".join(sec.xpath(".//SECTNO//text()"))
            text = " ".join(sec.xpath(".//P//text()"))
            yield head.strip(), sec, text

    @staticmethod
    def table_lines(sec):
        lines = []
        for row in sec.xpath(".//TABLE//ROW"):
            txt = " ".join(row.xpath(".//text()"))
            txt = re.sub(r"\s+", " ", txt).strip()
            if txt:
                lines.append(txt)
        return lines

    def ensure_body_system(self, name, cfr_section):
        cur = self.conn.execute("SELECT id FROM body_systems WHERE name=?", (name,))
        r = cur.fetchone()
        if r:
            return r[0]
        cur = self.conn.execute("INSERT INTO body_systems(name, cfr_section) VALUES(?,?)", (name, cfr_section))
        self.conn.commit()
        return cur.lastrowid

    def ensure_dc(self, code, name, body_system_id, section):
        cur = self.conn.execute("SELECT id FROM diagnostic_codes WHERE dc_code=?", (code,))
        r = cur.fetchone()
        if r:
            self.conn.execute(
                "UPDATE diagnostic_codes SET name=?, body_system_id=?, cfr_section=? WHERE id=?",
                (name, body_system_id, section, r[0])
            )
            self.conn.commit()
            return r[0]
        cur = self.conn.execute(
            "INSERT INTO diagnostic_codes(dc_code, name, body_system_id, cfr_section) VALUES(?,?,?,?)",
            (code, name, body_system_id, section)
        )
        self.conn.commit()
        return cur.lastrowid

    def add_rating(self, dc_id, pct, text):
        cur = self.conn.execute(
            "SELECT 1 FROM rating_criteria WHERE dc_id=? AND percentage=? AND criteria_text=?",
            (dc_id, pct, text.strip())
        )
        if not cur.fetchone():
            self.conn.execute(
                "INSERT INTO rating_criteria(dc_id, percentage, criteria_text) VALUES(?,?,?)",
                (dc_id, pct, text.strip())
            )

    def add_note(self, dc_id, num, text):
        cur = self.conn.execute(
            "SELECT 1 FROM dc_notes WHERE dc_id=? AND COALESCE(note_number,'')=COALESCE(?, '') AND note_text=?",
            (dc_id, num, text.strip())
        )
        if not cur.fetchone():
            self.conn.execute(
                "INSERT INTO dc_notes(dc_id, note_number, note_text) VALUES(?,?,?)",
                (dc_id, num, text.strip())
            )

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
