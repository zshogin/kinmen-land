import os
import math
import json
import httpx
from datetime import datetime
from fastapi import FastAPI, Query, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from .data_service import data_service
from .gis_service import gis_service
from .tax_service import tax_calculator
from .cad_service import cad_export_engine
from .subdivision_service import CadastralSubdivisionEngine
from .land_value_service import LandValueTrendEngine
from .coords import latlon_to_twd97_119, twd97_119_to_latlon
from .pipeline.scheduler import pipeline_scheduler
from .database import SessionLocal
from .models import CrawlerLog, RealEstateTransaction, User, AuditLog
from .auth import (
    init_default_users, hash_password, verify_password,
    create_access_token, verify_token, ROLE_PERMISSIONS, log_audit_trail
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VERSION_FILE = os.path.join(BASE_DIR, "version.json")
APP_VERSION = "v0.10_20261118"
APP_BUILD_DATE = "2026-11-18"
if os.path.exists(VERSION_FILE):
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            v_data = json.load(f)
            APP_VERSION = v_data.get("version", APP_VERSION)
            APP_BUILD_DATE = v_data.get("build_date", APP_BUILD_DATE)
    except Exception:
        pass

app = FastAPI(
    title="金門地政雲 API (Kinmen Land Cloud Service)",
    description="整合都市計畫、金門國家公園管制分區、地籍、實價登錄與多層級角色權限 (RBAC) 之現代空間地理資訊後端",
    version=APP_VERSION
)

# Enable CORS for cross-domain WebGIS access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_default_users()
    pipeline_scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    pipeline_scheduler.stop()

# ----------------- Auth & RBAC Dependency -----------------
def get_current_user_info(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """解析 Bearer Token 並驗證使用者身分與權限"""
    guest_profile = {
        "id": 0,
        "username": "guest",
        "role": "guest",
        "full_name": "一般民眾 (訪客)",
        "agency": "公眾便民查詢",
        "role_info": ROLE_PERMISSIONS["guest"]
    }
    
    if not authorization:
        return guest_profile
    
    token = authorization.replace("Bearer ", "").strip()
    payload = verify_token(token)
    if not payload:
        return guest_profile
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == payload.get("username")).first()
        if not user or user.status != "active":
            return guest_profile
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "full_name": user.full_name,
            "agency": user.agency or "",
            "role_info": ROLE_PERMISSIONS.get(user.role, ROLE_PERMISSIONS["guest"])
        }
    finally:
        db.close()

# ----------------- Request / Response Models -----------------
class IdentifyRequest(BaseModel):
    lat: float = Field(..., description="WGS84 緯度 (例如: 24.4550)")
    lon: float = Field(..., description="WGS84 經度 (例如: 118.3300)")

class CapacityRequest(BaseModel):
    land_area_ping: float = Field(..., description="土地坪數")
    zoning_name: str = Field(..., description="使用分區名稱 (例如: 自然村專用區)")

class FarmlandEvaluationRequest(BaseModel):
    area_sqm: float = Field(..., ge=1.0, description="土地面積 (平方公尺)")
    acquired_before_2000: bool = Field(False, description="是否為民國89年1月28日前取得 (老農資格)")
    zoning_name: str = Field("農業區", description="使用分區名稱")
    is_national_park: bool = Field(False, description="是否位於金門國家公園管制區")
    has_road_access: bool = Field(True, description="是否臨接現有道路/建築線")

class TaxCalculationRequest(BaseModel):
    land_area_sqm: float = Field(330.6, description="土地移轉面積 (平方公尺)")
    current_announced_val: float = Field(2500.0, description="當期公告土地現值 (元/m²)")
    prev_announced_val: float = Field(800.0, description="前次移轉現值 (元/m²)")
    cpi_ratio: float = Field(100.0, description="消費者物價指數累計漲幅 (%)")
    holding_years: int = Field(5, description="持有年限 (年)")
    is_self_use: bool = Field(False, description="是否適用自用住宅優惠稅率 (10%)")
    land_improvement_cost: float = Field(0.0, description="改良土地費用 (元)")
    has_building: bool = Field(False, description="是否包含建物一併移轉")
    building_area_ping: float = Field(0.0, description="建物總面積 (坪)")
    building_eval_val_per_ping: float = Field(12000.0, description="房屋評定現值單價 (元/坪)")
    scrivener_fee: float = Field(15000.0, description="地政士代書費預估 (元)")

