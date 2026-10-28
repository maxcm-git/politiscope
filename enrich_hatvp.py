#!/usr/bin/env python3
"""Contenu des déclarations d'intérêts publiées par la HATVP (open data), pour l'afficher sur les fiches.

Sortie : data/raw/hatvp_contenu.json  { "nom|AAAA-MM-JJ" : [déclaration, …] } du dépôt le plus récent au plus ancien,
  déclaration = {p: prénom, d: date de dépôt, t: DI|DIA, q: qualité, mod: modificative, pdf: fichier PDF officiel,
                 c: {pro, consultant, dirigeant, participations, benevole, mandats, observations}}
Seules les données du déclarant sont reprises. Exclus : déclarations de situation patrimoniale (DSP*, loi n° 2013-907),
activité du conjoint et des collaborateurs (tiers ; restent lisibles dans le PDF officiel), mentions
« [Données non publiées] ».
Sources : https://www.hatvp.fr/livraison/merge/declarations.xml (cache data/_cache/) et data/raw/hatvp_liste.csv
(nom du fichier PDF de chaque déclaration ; le site renvoie vers https://www.hatvp.fr/livraison/dossiers/<fichier>)."""
import csv, json, re, subprocess, unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent
RAW, CACHE = ROOT / "data" / "raw", ROOT / "data" / "_cache"
XML = "https://www.hatvp.fr/livraison/merge/declarations.xml"
NP = "[Données non publiées]"
SECTIONS = {  # section -> (bloc XML, champs dans l'ordre affiché)
    "pro": ("activProfCinqDerniereDto", ("description", "employeur", "dateDebut", "dateFin")),
    "consultant": ("activConsultantDto", ("description", "nomEmployeur", "dateDebut", "dateFin")),
    "dirigeant": ("participationDirigeantDto", ("activite", "nomSociete", "dateDebut", "dateFin")),
    "participations": ("participationFinanciereDto", ("nomSociete", "evaluation", "nombreParts", "capitalDetenu")),
    "benevole": ("fonctionBenevoleDto", ("descriptionActivite", "nomStructure")),
    "mandats": ("mandatElectifDto", ("descriptionMandat", "dateDebut", "dateFin")),
}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def txt(e, tag):
    v = (e.findtext(tag) or "").strip()
    return re.sub(r"\s+", " ", v.replace(NP, "")).strip()


def remuneration(it):
    r = it.find("remuneration")
    if r is None:
        return ""
    if not len(r):
        return txt(it, "remuneration")
    ans = [f"{txt(m, 'annee')} : {txt(m, 'montant')} €" for m in r.findall("montant/montant") if txt(m, "montant")]
    return " ; ".join(ans) + (f" ({txt(r, 'brutNet').lower()})" if ans and txt(r, "brutNet") else "")


def iso(d):  # « 24/01/2025 14:41:51 » -> « 2025-01-24 »
    m = re.match(r"(\d\d)/(\d\d)/(\d{4})", d or "")
    return f"{m[3]}-{m[2]}-{m[1]}" if m else ""


def main():
    dest = CACHE / "hatvp_declarations.xml"
    if not dest.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-sfL", "-o", dest, XML], check=True)
    fichiers = {}  # (nom, date de dépôt, type) -> PDF officiel
    for r in csv.DictReader(open(RAW / "hatvp_liste.csv", encoding="utf-8"), delimiter=";"):
        if r["type_document"] in ("di", "dia", "dim", "diam") and r["nom_fichier"]:
            fichiers[(norm(r["nom"]), r["date_depot"], r["type_document"])] = r["nom_fichier"]
    out = {}
    for x in ET.parse(dest).getroot():
        g = x.find("general")
        t = g.findtext("typeDeclaration/id")
        if t not in ("DI", "DIA"):  # jamais les DSP (patrimoine)
            continue
        dec = g.find("declarant")
        nom, d = txt(dec, "nom"), iso(x.findtext("dateDepot"))
        mod = g.findtext("declarationModificative") == "true"
        c = {}
        for k, (bloc, champs) in SECTIONS.items():
            l = [[txt(it, f) for f in champs] + [remuneration(it), txt(it, "commentaire")] for it in x.findall(f"{bloc}/items/items")]
            if l:
                c[k] = l
        obs = [txt(it, "contenu") for it in x.findall("observationInteretDto/items/items") if txt(it, "contenu")]
        if obs:
            c["observations"] = obs
        out.setdefault(f"{norm(nom)}|{iso(txt(dec, 'dateNaissance'))}", []).append({
            "p": txt(dec, "prenom"), "d": d, "t": t, "q": txt(g, "qualiteDeclarantForPDF").replace("/", " · "), "mod": mod,
            "pdf": fichiers.get((norm(nom), d, t.lower() + ("m" if mod else ""))) or "", "c": c})
    for l in out.values():
        l.sort(key=lambda e: e["d"], reverse=True)
    (RAW / "hatvp_contenu.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    n = sum(map(len, out.values()))
    print(f"HATVP : {n} déclarations d'intérêts de {len(out)} personnes ; PDF retrouvé pour",
          sum(bool(e["pdf"]) for l in out.values() for e in l))


if __name__ == "__main__":
    main()
