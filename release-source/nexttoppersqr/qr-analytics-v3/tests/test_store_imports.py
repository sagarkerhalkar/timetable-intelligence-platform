"""Offline regression tests for official publisher report importer."""
from __future__ import annotations

import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
MODULE = HERE / "scripts" / "import_store_downloads_v3.py"
spec = importlib.util.spec_from_file_location("qr_store_import", MODULE)
tool = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(tool)


class StoreImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "store.sqlite3"

    def test_play_installs_country_utf16_and_idempotence(self):
        file = self.root / "installs_com.example_202610_country.csv"
        file.write_text(
            "Date,Package Name,Country,Daily User Installs\n"
            "2026-10-01,com.example,IN,3\n"
            "2026-10-01,com.example,US,2\n",
            encoding="utf-16")
        self.assertEqual(tool.import_report(file,"play","com.example",self.db), ("imported",2))
        self.assertEqual(tool.import_report(file,"play","com.example",self.db), ("already_imported",2))
        con=sqlite3.connect(self.db)
        try:
            self.assertEqual(con.execute("select sum(count) from official_downloads").fetchone()[0],5)
        finally:
            con.close()

    def test_apple_tsv_types_not_mixed(self):
        file=self.root/"downloads.tsv"
        file.write_text(
            "Date\tApp Apple Identifier\tDownload Type\tTerritory\tCounts\tCampaign\n"
            "2026-10-02\t12345\tFirst Time Download\tIN\t8\tntqr-demo\n"
            "2026-10-02\t12345\tRedownload\tIN\t2\tntqr-demo\n",
            encoding="utf-8")
        self.assertEqual(tool.import_report(file,"apple","12345",self.db),("imported",2))
        con=sqlite3.connect(self.db)
        try:
            self.assertEqual(con.execute(
                "select count(*) from official_downloads where kind='First Time Download'").fetchone()[0],1)
            self.assertEqual(con.execute("select sum(count) from official_downloads").fetchone()[0],10)
        finally:
            con.close()

    def test_dimension_guard(self):
        file=self.root/"installs_com.example_202610_device.csv"
        file.write_text("Date,Package Name,Device,Daily User Installs\n2026-10-01,com.example,x,4\n")
        with self.assertRaisesRegex(ValueError,"country.csv"):
            tool.parse_report(file,"play","com.example")

    def test_app_identity_guard(self):
        file=self.root/"installs_com.example_202610_country.csv"
        file.write_text("Date,Package Name,Country,Daily User Installs\n2026-10-01,com.other,IN,7\n")
        with self.assertRaisesRegex(ValueError,"Unexpected app"):
            tool.parse_report(file,"play","com.example")

    def test_reimport_updated_month_replaces_not_adds(self):
        one=self.root/"installs_com.example_202610_country.csv"
        one.write_text("Date,Package Name,Country,Daily User Installs\n2026-10-01,com.example,IN,3\n")
        two=self.root/"installs_com.example_202611_country.csv"
        two.write_text("Date,Package Name,Country,Daily User Installs\n2026-10-01,com.example,IN,4\n")
        tool.import_report(one,"play","com.example",self.db)
        tool.import_report(two,"play","com.example",self.db)
        con=sqlite3.connect(self.db)
        try:
            self.assertEqual(con.execute("select sum(count) from official_downloads").fetchone()[0],4)
        finally:
            con.close()


if __name__=="__main__":
    unittest.main()