class CadExportRequest(BaseModel):
    title: str = Field(..., description="宗地或專案標題")
    town: str = Field("金寧鄉", description="鄉鎮")
    section: str = Field("赤岑段", description="地段")
    number: str = Field("165", description="地號")
    lat: float = Field(..., description="緯度 (WGS84)")
    lon: float = Field(..., description="經度 (WGS84)")
    area_sqm: float = Field(330.6, description="土地面積 (平方公尺)")
    zoning: str = Field("自然村專用區", description="使用分區")
    building_coverage: float = Field(60.0, description="法定建蔽率")
    floor_area_ratio: float = Field(180.0, description="法定容積率")
    include_layers: Optional[List[str]] = Field(None, description="匯出圖層清單")
    include_nearby_cases: bool = Field(True, description="是否包含周邊實價點位")

class SubdivisionSimulateRequest(BaseModel):
    title: str = Field("金門地政雲宗地", description="宗地標題")
    town: str = Field("金寧鄉", description="鄉鎮")
    section: str = Field("赤岑段", description="地段")
    number: str = Field("165", description="地號")
    lat: float = Field(24.4550, description="中心緯度")
    lon: float = Field(118.3300, description="中心經度")
    area_sqm: float = Field(330.6, description="母地號面積 (平方公尺)")
    zoning: str = Field("自然村專用區", description="使用分區")
    building_coverage: float = Field(60.0, description="法定建蔽率")
    floor_area_ratio: float = Field(180.0, description="法定容積率")
    split_mode: str = Field("equal", description="分割模式: equal(等分), ratio(比例), custom_area(指定面積)")
    count: int = Field(2, description="等分筆數 (2~4)")
    ratios: Optional[List[float]] = Field(None, description="比例分配陣列")
    target_sqm: Optional[float] = Field(None, description="自訂指定切割面積")
    cut_axis: str = Field("width", description="切割方向: width(臨路面寬分割), depth(縱深前後分割)")

class MergerSimulateRequest(BaseModel):
    title: str = Field("金門地政雲宗地", description="主宗地標題")
    town: str = Field("金寧鄉", description="鄉鎮")
    section: str = Field("赤岑段", description="地段")
    number: str = Field("165", description="地號")
    lat: float = Field(24.4550, description="中心緯度")
    lon: float = Field(118.3300, description="中心經度")
    area_sqm: float = Field(330.6, description="母地號面積 (平方公尺)")
    zoning: str = Field("自然村專用區", description="使用分區")
    building_coverage: float = Field(60.0, description="法定建蔽率")
    floor_area_ratio: float = Field(180.0, description="法定容積率")
    neighbors: Optional[List[Dict[str, Any]]] = Field(None, description="勾選擬合併之鄰地清單")

class LoginRequest(BaseModel):
    username: str
    password: str

class QuickSwitchRequest(BaseModel):
    role: str

class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str
    agency: Optional[str] = None
    role: str = "professional"

class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None

class AuditLogRequest(BaseModel):
    action: str
    target: Optional[str] = None
    details: Optional[str] = None

# ----------------- Health & Status API -----------------
@app.get("/api/v1/health", summary="系統健康狀態")
async def health_check():
    db = SessionLocal()
    last_sync = None
    db_count = 0
    user_count = 0
    try:
        db_count = db.query(RealEstateTransaction).count()
        user_count = db.query(User).count()
        last_log = db.query(CrawlerLog).order_by(CrawlerLog.id.desc()).first()
        if last_log:
            last_sync = {
                "batch": last_log.batch_period,
                "status": last_log.status,
                "time": last_log.executed_at.strftime("%Y-%m-%d %H:%M:%S") if last_log.executed_at else ""
            }
    finally:
        db.close()

    return {
        "status": "healthy",
        "service": "Kinmen Land Cloud Backend",
        "version": APP_VERSION,
        "build_date": APP_BUILD_DATE,
        "total_real_estate": len(data_service.real_estate_items),
        "db_records_count": db_count,
        "users_count": user_count,
        "scheduler_active": pipeline_scheduler.is_running,
        "last_sync": last_sync
    }

