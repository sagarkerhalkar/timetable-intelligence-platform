"""Standalone QR reporting contract tests against a synthetic SQLite DB.

No production database or running server is accessed.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "services/api/app/api/qr_reporting_v3.py"


def load_module():
    for name in ("qr_fixture", "qr_fixture.api"):
        module=types.ModuleType(name)
        module.__path__=[]
        sys.modules[name]=module
    d=types.ModuleType("qr_fixture.database")
    d.Database=object
    sys.modules[d.__name__]=d
    d=types.ModuleType("qr_fixture.dependencies")
    d.get_database=lambda: None
    sys.modules[d.__name__]=d
    spec=importlib.util.spec_from_file_location("qr_fixture.api.qr_reporting_v3",FILE)
    module=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


class FakeDatabase:
    def __init__(self,path):
        self.path=path

    def get_qr_code(self,qr_id):
        return qr_id if qr_id=="qr-a" else None


class ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=load_module()

    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db=Path(tmp.name)/"timetable.db"
        con=sqlite3.connect(self.db)
        try:
            con.executescript("""
                CREATE TABLE qr_codes(id TEXT PRIMARY KEY,name TEXT);
                CREATE TABLE qr_scans(
                    id INTEGER PRIMARY KEY, qr_id TEXT, scanned_at TEXT,
                    visitor_hash TEXT, confirmed INTEGER, country TEXT,
                    device_type TEXT, operating_system TEXT, browser TEXT,
                    device_model TEXT, telemetry_json TEXT
                );
                INSERT INTO qr_codes VALUES ('qr-a','A'),('qr-b','B');
            """)
            geo=json.dumps({"edge":{"country":"IN","region":"Madhya Pradesh","city":"Bhopal"}})
            rows=[
                ("qr-a","2026-10-01T12:00:00Z","abc123456789abcdef",1,"IN","Mobile","Android","Chrome","",geo),
                ("qr-a","2026-10-02T12:00:00Z","abc123456789abcdef",1,"IN","Mobile","Android","Chrome","",geo),
                ("qr-b","2026-10-03T12:00:00Z","zz123456789abcdef",0,"US","Desktop","Windows","Edge","",json.dumps({})),
            ]
            con.executemany("""
                INSERT INTO qr_scans(qr_id,scanned_at,visitor_hash,confirmed,country,
                  device_type,operating_system,browser,device_model,telemetry_json)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """,rows)
            con.commit()
        finally:
            con.close()
        self.fake=FakeDatabase(self.db)

    def test_verified_geo_district_not_guessed(self):
        report=self.api.summary(qr_id=None,database=self.fake)
        self.assertEqual(report["verified_scans"],2)
        self.assertEqual(report["unique_browsers"],1)
        self.assertEqual(report["locations"][0]["country"],"IN")
        self.assertEqual(report["locations"][0]["state"],"Madhya Pradesh")
        self.assertEqual(report["locations"][0]["city"],"Bhopal")
        self.assertEqual(report["locations"][0]["district"],"Unknown")
        self.assertEqual(report["devices"][0]["scans"],2)

    def test_qr_scoping(self):
        report=self.api.summary(qr_id="qr-a",database=self.fake)
        self.assertEqual(report["verified_scans"],2)
        self.assertEqual(len(report["qr_codes"]),1)

    def test_streamed_csv_excludes_legacy(self):
        resp=self.api.export_scans(qr_id=None,database=self.fake)
        async def collect():
            parts=[]
            async for item in resp.body_iterator:
                parts.append(item)
            return "".join(p.decode() if isinstance(p,bytes) else p for p in parts)
        output=asyncio.run(collect())
        self.assertIn("Madhya Pradesh",output)
        self.assertNotIn("qr-b",output)
        self.assertEqual(len(output.strip().splitlines()),3)

    def test_pdf_signature(self):
        resp=self.api.export_pdf(qr_id=None,database=self.fake)
        self.assertTrue(resp.body.startswith(b"%PDF"))

    def test_store_unconnected_no_fabricated_totals(self):
        report=self.api.store_stats(database=self.fake)
        self.assertEqual(report["status"],"not_connected")
        self.assertEqual(report["verified_store_downloads"],[])


if __name__=="__main__":
    unittest.main()
