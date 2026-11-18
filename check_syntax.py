with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
s = scripts[1]
bt = s.count('`')
print(f"Actual backticks: {bt} (even: {bt % 2 == 0})")
