import re

with open("DownloadHistory_ajax_list.html", "r", encoding="utf-8") as f:
    hist_html = f.read()

for match in re.findall(r'href=[\'"]([^\'"]+)[\'"]', hist_html):
    print("Link:", match)

for script in re.findall(r'<script[^>]*>(.*?)</script>', hist_html, re.S):
    for line in script.splitlines():
        if any(k in line for k in ['function', 'Download', 'season', 'val']):
            print("Hist JS:", line.strip()[:100])

selects = re.findall(r'<select[^>]*name=[\'"]?([^\'">\s]+)[\'"]?[^>]*>(.*?)</select>', hist_html, re.S)
for name, opts in selects:
    print(f"Hist SELECT name={name}")
    for val, text in re.findall(r'<option[^>]*value=[\'"]?([^\'">\s]*)[\'"]?[^>]*>(.*?)</option>', opts):
        print(f"   option val={val} text={text.strip()}")