# ----------------- Authentication & RBAC Endpoints -----------------
@app.post("/api/v1/auth/login", summary="使用者帳密登入")
async def auth_login(req: LoginRequest, request: Request):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == req.username).first()
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤，請確認後重試")
        if user.status != "active":
            raise HTTPException(status_code=403, detail="此帳號已被停用，請聯絡系統管理員")
        
        user.last_login = datetime.utcnow()
        db.commit()
        
        token = create_access_token(user.id, user.username, user.role)
        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_trail(user.username, "LOGIN", "系統登入", f"使用者 {user.full_name} 登入成功", client_ip)
        
        return {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "agency": user.agency or "",
                "role": user.role,
                "role_info": ROLE_PERMISSIONS.get(user.role, ROLE_PERMISSIONS["guest"])
            }
        }
    finally:
        db.close()

@app.get("/api/v1/auth/me", summary="取得目前登入使用者身分與權限")
async def auth_me(current_user: Dict[str, Any] = Depends(get_current_user_info)):
    return current_user

@app.post("/api/v1/auth/quick-switch", summary="快速切換展示身份 (Demo / 評審專用)")
async def auth_quick_switch(req: QuickSwitchRequest, request: Request):
    target_role = req.role.lower()
    if target_role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail="無效的角色層級")
    
    role_user_map = {
        "admin": "shogiin",
        "auditor": "auditor_kinmen",
        "professional": "pro_agent",
        "guest": "guest"
    }
    username = role_user_map.get(target_role, "guest")
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            init_default_users()
            user = db.query(User).filter(User.username == username).first()
        
        token = create_access_token(user.id, user.username, user.role)
        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_trail(user.username, "SWITCH_ROLE", f"快速切換至 {target_role}", "Demo 快速切換身份", client_ip)
        
        return {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "agency": user.agency or "",
                "role": user.role,
                "role_info": ROLE_PERMISSIONS.get(user.role, ROLE_PERMISSIONS["guest"])
            }
        }
    finally:
        db.close()

@app.post("/api/v1/auth/audit", summary="前端操作資安稽核回報")
async def report_audit(req: AuditLogRequest, request: Request, current_user: Dict[str, Any] = Depends(get_current_user_info)):
    client_ip = request.client.host if request.client else "127.0.0.1"
    log_audit_trail(
        username=current_user["username"],
        action=req.action,
        target=req.target,
        details=req.details,
        ip=client_ip
    )
    return {"status": "ok"}

# ----------------- System Admin & User Management API -----------------
@app.get("/api/v1/admin/users", summary="使用者帳號清單 (Level 4 管理員)")
async def list_users(current_user: Dict[str, Any] = Depends(get_current_user_info)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="權限不足：僅系統管理員 (Super Admin) 可檢視與管理使用者帳號")
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id.asc()).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "agency": u.agency or "",
                "role": u.role,
                "role_title": ROLE_PERMISSIONS.get(u.role, {}).get("title", u.role),
                "badge_color": ROLE_PERMISSIONS.get(u.role, {}).get("badge_color", "slate"),
                "status": u.status,
                "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "",
                "last_login": u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "從未登入"
            }
            for u in users
        ]
    finally:
        db.close()

@app.post("/api/v1/admin/users", summary="新增使用者帳號 (Level 4 管理員)")
async def create_user(req: UserCreateRequest, current_user: Dict[str, Any] = Depends(get_current_user_info)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="權限不足：僅系統管理員可建立帳號")
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == req.username).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"帳號名稱 '{req.username}' 已存在")
        new_user = User(
            username=req.username,
            password_hash=hash_password(req.password),
            full_name=req.full_name,
            agency=req.agency or "",
            role=req.role,
            status="active"
        )
        db.add(new_user)
        db.commit()
        log_audit_trail(current_user["username"], "CREATE_USER", req.username, f"建立新帳號 {req.full_name} ({req.role})")
        return {"status": "success", "message": f"帳號 {req.username} 建立成功"}
    finally:
        db.close()

