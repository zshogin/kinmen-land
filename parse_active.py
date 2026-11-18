import re

with open("Download_ajax_active.html", "r", encoding="utf-8") as f:
    active_html = f.read()

print("--- Forms and Inputs in Download_ajax_active ---")
forms = re.findall(r'<form[^>]*>(.*?)</form>', active_html, re.S)
for form in forms:
    print("FORM:")
    inputs = re.findall(r'<input[^>]*>', form)
    for inp in inputs:
        print(" ", inp)
    selects = re.findall(r'<select[^>]*name=[\'"]?([^\'">\s]+)[\'"]?[^>]*>(.*?)</select>', form, re.S)
    for name, opts in selects:
        print(f" SELECT name={name}")
        for val, text in re.findall(r'<option[^>]*value=[\'"]?([^\'">\s]*)[\'"]?[^>]*>(.*?)</option>', opts):
            print(f"   option val={val} text={text.strip()}")

print("\n--- Download links in Download_ajax_active ---")
for match in re.findall(r'href=[\'"]([^\'"]+)[\'"]', active_html):
    if any(k in match for k in ['Download', 'action', 'zip', 'csv']):
        print(" ", match)

print("\n--- JavaScript functions in Download_ajax_active ---")
for script in re.findall(r'<script[^>]*>(.*?)</script>', active_html, re.S):
    for line in script.splitlines():
        if any(k in line for k in ['function', 'submit', 'url', 'action', 'download', 'Download']):
            print(" JS:", line.strip()[:100])
