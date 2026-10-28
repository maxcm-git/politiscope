#!/usr/bin/env python3
"""Cartes du site, en SVG pré-projeté (aucune librairie côté navigateur).

- site/geo/france.json : régions + départements de métropole, et les 5 DROM en encarts.
- site/geo/d/<dep>.json : contours simplifiés des communes d'un département.

Sources : france-geojson (régions/départements simplifiés, IGN/INSEE, Licence Ouverte) et
geo.api.gouv.fr (contours des communes, cache dans data/_cache/contours). Stdlib seulement."""
import json, math
from pathlib import Path

ROOT = Path(__file__).parent
GEO = ROOT / "data" / "raw" / "geo"
CACHE = ROOT / "data" / "_cache" / "contours"
OUT = ROOT / "site" / "geo"

W, H = 1000, 800           # carte de France
METRO_BOX = (190, 10, 990, 790)
DROM = ["971", "972", "973", "974", "976"]   # encarts, de haut en bas
DROM_BOX = (10, 10, 170, 790)
DEP_W = 800                 # cartes de département


def rings(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [r for p in polys for r in p]


def rdp(pts, eps):
    # Douglas-Peucker itératif (pas de récursion : certains contours font 10 000 points).
    if len(pts) < 4:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy)
        best, idx = 0, None
        for i in range(a + 1, b):
            # Anneau fermé : premier point = dernier, segment nul -> distance au point lui-même.
            d = (abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / n if n
                 else math.hypot(pts[i][0] - x1, pts[i][1] - y1))
            if d > best:
                best, idx = d, i
        if idx is not None and best > eps:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def fitter(features, box):
    # Projection équirectangulaire corrigée de cos(latitude) : suffisante à l'échelle d'un pays.
    lons = [x for f in features for r in rings(f["geometry"]) for x, _ in r]
    lats = [y for f in features for r in rings(f["geometry"]) for _, y in r]
    k = math.cos(math.radians((min(lats) + max(lats)) / 2))
    x0, x1, y0, y1 = min(lons) * k, max(lons) * k, min(lats), max(lats)
    bx0, by0, bx1, by1 = box
    s = min((bx1 - bx0) / (x1 - x0), (by1 - by0) / (y1 - y0))
    ox = bx0 + ((bx1 - bx0) - (x1 - x0) * s) / 2
    oy = by0 + ((by1 - by0) - (y1 - y0) * s) / 2
    return lambda lon, lat: (ox + (lon * k - x0) * s, oy + (y1 - lat) * s)


def path(geom, proj, eps):
    out, best = [], (0, None)
    for r in rings(geom):
        pts = rdp([proj(*p) for p in r], eps)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        if len(pts) < 3 or (max(xs) - min(xs)) + (max(ys) - min(ys)) < 1.2:
            continue  # îlot invisible à cette échelle
        out.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
        area = sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts))) / 2
        if abs(area) > best[0]:
            cx = sum((pts[i][0] + pts[i - 1][0]) * (pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1])
                     for i in range(len(pts))) / (6 * area)
            cy = sum((pts[i][1] + pts[i - 1][1]) * (pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1])
                     for i in range(len(pts))) / (6 * area)
            best = (abs(area), (round(cx, 1), round(cy, 1)))
    return "".join(out), best[1]


def bbox(d):
    nums = [float(v) for v in d.replace("M", " ").replace("L", " ").replace("Z", " ").replace(",", " ").split()]
    xs, ys = nums[0::2], nums[1::2]
    return [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)]


def load(name):
    return json.load(open(GEO / name, encoding="utf-8"))["features"]


def france():
    deps_info = {d["code"]: d for d in json.load(open(GEO / "departements.json", encoding="utf-8"))}
    reg_metro, dep_metro = load("regions-version-simplifiee.geojson"), load("departements-version-simplifiee.geojson")
    proj = fitter(dep_metro, METRO_BOX)
    regions, deps = [], []
    for f in reg_metro:
        d, _ = path(f["geometry"], proj, 0.4)
        regions.append([f["properties"]["code"], d, bbox(d)])
    for f in dep_metro:
        code = f["properties"]["code"]
        d, c = path(f["geometry"], proj, 0.4)
        deps.append([code, deps_info[code]["codeRegion"], d, c, bbox(d)])
    # DROM : chacun dans son encart, à sa propre échelle (région = département).
    outre = {f["properties"]["code"]: f for f in load("departements-avec-outre-mer.geojson")}
    x0, y0, x1, y1 = DROM_BOX
    step = (y1 - y0) / len(DROM)
    insets = []
    for i, code in enumerate(DROM):
        box = (x0 + 8, y0 + i * step + 22, x1 - 8, y0 + (i + 1) * step - 8)
        p = fitter([outre[code]], box)
        d, c = path(outre[code]["geometry"], p, 0.4)
        reg = deps_info[code]["codeRegion"]
        regions.append([reg, d, bbox(d)])
        deps.append([code, reg, d, c, bbox(d)])
        insets.append([code, round(x0, 1), round(y0 + i * step, 1), round(x1 - x0, 1), round(step - 4, 1)])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "france.json").write_text(json.dumps(
        {"w": W, "h": H, "regions": regions, "deps": deps, "insets": insets}, separators=(",", ":")), encoding="utf-8")
    print(f"france.json : {len(regions)} régions, {len(deps)} départements")


def communes():
    (OUT / "d").mkdir(parents=True, exist_ok=True)
    total = 0
    for f in sorted(CACHE.glob("*.json")):
        feats = json.load(open(f, encoding="utf-8"))["features"]
        proj = fitter(feats, (0, 0, DEP_W, DEP_W))
        rows, ys = [], []
        for x in feats:
            d, c = path(x["geometry"], proj, 0.6)
            if d:
                rows.append([x["properties"]["code"], d, c])
                ys += bbox(d)[1::2]
        h = math.ceil(max(ys)) + 2
        data = json.dumps({"w": DEP_W, "h": h, "c": rows}, separators=(",", ":"))
        (OUT / "d" / f.name).write_text(data, encoding="utf-8")
        total += len(data)
    print(f"{len(list(CACHE.glob('*.json')))} cartes de département, {total / 1e6:.1f} Mo au total")


if __name__ == "__main__":
    france()
    communes()