@app.put("/api/v1/admin/users/{user_id}", summary="修改使用者權限或啟用/停用 (Level 4 管理員)")
async def update_user(user_id: int, req: UserUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user_info)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="權限不足：僅系統管理員可變更帳號設定")
    db = SessionLocal()
    try:
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="找不到指定使用者")
        
        # Protect default admin
        if target_user.username == "shogiin" and req.status == "disabled":
            raise HTTPException(status_code=400, detail="不可停用預設系統管理員 shogiin")
        
        if req.role:
            target_user.role = req.role
        if req.status:
            target_user.status = req.status
        
        db.commit()
        log_audit_trail(current_user["username"], "UPDATE_USER", target_user.username, f"更新角色={req.role}, 狀態={req.status}")
        return {"status": "success", "message": "帳號設定更新成功"}
    finally:
        db.close()

@app.get("/api/v1/admin/audit-logs", summary="查詢系統資安稽核日誌 (Level 3 稽核員 / Level 4 管理員)")
async def get_audit_logs(limit: int = Query(50, ge=1, le=200), current_user: Dict[str, Any] = Depends(get_current_user_info)):
    if current_user.get("role") not in ["admin", "auditor"]:
        raise HTTPException(status_code=403, detail="權限不足：僅系統管理員與公務稽核員可調閱系統日誌")
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
        return [
            {
                "id": l.id,
                "username": l.username,
                "action": l.action,
                "target": l.target or "-",
                "details": l.details or "-",
                "ip": l.ip_address,
                "created_at": l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else ""
            }
            for l in logs
        ]
    finally:
        db.close()

# ----------------- Cadastre & Real Estate Endpoints -----------------
@app.get("/api/v1/sections", summary="取得金門全縣 250 地段清單")
async def get_sections(town: Optional[str] = Query(None, description="鄉鎮市區")):
    return data_service.get_sections(town)

@app.get("/api/v1/real-estate/filter", summary="實價登錄多維度查詢與統計")
async def filter_real_estate(
    town: Optional[str] = Query(None, description="行政區"),
    b_type: Optional[str] = Query(None, description="建物型態"),
    min_price: Optional[float] = Query(None, description="最低總價(萬元)"),
    max_price: Optional[float] = Query(None, description="最高總價(萬元)"),
    min_unit: Optional[float] = Query(None, description="最低單價(萬/坪)"),
    max_unit: Optional[float] = Query(None, description="最高單價(萬/坪)"),
    keyword: Optional[str] = Query(None, description="地址/地段關鍵字"),
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0)
):
    return data_service.filter_real_estate(
        town=town,
        b_type=b_type,
        min_price=min_price,
        max_price=max_price,
        min_unit=min_unit,
        max_unit=max_unit,
        keyword=keyword,
        limit=limit,
        offset=offset
    )

@app.get("/api/v1/real-estate/nearby", summary="空間環域搜尋鄰近成交案件")
async def get_nearby_real_estate(
    lat: float = Query(..., description="中心緯度"),
    lon: float = Query(..., description="中心經度"),
    radius_km: float = Query(1.5, ge=0.1, le=10.0, description="搜尋半徑公里"),
    limit: int = Query(8, ge=1, le=50)
):
    return data_service.get_nearby_transactions(lat, lon, radius_km, limit)

@app.get("/api/v1/real-estate/buffer-analysis", summary="空間環域半徑實價深度分析 (300m / 500m / 1000m) - 對標臺北地政雲 fun=g11")
async def analyze_buffer_real_estate(
    lat: float = Query(..., description="中心點緯度 (WGS84)"),
    lon: float = Query(..., description="中心點經度 (WGS84)"),
    radius_m: int = Query(500, ge=100, le=3000, description="搜尋半徑公尺 (如: 300, 500, 1000)"),
    b_type: Optional[str] = Query(None, description="建物型態篩選 (如: 全部, 透天厝, 公寓)"),
    current_user: Dict[str, Any] = Depends(get_current_user_info)
):
    return data_service.get_buffer_analysis(lat, lon, radius_m, b_type)

