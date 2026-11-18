with open("kinmen_urban_page.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for line in lines:
    if any(k in line.lower() for k in ['map', 'arcgis', 'ol.', 'leaflet', 'api', 'layer', 'kinmen', 'esri', 'wms', 'wmts']):
        print(line.strip()[:130])
