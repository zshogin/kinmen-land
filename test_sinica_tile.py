import urllib.request
import ssl
import math

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Kinmen center: lat 24.445, lon 118.345, z=13
z = 13
lat = 24.445
lon = 118.345
n = 2.0 ** z
x = int((lon + 180.0) / 360.0 * n)
lat_rad = math.radians(lat)
y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

print(f"Testing Kinmen tile at z={z}, x={x}, y={y}")

for layer in ['Kinmen_aerialphoto_1958', 'Kinmen_1966']:
    url = f"https://gis.sinica.edu.tw/kinmen/file-exists.php?img={layer}-png-{z}-{x}-{y}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            data = resp.read()
            print(f"Layer {layer}: HTTP {resp.status}, size {len(data)} bytes, Content-Type: {resp.headers.get('Content-Type')}")
    except Exception as e:
        print(f"Error for {layer}: {e}")