@app.get("/api/v1/real-estate/stats", summary="金門房市行情排行榜與統計")
async def get_real_estate_stats():
    return data_service.get_market_statistics()

@app.get("/api/v1/real-estate/trends", summary="取得金門歷季價量走勢與型態佔比 (ECharts)")
async def get_real_estate_trends():
    return data_service.get_trend_analytics()

@app.get("/api/v1/real-estate/heatmap-data", summary="取得全島房價熱力圖向量點位 (Leaflet.heat 專用)")
async def get_heatmap_data(
    mode: str = Query("price", description="加權模式: price (單價加權), count (交易密度), total (總價量體)"),
    b_type: Optional[str] = Query(None, description="型態篩選: 全部, 住宅, 土地")
):
    raw_items = data_service.real_estate_items
    valid_items = []

    for item in raw_items:
        item_type = item.get("b_type", "")
        if b_type == "住宅":
            if not any(h in item_type for h in ["華廈", "住宅大樓", "公寓", "透天厝", "農舍", "套房"]):
                continue
        elif b_type == "土地":
            if "土地" not in item_type:
                continue

        lat = item.get("lat")
        lon = item.get("lon")
        unit_p = item.get("unit_ping_wan", 0.0) or 0.0
        tot_p = item.get("total_price_wan", 0.0) or 0.0

        if lat and lon:
            valid_items.append({
                "lat": lat,
                "lon": lon,
                "unit_price": unit_p,
                "total_price": tot_p,
                "b_type": item_type,
                "addr": item.get("addr", "")
            })

    if not valid_items:
        return {"mode": mode, "b_type": b_type or "全部", "count": 0, "max_unit_price": 0, "min_unit_price": 0, "points": []}

    units = [p["unit_price"] for p in valid_items if p["unit_price"] > 0]
    max_u = max(units) if units else 35.0
    min_u = min(units) if units else 0.5

    heat_points = []
    for p in valid_items:
        if mode == "price":
            if p["unit_price"] > 0 and max_u > min_u:
                # Intensity between 0.2 and 1.0 based on unit price
                intensity = 0.2 + 0.8 * ((p["unit_price"] - min_u) / (max_u - min_u))
            else:
                intensity = 0.15
        elif mode == "total":
            intensity = min(1.0, max(0.2, p["total_price"] / 2500.0))
        else: # density
            intensity = 0.85

        heat_points.append([round(p["lat"], 5), round(p["lon"], 5), round(intensity, 3)])

    return {
        "mode": mode,
        "b_type": b_type or "全部",
        "count": len(heat_points),
        "max_unit_price": round(max_u, 1),
        "min_unit_price": round(min_u, 1),
        "points": heat_points
    }

@app.post("/api/v1/gis/identify", summary="地塊空間相交檢索 (核心 fun=g11)")
async def identify_location(req: IdentifyRequest, request: Request, current_user: Dict[str, Any] = Depends(get_current_user_info)):
    spatial_info = await gis_service.identify_location(req.lat, req.lon)
    nearby_cases = data_service.get_nearby_transactions(req.lat, req.lon, radius_km=1.5, limit=6)
    
    # 紀錄調閱日誌
    if current_user.get("username") != "guest":
        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_trail(
            current_user["username"],
            "PARCEL_IDENTIFY",
            f"坐標: {req.lat:.4f}, {req.lon:.4f}",
            f"分區: {spatial_info.get('urban_plan', {}).get('main_zone', '一般')}",
            client_ip
        )

    return {
        "spatial": spatial_info,
        "nearby_transactions": nearby_cases
    }

@app.post("/api/v1/gis/calculate-capacity", summary="自然村與建管容積試算")
async def calculate_capacity(req: CapacityRequest):
    return gis_service.calculate_building_capacity(req.land_area_ping, req.zoning_name)

