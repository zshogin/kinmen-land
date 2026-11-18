import math

# TM2 to WGS84 formula for Taiwan/Kinmen (TWD97 zone 119)
# Central meridian: 119.0 degrees, scale factor: 0.9999, false easting: 250000, false northing: 0
# GRS80 ellipsoid: a = 6378137.0, b = 6356752.314140356, f = 1/298.257222101

def twd97_119_to_latlon(x, y):
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

    return lat * 180.0 / math.pi, lon * 180.0 / math.pi

# Test with a known Kinmen coordinate from door_Pub
# Let's test by querying 1 door
import urllib.request, ssl, json
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
url = "https://mapcloud.kinmen.gov.tw/arcgiswa/rest/services/Public/door_Pub/MapServer/0/query?where=1%3D1&outFields=Address,X,Y&resultRecordCount=3&f=pjson"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    for f in res['features']:
        x, y = f['attributes']['X'], f['attributes']['Y']
        addr = f['attributes']['Address']
        lat, lon = twd97_119_to_latlon(x, y)
        print(f"{addr}: X={x}, Y={y} -> Lat={lat:.5f}, Lon={lon:.5f}")
