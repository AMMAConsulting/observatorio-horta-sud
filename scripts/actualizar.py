"""Descarga la oferta turística de L'Horta Sud desde Dades Obertes GVA y escribe datos.json."""
import json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

BASE = "https://dadesobertes.gva.es/api/3/action/"
COMARCA = re.compile(r"horta\s*sud", re.I)
RESPALDO = [{"id": "2c1e8aa4-5238-47c4-9404-f574ee1269a4", "etiqueta": "Viviendas de uso turístico"}]

def ckan(accion, **params):
    url = BASE + accion + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "observatorio-horta-sud"})
    with urllib.request.urlopen(req, timeout=90) as r:
        j = json.load(r)
    if not j.get("success"):
        raise RuntimeError(str(j.get("error")))
    return j["result"]

def descubrir():
    out = []
    for q in ("name:dades-turisme*", "turisme comunitat valenciana"):
        try:
            for p in ckan("package_search", q=q, rows=100)["results"]:
                for r in p.get("resources", []):
                    if r.get("datastore_active") and re.search(r"(ú|u)ltim|darrer", r.get("name") or "", re.I):
                        et = re.sub(r"^Lista de\s+", "", r.get("name") or p["title"], flags=re.I)
                        et = re.sub(r"\s*[ÚU]ltimo? Per[íi]odo\s*", "", et, flags=re.I).strip()
                        out.append({"id": r["id"], "etiqueta": et})
            if out:
                return out
        except Exception as e:
            print("descubrir:", e, file=sys.stderr)
    return RESPALDO

def campo(o, nombre):
    for k, v in o.items():
        if k.lower() == nombre:
            return v

def fecha(v):
    v = (str(v) if v is not None else "").strip()
    if not v:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        return m.group(0)
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", v)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else "0001-01-01"

def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0

filas = []
for f in descubrir():
    try:
        offset = 0
        while True:
            r = ckan("datastore_search", resource_id=f["id"], q="sud", limit=5000, offset=offset)
            for o in r["records"]:
                if COMARCA.search(str(campo(o, "comarca") or "")):
                    filas.append({
                        "tipo": f["etiqueta"],
                        "muni": str(campo(o, "municipio") or "Sin municipio").strip(),
                        "plazas": int(num(campo(o, "plazas"))),
                        "alta": fecha(campo(o, "fecha alta")),
                        "baja": fecha(campo(o, "fecha baja")),
                    })
            if len(r["records"]) < 5000:
                break
            offset += 5000
        print("OK", f["etiqueta"])
    except Exception as e:
        print("Fuente omitida", f["etiqueta"], e, file=sys.stderr)

if not filas:
    sys.exit("No se obtuvo ningún registro de la comarca: no se sobrescribe datos.json")

with open("datos.json", "w", encoding="utf-8") as fh:
    json.dump({"actualizado": datetime.now(timezone.utc).isoformat(), "filas": filas}, fh, ensure_ascii=False)
print(len(filas), "registros")