@app.post("/api/v1/gis/evaluate-farmland", summary="農地分割與農舍興建資格合規檢測 (M3.2)")
async def evaluate_farmland(req: FarmlandEvaluationRequest):
    return gis_service.evaluate_farmland_compliance(
        area_sqm=req.area_sqm,
        acquired_before_2000=req.acquired_before_2000,
        zoning_name=req.zoning_name,
        is_national_park=req.is_national_park,
        has_road_access=req.has_road_access
    )

# ----------------- Land Tax & Registration Fee Endpoints -----------------
@app.post("/api/v1/tax/calculate", summary="地政登記稅費與土地增值稅深度自動試算機 (對標台北地政雲稅費試算)")
async def calculate_land_transaction_taxes(req: TaxCalculationRequest):
    return tax_calculator.calculate_full_transaction(req.dict())

@app.get("/api/v1/tax/quick-estimate", summary="依宗地坐標與面積快速預估公告土地現值與稅費")
async def quick_estimate_land_tax(
    lat: float = Query(..., description="宗地中心緯度"),
    lon: float = Query(..., description="宗地中心經度"),
    area_sqm: float = Query(330.6, description="土地面積 (平方公尺)"),
    is_self_use: bool = Query(False, description="是否自用住宅 (10% 優惠)"),
    holding_years: int = Query(5, description="持有年限"),
    has_building: bool = Query(False, description="是否含建物移轉"),
    building_ping: float = Query(0.0, description="建物面積 (坪)")
):
    # 依經緯度判斷所在區位之基準公告土地現值
    announced_val = 2500.0
    if lon < 118.28:
        announced_val = 2200.0  # 烈嶼鄉
    elif lat < 24.436 and 118.315 < lon < 118.325:
        announced_val = 18500.0  # 金城精華城區 (民生/中興)
    elif lat < 24.445 and 118.310 < lon < 118.340:
        announced_val = 8000.0  # 金城外圍 / 金大周邊
    elif 118.305 < lon < 118.345 and 24.445 < lat < 24.465:
        announced_val = 3200.0  # 金寧鄉 / 大橋端
    elif 118.410 < lon < 118.425 and 24.435 < lat < 24.445:
        announced_val = 9500.0  # 金湖市港段
    elif lon > 118.39:
        announced_val = 2600.0  # 金沙鎮

    prev_val = max(500.0, round(announced_val * 0.45))

    payload = {
        "land_area_sqm": area_sqm,
        "current_announced_val": announced_val,
        "prev_announced_val": prev_val,
        "holding_years": holding_years,
        "is_self_use": is_self_use,
        "has_building": has_building,
        "building_area_ping": building_ping
    }
    res = tax_calculator.calculate_full_transaction(payload)
    res["estimated_announced_val"] = announced_val
    res["estimated_prev_val"] = prev_val
    return res

# ----------------- CAD / DXF / KML Vector Export Endpoints -----------------
@app.post("/api/v1/cad/preview-metadata", summary="取得宗地 CAD 向量資訊與 TWD97 範圍預覽")
async def preview_cad_metadata(req: CadExportRequest):
    x_c, y_c = latlon_to_twd97_119(req.lat, req.lon)
    pts = cad_export_engine.generate_parcel_geometry(req.lat, req.lon, req.area_sqm)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    perimeter = sum(
        math.hypot(pts[i+1][0] - pts[i][0], pts[i+1][1] - pts[i][1])
        for i in range(len(pts) - 1)
    )

    nearby = []
    if req.include_nearby_cases:
        nearby = data_service.get_nearby_transactions(req.lat, req.lon, radius_km=0.5, limit=8)

    return {
        "target_title": req.title,
        "twd97_center": {"x": x_c, "y": y_c},
        "extents": {
            "min_x": round(min(xs), 2),
            "min_y": round(min(ys), 2),
            "max_x": round(max(xs), 2),
            "max_y": round(max(ys), 2)
        },
        "geometry_stats": {
            "area_sqm": req.area_sqm,
            "area_ping": round(req.area_sqm * 0.3025, 2),
            "perimeter_m": round(perimeter, 2),
            "vertex_count": len(pts)
        },
        "available_layers": [
            {"id": "CADASTRAL_LOT", "name": "宗地地籍界址線", "color": "Green (3)", "active": True},
            {"id": "BUILDING_LINE", "name": "法定退縮線 / 建築線", "color": "Red (1)", "active": True},
            {"id": "BUILDING_ENVELOPE", "name": "法定建築基底外框", "color": "Magenta (6)", "active": True},
            {"id": "LOT_ANNOTATION", "name": "地號/面積/分區文字註記", "color": "Yellow (2)", "active": True},
            {"id": "SURROUNDING_CASES", "name": "周邊實價登錄成交點位", "color": "Cyan (4)", "active": True},
            {"id": "SURVEY_GRID", "name": "TWD97 國土測繪十字基準線", "color": "Gray (8)", "active": True}
        ],
        "nearby_cases_count": len(nearby)
    }

