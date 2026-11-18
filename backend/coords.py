import math

# TM2 to WGS84 formula for Taiwan/Kinmen (TWD97 zone 119)
# Central meridian: 119.0 degrees, scale factor: 0.9999, false easting: 250000, false northing: 0
# GRS80 ellipsoid: a = 6378137.0, b = 6356752.314140356

def twd97_119_to_latlon(x: float, y: float):
    a = 6378137.0
    b = 6356752.314140356
    lon0 = 119.0 * math.pi / 180.0
    k0 = 0.9999
    dx = 250000.0

    e = math.sqrt(1 - (b / a) ** 2)
    e2 = e ** 2 / (1 - e ** 2)

    x -= dx
    M = y / k0

    mu = M / (a * (1 - e ** 2 / 4 - 3 * e ** 4 / 64 - 5 * e ** 6 / 256))
    e1 = (1 - math.sqrt(1 - e ** 2)) / (1 + math.sqrt(1 - e ** 2))

    J1 = (3 * e1 / 2 - 27 * e1 ** 3 / 32)
    J2 = (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32)
    J3 = (151 * e1 ** 3 / 96)
    J4 = (1097 * e1 ** 4 / 512)

    fp = mu + J1 * math.sin(2 * mu) + J2 * math.sin(4 * mu) + J3 * math.sin(6 * mu) + J4 * math.sin(8 * mu)

    C1 = e2 * math.cos(fp) ** 2
    T1 = math.tan(fp) ** 2
    R1 = a * (1 - e ** 2) / ((1 - (e * math.sin(fp)) ** 2) ** 1.5)
    N1 = a / math.sqrt(1 - (e * math.sin(fp)) ** 2)
    D = x / (N1 * k0)

    Q1 = N1 * math.tan(fp) / R1
    Q2 = (D ** 2 / 2)
    Q3 = (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * e2) * D ** 4 / 24
    Q4 = (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * e2 - 3 * C1 ** 2) * D ** 6 / 720
    lat = fp - Q1 * (Q2 - Q3 + Q4)

    Q5 = D
    Q6 = (1 + 2 * T1 + C1) * D ** 3 / 6
    Q7 = (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * e2 + 24 * T1 ** 2) * D ** 5 / 120
    lon = lon0 + (Q5 - Q6 + Q7) / math.cos(fp)

    return round(lat * 180.0 / math.pi, 6), round(lon * 180.0 / math.pi, 6)

def latlon_to_twd97_119(lat: float, lon: float):
    a = 6378137.0
    b = 6356752.314140356
    lon0 = 119.0 * math.pi / 180.0
    k0 = 0.9999
    dx = 250000.0

    phi = lat * math.pi / 180.0
    lam = lon * math.pi / 180.0

    e = math.sqrt(1 - (b / a) ** 2)
    e2 = e ** 2 / (1 - e ** 2)

    N = a / math.sqrt(1 - (e * math.sin(phi)) ** 2)
    T = math.tan(phi) ** 2
    C = e2 * math.cos(phi) ** 2
    A = (lam - lon0) * math.cos(phi)

    M = a * ((1 - e**2/4 - 3*e**4/64 - 5*e**6/256)*phi 
             - (3*e**2/8 + 3*e**4/32 + 45*e**6/1024)*math.sin(2*phi) 
             + (15*e**4/256 + 45*e**6/1024)*math.sin(4*phi) 
             - (35*e**6/3072)*math.sin(6*phi))

    x = dx + k0 * N * (A + (1 - T + C)*A**3/6 + (5 - 18*T + T**2 + 72*C - 58*e2)*A**5/120)
    y = k0 * (M + N * math.tan(phi) * (A**2/2 + (5 - T + 9*C + 4*C**2)*A**4/24 + (61 - 58*T + T**2 + 600*C - 330*e2)*A**6/720))

    return round(x, 2), round(y, 2)

def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)
