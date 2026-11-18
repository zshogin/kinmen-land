import os
import json
import hashlib
from .database import engine, Base, SessionLocal
from .models import CadastreSection, RealEstateTransaction, FarmlandAuditRecord, CrawlerLog

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generate_case_id(item: dict, idx: int = 0) -> str:
    """Generate reproducible unique case ID for deduplication"""
    raw_str = f"{item.get('town')}_{item.get('addr')}_{item.get('date')}_{item.get('total_price_wan')}_{item.get('area_ping')}_{item.get('floor')}_{idx}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]

def init_database(seed_data: bool = True):
    print(">> Initializing Database Schema...")
    Base.metadata.create_all(bind=engine)
    print(">> Tables created successfully!")

    if not seed_data:
        return

    db = SessionLocal()
    try:
        # 1. Seed Cadastre Sections
        sections_count = db.query(CadastreSection).count()
        if sections_count == 0:
            sections_path = os.path.join(BASE_DIR, "kinmen_sections.json")
            if os.path.exists(sections_path):
                print(">> Seeding Cadastre Sections from kinmen_sections.json...")
                with open(sections_path, "r", encoding="utf-8") as f:
                    sections_dict = json.load(f)

                batch = []
                for town, s_list in sections_dict.items():
                    for s in s_list:
                        batch.append(CadastreSection(
                            town=town,
                            section_name=s.get("name"),
                            section_code=s.get("code")
                        ))
                db.bulk_save_objects(batch)
                db.commit()
                print(f"   -> Seeded {len(batch)} cadastre sections across Kinmen!")
            else:
                print(f"   ! File not found: {sections_path}")
        else:
            print(f">> Cadastre sections already populated ({sections_count} rows).")

        # 2. Seed Real Estate Transactions
        re_count = db.query(RealEstateTransaction).count()
        if re_count == 0:
            re_path = os.path.join(BASE_DIR, "kinmen_real_estate.json")
            if os.path.exists(re_path):
                print(">> Seeding Real Estate Transactions from kinmen_real_estate.json...")
                with open(re_path, "r", encoding="utf-8") as f:
                    items = json.load(f)

                batch = []
                for idx, item in enumerate(items):
                    case_id = generate_case_id(item, idx)
                    batch.append(RealEstateTransaction(
                        case_id=case_id,
                        town=item.get("town", "金寧鄉"),
                        section=item.get("section", ""),
                        target=item.get("target", "房地(土地+建物)"),
                        addr=item.get("addr", ""),
                        land_number=item.get("land_number", ""),
                        date=item.get("date", "115/01/01"),
                        quarter=item.get("quarter", "115Q1"),
                        total_price_wan=float(item.get("total_price_wan", 0)),
                        unit_ping_wan=float(item.get("unit_ping_wan", 0)),
                        area_ping=float(item.get("area_ping", 0)),
                        area_sqm=float(item.get("area_sqm", 0)),
                        b_type=item.get("b_type", "透天厝"),
                        floor=item.get("floor", "全棟"),
                        total_floors=item.get("total_floors", "3"),
                        age=float(item.get("age", 0)) if item.get("age") is not None else 0.0,
                        lat=float(item.get("lat", 24.45)),
                        lon=float(item.get("lon", 118.33)),
                        twd97_x=float(item.get("twd97_x", 0)),
                        twd97_y=float(item.get("twd97_y", 0)),
                        source="SEED_JSON"
                    ))
                db.bulk_save_objects(batch)
                db.commit()
                print(f"   -> Seeded {len(batch)} real estate transactions successfully!")
            else:
                print(f"   ! File not found: {re_path}")
        else:
            print(f">> Real estate transactions already populated ({re_count} rows).")

    except Exception as e:
        db.rollback()
        print(f"Error during database initialization: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