@app.post("/api/v1/cad/export-dxf", summary="匯出 AutoCAD DXF 向量圖檔 (TWD97 119 分帶公制)")
async def export_cad_dxf(req: CadExportRequest):
    target_info = req.dict()
    nearby = data_service.get_nearby_transactions(req.lat, req.lon, radius_km=0.5, limit=12) if req.include_nearby_cases else []
    dxf_str = cad_export_engine.generate_dxf(target_info, nearby, req.include_layers)
    clean_name = req.title.replace(" ", "_").replace("/", "_")
    filename = f"{clean_name}_TWD97.dxf"

    return Response(
        content=dxf_str.encode("utf-8"),
        media_type="application/dxf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{httpx.URL(filename)}"}
    )

@app.post("/api/v1/cad/export-kml", summary="匯出 Google Earth KML 3D 向量檔 (WGS84 經緯度)")
async def export_cad_kml(req: CadExportRequest):
    target_info = req.dict()
    nearby = data_service.get_nearby_transactions(req.lat, req.lon, radius_km=0.5, limit=12) if req.include_nearby_cases else []
    kml_str = cad_export_engine.generate_kml(target_info, nearby)
    clean_name = req.title.replace(" ", "_").replace("/", "_")
    filename = f"{clean_name}_GoogleEarth.kml"

    return Response(
        content=kml_str.encode("utf-8"),
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{httpx.URL(filename)}"}
    )

@app.post("/api/v1/cad/export-geojson", summary="匯出標準 RFC 7946 GeoJSON 格式檔 (QGIS/GIS)")
async def export_cad_geojson(req: CadExportRequest):
    target_info = req.dict()
    nearby = data_service.get_nearby_transactions(req.lat, req.lon, radius_km=0.5, limit=12) if req.include_nearby_cases else []
    geojson_dict = cad_export_engine.generate_geojson(target_info, nearby)
    clean_name = req.title.replace(" ", "_").replace("/", "_")
    filename = f"{clean_name}_QGIS.geojson"

    return Response(
        content=json.dumps(geojson_dict, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{httpx.URL(filename)}"}
    )

@app.post("/api/v1/cad/export-package", summary="一鍵匯出全套工程圖資包 (DXF + KML + GeoJSON + 規格說明 ZIP)")
async def export_cad_package(req: CadExportRequest):
    target_info = req.dict()
    nearby = data_service.get_nearby_transactions(req.lat, req.lon, radius_km=0.5, limit=12) if req.include_nearby_cases else []
    zip_bytes = cad_export_engine.generate_full_zip_package(target_info, nearby)
    clean_name = req.title.replace(" ", "_").replace("/", "_")
    filename = f"{clean_name}_CAD_GIS_Package.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{httpx.URL(filename)}"}
    )

# ==================== 宗地分割與合併模擬 (Cadastral Subdivision & Merger) ====================
@app.post("/api/v1/cadastral/subdivision-simulate", summary="宗地分割模擬運算 (含農發條例第16條與畸零地面寬深度法規檢核)")
async def simulate_subdivision(req: SubdivisionSimulateRequest):
    target_info = req.dict()
    result = CadastralSubdivisionEngine.simulate_subdivision(
        target_info=target_info,
        split_mode=req.split_mode,
        count=req.count,
        ratios=req.ratios,
        target_sqm=req.target_sqm,
        cut_axis=req.cut_axis
    )
    return result

