#!/usr/bin/env python3
"""Photos des élus locaux : images sous licence libre de Wikimedia Commons, via Wikidata.

Une personne de Wikidata (nationalité française, avec image, date de naissance, et profession « personnalité politique »
ou une fonction occupée) est rattachée à un élu du RNE si la date de naissance est la même et si son libellé contient
le nom et le début du prénom. Auteur et licence viennent de l'API Commons (attribution exigée par CC BY / BY-SA).

Sorties : data/raw/photos_locales/<id>.jpg (320 px) et data/raw/photos_locales.json
  { "nom|prénom|naissance" (normalisés) : {"photo": fichier, "credit": "Wikimedia Commons · auteur · licence", "source": page} }
Les sites des mairies ne sont pas utilisés : formats hétérogènes et photos sans licence de réutilisation connue."""
import csv, io, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
import build_local

RAW = Path(__file__).parent / "data" / "raw"
OUT = RAW / "photos_locales"
UA = {"User-Agent": "Politiscope-prototype/0.1 (contact@politiscope.example)"}
REQ = """SELECT DISTINCT ?p ?label ?naiss ?img WHERE {
  ?p wdt:P27 wd:Q142; wdt:P31 wd:Q5; wdt:P18 ?img; wdt:P569 ?naiss . %s
  FILTER(YEAR(?naiss) > 1935) ?p rdfs:label ?label FILTER(LANG(?label) = "fr") }"""
norm = build_local.norm


def http(url, accept="*/*"):
    return urllib.request.urlopen(urllib.request.Request(url, headers={**UA, "Accept": accept}), timeout=180).read()


def wikidata():
    lignes = {}
    for filtre in ("?p wdt:P106 wd:Q82955 .", "?p wdt:P39 ?poste ."):  # personnalité politique, ou fonction occupée
        q = urllib.parse.urlencode({"query": REQ % filtre})
        for r in csv.DictReader(io.StringIO(http(f"https://query.wikidata.org/sparql?{q}", "text/csv").decode())):
            if r.get("naiss") and r.get("img"):  # réponse tronquée : dernière ligne incomplète
                lignes[r["p"]] = r
    return list(lignes.values())


def commons(fichiers):
    """Fichier Commons -> (vignette 320 px, auteur, licence, page), par lots de 50."""
    out, fichiers = {}, list(fichiers)
    for i in range(0, len(fichiers), 50):
        q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiurlwidth": 320,
                                    "iiprop": "url|extmetadata", "titles": "|".join("File:" + f for f in fichiers[i:i + 50])})
        rep = json.loads(http(f"https://commons.wikimedia.org/w/api.php?{q}"))
        norme = {n["to"]: n["from"][5:] for n in rep["query"].get("normalized", [])}
        for page in rep["query"]["pages"].values():
            ii = (page.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata", {})
            auteur = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip() or "auteur non précisé"
            out[norme.get(page["title"], page["title"][5:])] = (ii.get("thumburl"), auteur[:80],
                                                                  meta.get("LicenseShortName", {}).get("value", ""), ii.get("descriptionurl"))
    return out


def main():
    prec = RAW / "photos_locales.json"
    # Les photos changent peu : Wikidata une fois par jour suffit, et sa panne ne bloque pas la mise à jour.
    if prec.exists() and time.time() - prec.stat().st_mtime < 86400 and "--force" not in sys.argv:
        print("photos d'élus locaux : celles du jour, gardées")
        return
    try:
        personnes = wikidata()
    except Exception as e:
        if not prec.exists():
            raise
        print(f"⚠ Wikidata injoignable ({e.__class__.__name__}) : photos précédentes gardées")
        return
    deps, _, _ = build_local.geographie()
    P = build_local.lire_mandats(deps)
    par_date = {}
    for r in personnes:
        par_date.setdefault(r["naiss"][:10], []).append(r)
    trouves = {}
    for (nom, prenom, naiss), p in P.by_key.items():
        for r in par_date.get(naiss, []):
            l = norm(r["label"])
            if nom in l and prenom[:3] in l:
                trouves[f"{nom}|{prenom}|{naiss}"] = urllib.parse.unquote(r["img"].rsplit("/", 1)[1])
    infos = commons(set(trouves.values()))
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for k, f in trouves.items():
        thumb, auteur, licence, page = infos.get(f, (None,) * 4)
        if not thumb or not licence:  # sans licence identifiée : pas de photo
            continue
        dest = OUT / (re.sub(r"[^a-z0-9]+", "-", k) + ".jpg")
        if not dest.exists():
            brut = dest.with_suffix(".src")
            brut.write_bytes(http(thumb))
            build_local.reduire(brut, dest)
            brut.unlink()
        res[k] = {"photo": dest.name, "credit": f"Wikimedia Commons · {auteur} · {licence}", "source": page}
    # Nationaux illustrés par Commons (enrich_parlement) : auteur et licence pour le crédit.
    nat = json.loads((RAW / "parlement.json").read_text(encoding="utf-8")) if (RAW / "parlement.json").exists() else {}
    fic = {k: re.match(r"Wikimedia Commons \((.*)\)$", v.get("photo_credit") or "") for k, v in nat.items()}
    inf = commons({m[1] for m in fic.values() if m})
    credits = {k: {"credit": f"Wikimedia Commons · {inf[m[1]][1]} · {inf[m[1]][2]}", "source": inf[m[1]][3]}
               for k, m in fic.items() if m and inf.get(m[1], (None,))[0] and inf[m[1]][2]}
    (RAW / "credits_commons.json").write_text(json.dumps(credits, ensure_ascii=False, indent=0), encoding="utf-8")
    (RAW / "photos_locales.json").write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"photos d'élus locaux : {len(res)} (Wikidata : {len(trouves)} rapprochés)")


if __name__ == "__main__":
    main()
