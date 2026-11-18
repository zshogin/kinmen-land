-- ====================================================================
-- 金門地政雲 (Kinmen Land Cloud) - PostgreSQL + PostGIS 空間資料庫架構
-- 坐標系: WGS84 (EPSG:4326) / 金門專用 TWD97 TM2 119分帶 (EPSG:3825/custom)
-- ====================================================================

-- 1. 啟用 PostGIS 空間拓樸擴充套件
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 2. 金門全縣地段目錄表 (Cadastre Sections)
CREATE TABLE IF NOT EXISTS cadastre_sections (
    id SERIAL PRIMARY KEY,
    town VARCHAR(50) NOT NULL,
    section_name VARCHAR(100) NOT NULL,
    section_code VARCHAR(20) NOT NULL,
    center_lat DOUBLE PRECISION,
    center_lon DOUBLE PRECISION,
    geom geometry(Point, 4326),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sections_town_code ON cadastre_sections(town, section_code);
CREATE INDEX IF NOT EXISTS idx_sections_geom ON cadastre_sections USING GIST (geom);

-- 3. 內政部實價登錄成交明細表 (Real Estate Transactions)
CREATE TABLE IF NOT EXISTS real_estate_transactions (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(100) UNIQUE NOT NULL,
    town VARCHAR(50) NOT NULL,
    section VARCHAR(100),
    target VARCHAR(100),
    addr VARCHAR(255) NOT NULL,
    land_number VARCHAR(50),
    date VARCHAR(20) NOT NULL,
    quarter VARCHAR(20) NOT NULL,
    total_price_wan DOUBLE PRECISION NOT NULL,
    unit_ping_wan DOUBLE PRECISION NOT NULL,
    area_ping DOUBLE PRECISION NOT NULL,
    area_sqm DOUBLE PRECISION NOT NULL,
    b_type VARCHAR(100) NOT NULL,
    floor VARCHAR(50),
    total_floors VARCHAR(50),
    age DOUBLE PRECISION,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    twd97_x DOUBLE PRECISION,
    twd97_y DOUBLE PRECISION,
    geom geometry(Point, 4326),
    source VARCHAR(50) DEFAULT 'MOI_DECENNIAL',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 空間索引與多維度複合索引
CREATE INDEX IF NOT EXISTS idx_re_geom ON real_estate_transactions USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_re_town_quarter ON real_estate_transactions(town, quarter);
CREATE INDEX IF NOT EXISTS idx_re_btype_unit ON real_estate_transactions(b_type, unit_ping_wan);
CREATE INDEX IF NOT EXISTS idx_re_addr_trgm ON real_estate_transactions USING gin (addr gin_trgm_ops);

-- 自動同步更新 geom 觸發器函數
CREATE OR REPLACE FUNCTION update_re_geom_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom := ST_SetSRID(ST_MakePoint(NEW.lon, NEW.lat), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_re_update_geom ON real_estate_transactions;
CREATE TRIGGER trg_re_update_geom
BEFORE INSERT OR UPDATE OF lat, lon ON real_estate_transactions
FOR EACH ROW EXECUTE FUNCTION update_re_geom_column();

-- 4. 空間環域檢索存儲過程 / 視圖 (Spatial Buffer & Distance Lookup)
-- 查詢給定經緯度半徑範圍內的最近交易案件
CREATE OR REPLACE FUNCTION get_nearby_transactions_postgis(
    p_lat DOUBLE PRECISION,
    p_lon DOUBLE PRECISION,
    p_radius_meters DOUBLE PRECISION DEFAULT 1500.0,
    p_limit INT DEFAULT 10
)
RETURNS TABLE (
    id INT,
    case_id VARCHAR,
    town VARCHAR,
    addr VARCHAR,
    date VARCHAR,
    b_type VARCHAR,
    total_price_wan DOUBLE PRECISION,
    unit_ping_wan DOUBLE PRECISION,
    distance_meters DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id,
        r.case_id,
        r.town,
        r.addr,
        r.date,
        r.b_type,
        r.total_price_wan,
        r.unit_ping_wan,
        ST_Distance(
            r.geom::geography,
            ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography
        ) AS distance_meters
    FROM real_estate_transactions r
    WHERE ST_DWithin(
        r.geom::geography,
        ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography,
        p_radius_meters
    )
    ORDER BY distance_meters ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 5. 農地合規審核紀錄表
CREATE TABLE IF NOT EXISTS farmland_audit_records (
    id SERIAL PRIMARY KEY,
    town VARCHAR(50) NOT NULL,
    section VARCHAR(100),
    land_number VARCHAR(50),
    area_sqm DOUBLE PRECISION NOT NULL,
    area_ping DOUBLE PRECISION NOT NULL,
    qualification_type VARCHAR(50) NOT NULL,
    has_road_access BOOLEAN DEFAULT TRUE,
    is_national_park BOOLEAN DEFAULT FALSE,
    compliance_status VARCHAR(50) NOT NULL,
    max_base_area_sqm DOUBLE PRECISION NOT NULL,
    max_floor_area_sqm DOUBLE PRECISION NOT NULL,
    agri_preserve_sqm DOUBLE PRECISION NOT NULL,
    can_subdivide BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. 每旬爬蟲同步日誌表
CREATE TABLE IF NOT EXISTS crawler_logs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    batch_period VARCHAR(50) NOT NULL,
    records_fetched INT DEFAULT 0,
    records_inserted INT DEFAULT 0,
    records_updated INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'SUCCESS',
    error_message TEXT,
    duration_seconds DOUBLE PRECISION DEFAULT 0.0,
    executed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