@app.post("/api/v1/cadastral/merger-simulate", summary="宗地合併模擬運算 (含鄰地聯集、規模效益評估與土地登記規則檢核)")
async def simulate_merger(req: MergerSimulateRequest):
    primary_info = req.dict()
    result = CadastralSubdivisionEngine.simulate_merger(
        primary_info=primary_info,
        neighbors=req.neighbors or []
    )
    return result

@app.post("/api/v1/cadastral/export-subdivision-dxf", summary="匯出分割模擬 AutoCAD DXF 向量圖檔 (含新地籍線、分割切線與界址標註)")
async def export_subdivision_dxf(req: SubdivisionSimulateRequest):
    target_info = req.dict()
    result = CadastralSubdivisionEngine.simulate_subdivision(
        target_info=target_info,
        split_mode=req.split_mode,
        count=req.count,
        ratios=req.ratios,
        target_sqm=req.target_sqm,
        cut_axis=req.cut_axis
    )
    dxf_str = CadastralSubdivisionEngine.generate_subdivision_dxf(result)
    clean_name = f"{req.town}_{req.section}_{req.number}_Subdivision"
    filename = f"{clean_name}_TWD97.dxf"

    return Response(
        content=dxf_str.encode("utf-8"),
        media_type="application/dxf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{httpx.URL(filename)}"}
    )

# ==================== 歷年公告土地現值與地價走勢分析 (10-Year Land Value Trends) ====================
@app.get("/api/v1/land-value/historical-trends", summary="查詢宗地近10年公告現值與公告地價時間序列與金門各鄉鎮對比")
async def get_land_value_trends(
    town: str = Query("金寧鄉", description="鄉鎮"),
    section: str = Query("赤岑段", description="地段"),
    number: str = Query("165", description="地號"),
    base_price_sqm: Optional[float] = Query(None, description="基準單價 (元/m²)")
):
    trends = LandValueTrendEngine.get_parcel_10y_trends(
        town=town,
        section=section,
        number=number,
        current_sqm_val=base_price_sqm
    )
    return trends

@app.post("/api/v1/pipeline/trigger-sync", summary="手動觸發內政部每旬實價同步管線 (需 Level 4 系統管理員權限)")
async def trigger_pipeline_sync(current_user: Dict[str, Any] = Depends(get_current_user_info)):
    # 嚴格 RBAC 權限攔截
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail=f"【權限攔截】操作被拒絕：目前身分「{current_user.get('full_name')}」不具備管線手動執行權限。此功能僅限「Level 4 系統管理員 (Super Admin)」操作。"
        )
    
    res = pipeline_scheduler.trigger_manual_sync()
    data_service.reload_data()
    log_audit_trail(current_user["username"], "PIPELINE_SYNC", "內政部實價同步管線", f"結果: {res}")
    return {
        "sync_result": res,
        "current_total_transactions": len(data_service.real_estate_items)
    }

@app.get("/api/v1/pipeline/sync-logs", summary="取得實價登錄自動排程同步紀錄 (M2.2)")
async def get_sync_logs(limit: int = Query(10, ge=1, le=50)):
    db = SessionLocal()
    try:
        logs = db.query(CrawlerLog).order_by(CrawlerLog.id.desc()).limit(limit).all()
        return [
            {
                "id": l.id,
                "job_name": l.job_name,
                "batch_period": l.batch_period,
                "records_fetched": l.records_fetched,
                "records_inserted": l.records_inserted,
                "records_updated": l.records_updated,
                "status": l.status,
                "duration_seconds": l.duration_seconds,
                "executed_at": l.executed_at.strftime("%Y-%m-%d %H:%M:%S") if l.executed_at else ""
            }
            for l in logs
        ]
    finally:
        db.close()

@app.get("/proxy", summary="OGC/ArcGIS 跨來源圖資代理")
async def proxy_request(url: str):
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            content_type = resp.headers.get("Content-Type", "application/octet-stream")
            return Response(content=resp.content, status_code=resp.status_code, media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- Frontend Static Serving -----------------
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="static")
