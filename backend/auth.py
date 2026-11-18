import os
import hmac
import hashlib
import base64
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from .models import User, AuditLog
from .database import Base, engine, SessionLocal

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "kinmen-land-cloud-secure-jwt-token-key-2026")
SALT = b"kinmen_land_salt_9988"

# Role Definition & Permissions Matrix
ROLE_PERMISSIONS: Dict[str, Dict[str, Any]] = {
    "admin": {
        "title": "系統管理員 (Level 4)",
        "badge_color": "purple",
        "badge_text": "系統管理員",
        "description": "具備全系統最高管理權限，包含帳號指派、管線排程與資安稽核",
        "permissions": [
            "can_sync_pipeline",
            "can_manage_users",
            "can_view_audit_logs",
            "can_export_report_pro",
            "can_custom_signature",
            "can_advanced_calc",
            "can_farmland_audit"
        ]
    },
    "auditor": {
        "title": "公務稽核員 (Level 3)",
        "badge_color": "amber",
        "badge_text": "公務稽核員",
        "description": "公務機關審查身分，可查核所有宗地、日誌與管線紀錄",
        "permissions": [
            "can_view_audit_logs",
            "can_export_report_pro",
            "can_custom_signature",
            "can_advanced_calc",
            "can_farmland_audit"
        ]
    },
    "professional": {
        "title": "認證專業人員 (Level 2)",
        "badge_color": "emerald",
        "badge_text": "執業地政士",
        "description": "專業從業人員，支援完整 A4 報告產權簽章、農舍合規檢測與建管試算",
        "permissions": [
            "can_export_report_pro",
            "can_custom_signature",
            "can_advanced_calc",
            "can_farmland_audit"
        ]
    },
    "guest": {
        "title": "一般訪客 (Level 1)",
        "badge_color": "slate",
        "badge_text": "一般訪客",
        "description": "公眾便民服務，支援地圖瀏覽、實價查詢與浮水印預覽",
        "permissions": [
            "can_view_basic_map",
            "can_view_trends"
        ]
    }
}

def hash_password(password: str) -> str:
    """使用 PBKDF2 HMAC-SHA256 安全雜湊密碼"""
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), SALT, 100000)
    return key.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證明文密碼是否吻合雜湊"""
    return hmac.compare_digest(hash_password(plain_password), hashed_password)

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def base64url_decode(s: str) -> bytes:
    padding = '=' * (4 - (len(s) % 4))
    return base64.urlsafe_b64decode(s + padding)

def create_access_token(user_id: int, username: str, role: str, expires_in_days: int = 7) -> str:
    """生成標準無第三方依賴的 HMAC-SHA256 簽名 JWT Token"""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + (expires_in_days * 86400)
    }
    
    header_b64 = base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = base64url_encode(json.dumps(payload).encode('utf-8'))
    msg = f"{header_b64}.{payload_b64}".encode('utf-8')
    
    sig = hmac.new(SECRET_KEY.encode('utf-8'), msg, hashlib.sha256).digest()
    sig_b64 = base64url_encode(sig)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """驗證 Token 並解析 payload"""
    try:
        parts = token.strip().split('.')
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, sig_b64 = parts
        msg = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), msg, hashlib.sha256).digest()
        actual_sig = base64url_decode(sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        
        payload = json.loads(base64url_decode(payload_b64).decode('utf-8'))
        if payload.get("exp", 0) < time.time():
            return None # Expired
        
        return payload
    except Exception:
        return None

def init_default_users():
    """初始化預設 4 個角色層級帳號 (含指定的 shogiin 系統管理員)"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        preset_users = [
            {
                "username": "shogiin",
                "password": "123456789",
                "full_name": "系統管理員 (shogiin)",
                "agency": "金門地政雲資訊中心",
                "role": "admin",
                "status": "active"
            },
            {
                "username": "auditor_kinmen",
                "password": "auditor123",
                "full_name": "李科長 (公務稽核)",
                "agency": "金門縣政府地政局",
                "role": "auditor",
                "status": "active"
            },
            {
                "username": "pro_agent",
                "password": "pro123",
                "full_name": "陳建志 (特約地政士)",
                "agency": "浯江地政士聯合事務所",
                "role": "professional",
                "status": "active"
            },
            {
                "username": "guest",
                "password": "guest",
                "full_name": "一般民眾 (訪客)",
                "agency": "公眾便民查詢",
                "role": "guest",
                "status": "active"
            }
        ]
        
        for u in preset_users:
            existing = db.query(User).filter(User.username == u["username"]).first()
            if not existing:
                new_user = User(
                    username=u["username"],
                    password_hash=hash_password(u["password"]),
                    full_name=u["full_name"],
                    agency=u["agency"],
                    role=u["role"],
                    status=u["status"]
                )
                db.add(new_user)
            else:
                # Update password and details for default admin if exists
                if u["username"] == "shogiin":
                    existing.password_hash = hash_password(u["password"])
                    existing.role = "admin"
                    existing.status = "active"
        db.commit()
    finally:
        db.close()

def log_audit_trail(username: str, action: str, target: Optional[str] = None, details: Optional[str] = None, ip: Optional[str] = None):
    """記錄資安與業務稽核日誌"""
    db = SessionLocal()
    try:
        record = AuditLog(
            username=username,
            action=action,
            target=target,
            details=details,
            ip_address=ip or "127.0.0.1",
            created_at=datetime.utcnow()
        )
        db.add(record)
        db.commit()
    except Exception as e:
        print(f"Error logging audit trail: {e}")
    finally:
        db.close()
