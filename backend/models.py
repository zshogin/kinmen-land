import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Index
from .database import Base

class CadastreSection(Base):
    """金門全縣 250 地段目錄模型"""
    __tablename__ = "cadastre_sections"

    id = Column(Integer, primary_key=True, index=True)
    town = Column(String(50), nullable=False, index=True)
    section_name = Column(String(100), nullable=False, index=True)
    section_code = Column(String(20), nullable=False, index=True)
    center_lat = Column(Float, nullable=True)
    center_lon = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_section_town_code", "town", "section_code"),
    )

class RealEstateTransaction(Base):
    """內政部實價登錄成交明細模型"""
    __tablename__ = "real_estate_transactions"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(100), unique=True, index=True, nullable=False) # 唯一去重雜湊
    town = Column(String(50), nullable=False, index=True)
    section = Column(String(100), nullable=True, index=True)
    target = Column(String(100), nullable=True)  # 房地(土地+建物)、土地、車位等
    addr = Column(String(255), nullable=False, index=True)
    land_number = Column(String(50), nullable=True, index=True)
    date = Column(String(20), nullable=False, index=True)  # 民國日期 115/10/12
    quarter = Column(String(20), nullable=False, index=True)  # 115Q4
    total_price_wan = Column(Float, nullable=False)  # 總價 (萬元)
    unit_ping_wan = Column(Float, nullable=False)  # 單價 (萬/坪)
    area_ping = Column(Float, nullable=False)  # 坪數
    area_sqm = Column(Float, nullable=False)  # 平方公尺
    b_type = Column(String(100), nullable=False, index=True)  # 透天厝、公寓、住宅大樓等
    floor = Column(String(50), nullable=True)  # 交易樓層
    total_floors = Column(String(50), nullable=True)  # 總樓層數
    age = Column(Float, nullable=True)  # 屋齡 (年)
    lat = Column(Float, nullable=False, index=True)  # WGS84 緯度
    lon = Column(Float, nullable=False, index=True)  # WGS84 經度
    twd97_x = Column(Float, nullable=True)  # TWD97 TM2 119 橫坐標
    twd97_y = Column(Float, nullable=True)  # TWD97 TM2 119 縱坐標
    source = Column(String(50), default="MOI_DECENNIAL")  # 資料來源
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_re_town_quarter", "town", "quarter"),
        Index("idx_re_lat_lon", "lat", "lon"),
    )

class FarmlandAuditRecord(Base):
    """農地分割與農舍興建資格合規檢測查詢紀錄"""
    __tablename__ = "farmland_audit_records"

    id = Column(Integer, primary_key=True, index=True)
    town = Column(String(50), nullable=False)
    section = Column(String(100), nullable=True)
    land_number = Column(String(50), nullable=True)
    area_sqm = Column(Float, nullable=False)
    area_ping = Column(Float, nullable=False)
    qualification_type = Column(String(50), nullable=False)  # 老農 / 新農
    has_road_access = Column(Boolean, default=True)
    is_national_park = Column(Boolean, default=False)
    compliance_status = Column(String(50), nullable=False)  # COMPLIANT, RESTRICTED, NON_COMPLIANT
    max_base_area_sqm = Column(Float, nullable=False)
    max_floor_area_sqm = Column(Float, nullable=False)
    agri_preserve_sqm = Column(Float, nullable=False)
    can_subdivide = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CrawlerLog(Base):
    """內政部實價登錄自動排程同步日誌模型"""
    __tablename__ = "crawler_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(100), nullable=False)
    batch_period = Column(String(50), nullable=False)  # 例如: 115S4-旬期2
    records_fetched = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    status = Column(String(20), default="SUCCESS")  # SUCCESS, FAILED
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)

class User(Base):
    """使用者帳號與角色權限模型 (RBAC)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    agency = Column(String(100), nullable=True) # 單位或事務所
    role = Column(String(30), nullable=False, default="guest", index=True) # admin, auditor, professional, guest
    status = Column(String(20), default="active", nullable=False) # active, disabled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class AuditLog(Base):
    """系統操作與資安稽核日誌模型"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True) # LOGIN, PARCEL_SEARCH, REPORT_EXPORT, PIPELINE_SYNC, USER_UPDATE
    target = Column(String(255), nullable=True) # 操作目標 (如地號、報表、用戶)
    ip_address = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

