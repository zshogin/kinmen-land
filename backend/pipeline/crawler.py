import io
import ssl
import csv
import zipfile
import urllib.request
from typing import List, Dict, Any, Optional

MOI_DECENNIAL_URL = "https://plvr.land.moi.gov.tw/Download?type=zip&fileName=lvr_landcsv.zip"

class MOICrawler:
    def __init__(self, download_url: str = MOI_DECENNIAL_URL):
        self.download_url = download_url
        self.ssl_context = ssl._create_unverified_context()

    def fetch_kinmen_decennial_csvs(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Download the latest decennial MOI open data zip file
        and extract Kinmen County CSV files (county code 'W').
        Returns dictionary of parsed rows for 'sales' (w_lvr_land_a) and 'presale' (w_lvr_land_b).
        """
        req = urllib.request.Request(
            self.download_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KinmenLandCloud/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=45) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"MOI returned HTTP status {resp.status}")
                zip_data = resp.read()
        except Exception as e:
            raise RuntimeError(f"Failed to download MOI zip: {e}")

        results = {
            "sales": [],
            "presale": []
        }

        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                namelist = zf.namelist()
                for fname in namelist:
                    lower = fname.lower()
                    if lower.endswith("w_lvr_land_a.csv"):
                        content = zf.read(fname).decode("utf-8-sig", errors="ignore")
                        results["sales"] = self._parse_csv_content(content)
                    elif lower.endswith("w_lvr_land_b.csv"):
                        content = zf.read(fname).decode("utf-8-sig", errors="ignore")
                        results["presale"] = self._parse_csv_content(content)
        except Exception as e:
            raise RuntimeError(f"Failed to decompress MOI zip archive: {e}")

        return results

    def _parse_csv_content(self, csv_text: str) -> List[Dict[str, str]]:
        """Parse MOI CSV text into list of dicts, skipping the secondary English header line"""
        lines = csv_text.splitlines()
        if len(lines) < 2:
            return []

        # Line 0: Chinese headers
        # Line 1: English column definitions (skip)
        # Line 2+: Data rows
        header_line = lines[0]
        data_lines = [header_line] + lines[2:]

        reader = csv.DictReader(data_lines)
        rows = []
        for row in reader:
            if not row or not any(row.values()):
                continue
            rows.append(row)
        return rows

crawler = MOICrawler()
