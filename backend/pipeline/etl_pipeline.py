import time
import datetime
import hashlib
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import RealEstateTransaction, CadastreSection, CrawlerLog
from ..coords import latlon_to_twd97_119
from .crawler import crawler

# Kinmen Town Center Coordinates for geocoding fallback
TOWN_CENTERS = {
    "金寧鄉": {"lat": 24.4550, "lon": 118.3300},
    "金城鎮": {"lat": 24.4327, "lon": 118.3186},
    "金湖鎮": {"lat": 24.4385, "lon": 118.4120},
    "金沙鎮": {"lat": 24.4900, "lon": 118.4150},
    "烈嶼鄉": {"lat": 24.4300, "lon": 118.2350}
}

class ETLPipeline:
    def __init__(self):
        self.crawler = crawler

    def run_sync(self, batch_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute full decennial MOI synchronization pipeline:
        1. Fetch latest MOI decennial open data
        2. Clean, transform, and geocode records
        3. Upsert into database
        4. Log execution details
        """
        start_time = time.time()
        now = datetime.datetime.utcnow()
        if not batch_name:
            roc_year = now.year - 1911
            day_group = 1 if now.day <= 10 else (2 if now.day <= 20 else 3)
            batch_name = f"{roc_year}S{now.month}-旬期{day_group}"

        db: Session = SessionLocal()
        records_fetched = 0
        records_inserted = 0
        records_updated = 0
        status = "SUCCESS"
        error_msg = None

        try:
            print(f">> [ETL] Starting MOI Decennial Sync for batch: {batch_name}...")
            raw_data = self.crawler.fetch_kinmen_decennial_csvs()
            all_raw_rows = raw_data.get("sales", []) + raw_data.get("presale", [])
            records_fetched = len(all_raw_rows)
            print(f">> [ETL] Downloaded {records_fetched} raw Kinmen transaction rows.")

            # Cache known section centers for rapid geocoding
            sections_map = {}
            for s in db.query(CadastreSection).all():
                sections_map[(s.town, s.section_name)] = (s.center_lat, s.center_lon)

            for raw in all_raw_rows:
                transformed = self._transform_row(raw, sections_map)
                if not transformed:
                    continue

                case_id = transformed["case_id"]
                existing = db.query(RealEstateTransaction).filter_by(case_id=case_id).first()

                if existing:
                    # Update fields if needed
                    existing.total_price_wan = transformed["total_price_wan"]
                    existing.unit_ping_wan = transformed["unit_ping_wan"]
                    existing.updated_at = datetime.datetime.utcnow()
                    records_updated += 1
                else:
                    new_item = RealEstateTransaction(**transformed)
                    db.add(new_item)
                    records_inserted += 1

            db.commit()
            print(f">> [ETL] Sync complete: +{records_inserted} new, ~{records_updated} updated.")

        except Exception as e:
            db.rollback()
            status = "FAILED"
            error_msg = str(e)
            print(f">> [ETL ERROR] Sync failed: {e}")

        duration = round(time.time() - start_time, 2)

        # Record crawler log
        try:
            log_entry = CrawlerLog(
                job_name="MOI_DECENNIAL_SYNC",
                batch_period=batch_name,
                records_fetched=records_fetched,
                records_inserted=records_inserted,
                records_updated=records_updated,
                status=status,
                error_message=error_msg,
                duration_seconds=duration,
                executed_at=now
            )
            db.add(log_entry)
            db.commit()
        except Exception as log_err:
            print(f">> [ETL ERROR] Failed to write crawler log: {log_err}")
        finally:
            db.close()

        return {
            "batch_period": batch_name,
            "status": status,
            "records_fetched": records_fetched,
            "records_inserted": records_inserted,
            "records_updated": records_updated,
            "duration_seconds": duration,
            "error": error_msg
        }

    def _transform_row(self, raw: Dict[str, str], sections_map: Dict) -> Optional[Dict[str, Any]]:
        """Transform raw MOI dictionary into RealEstateTransaction kwargs"""
        town = (raw.get("鄉鎮市區") or "").strip()
        addr = (raw.get("土地位置建物門牌") or "").strip()
        if not town or not addr:
            return None

        # Clean town name (ensure 鄉/鎮)
        if not town.endswith(("鄉", "鎮")):
            town = town + "鄉" if town in ["金寧", "金沙", "烈嶼"] else town + "鎮"

        # Unique Case ID
        serial_no = (raw.get("編號") or "").strip()
        if serial_no:
            case_id = f"MOI_{serial_no}"
        else:
            raw_hash = f"{town}_{addr}_{raw.get('交易年月日')}_{raw.get('總價元')}"
            case_id = f"MOI_{hashlib.sha256(raw_hash.encode()).hexdigest()[:16]}"

        # Parse Date & Quarter
        raw_date = (raw.get("交易年月日") or "").strip()
        if len(raw_date) == 7:  # e.g. 1151002
            y, m, d = raw_date[:3], raw_date[3:5], raw_date[5:]
            date_str = f"{y}/{m}/{d}"
            month_int = int(m)
            q = (month_int - 1) // 3 + 1
            quarter_str = f"{y}Q{q}"
        elif len(raw_date) == 6:  # e.g. 991002
            y, m, d = raw_date[:2], raw_date[2:4], raw_date[4:]
            date_str = f"{y}/{m}/{d}"
            month_int = int(m)
            q = (month_int - 1) // 3 + 1
            quarter_str = f"{y}Q{q}"
        else:
            date_str = raw_date or "115/01/01"
            quarter_str = "115Q1"

        # Price conversion
        try:
            total_price_ntd = float(raw.get("總價元") or 0)
            total_price_wan = round(total_price_ntd / 10000.0, 1)
        except ValueError:
            total_price_wan = 0.0

        # Area conversion (Land area or Building area)
        try:
            b_area = float(raw.get("建物移轉總面積平方公尺") or 0)
            l_area = float(raw.get("土地移轉總面積平方公尺") or 0)
            area_sqm = b_area if b_area > 0 else l_area
            area_ping = round(area_sqm * 0.3025, 1)
        except ValueError:
            area_sqm = 0.0
            area_ping = 0.0

        # Unit price conversion
        try:
            unit_sqm = float(raw.get("單價元平方公尺") or 0)
            if unit_sqm > 0:
                unit_ping_wan = round((unit_sqm * 3.305785) / 10000.0, 1)
            elif area_ping > 0 and total_price_wan > 0:
                unit_ping_wan = round(total_price_wan / area_ping, 1)
            else:
                unit_ping_wan = 0.0
        except ValueError:
            unit_ping_wan = 0.0

        # Building type
        b_type = (raw.get("建物型態") or raw.get("交易標的") or "房地(土地+建物)").strip()
        target = (raw.get("交易標的") or "房地(土地+建物)").strip()
        floor = (raw.get("移轉層次") or "").strip()
        total_floors = (raw.get("總樓層數") or "").strip()

        # Coordinates estimation from section name or town center
        lat, lon = self._estimate_coordinates(town, addr, sections_map)
        twd97_x, twd97_y = latlon_to_twd97_119(lat, lon)

        return {
            "case_id": case_id,
            "town": town,
            "section": "",
            "target": target,
            "addr": addr,
            "land_number": "",
            "date": date_str,
            "quarter": quarter_str,
            "total_price_wan": total_price_wan,
            "unit_ping_wan": unit_ping_wan,
            "area_ping": area_ping,
            "area_sqm": area_sqm,
            "b_type": b_type,
            "floor": floor,
            "total_floors": total_floors,
            "age": 0.0,
            "lat": lat,
            "lon": lon,
            "twd97_x": twd97_x,
            "twd97_y": twd97_y,
            "source": "MOI_DECENNIAL"
        }

    def _estimate_coordinates(self, town: str, addr: str, sections_map: Dict) -> (float, float):
        """Estimate location coordinates using cadastral section matching or town centers"""
        # 1. Match section name in address
        for (s_town, s_name), coords in sections_map.items():
            if s_town == town and s_name in addr and coords[0]:
                return coords[0], coords[1]

        # 2. Known local spots
        if "赤岑" in addr: return 24.4628, 118.3275
        if "西堡" in addr: return 24.4596, 118.3386
        if "塔后" in addr: return 24.4421, 118.4196
        if "民族路" in addr: return 24.4346, 118.3195
        if "慈湖路" in addr: return 24.4560, 118.3120
        if "市港" in addr: return 24.4385, 118.4120
        if "料羅" in addr: return 24.4234, 118.4330
        if "湖下" in addr: return 24.4600, 118.3050

        # 3. Town center fallback with slight deterministic jitter based on address
        center = TOWN_CENTERS.get(town, {"lat": 24.4500, "lon": 118.3300})
        hash_val = int(hashlib.md5(addr.encode("utf-8")).hexdigest()[:4], 16)
        lat_offset = ((hash_val % 100) - 50) * 0.0001
        lon_offset = (((hash_val // 100) % 100) - 50) * 0.0001
        return round(center["lat"] + lat_offset, 5), round(center["lon"] + lon_offset, 5)

etl_pipeline = ETLPipeline()
