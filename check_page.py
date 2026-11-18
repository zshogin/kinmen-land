import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://plvr.land.moi.gov.tw/DownloadOpenData', headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    seasons = re.findall(r'<option[^>]*value=[\'"]?([0-9]{3}[sS][0-9])[\'"]?[^>]*>(.*?)</option>', html, re.I)
    print('Found seasons count:', len(seasons))
    print('Recent seasons:', seasons[:15])

    links = re.findall(r'href=[\'"]([^\'"]*(?:Download|download|zip|csv)[^\'"]*)[\'"]', html, re.I)
    print('Found links:', links)

    buttons = re.findall(r'(Download[a-zA-Z0-9_\?=&]+)', html)
    print('Buttons/Endpoints found:', set(buttons))
except Exception as e:
    print('Error:', e)
