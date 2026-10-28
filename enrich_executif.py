#!/usr/bin/env python3
"""Président de la République + membres du Gouvernement en exercice -> data/raw/executif.json.

Aucune source unique n'est fiable pour « qui est en poste » :
  - Assemblée nationale (AMO, acteurs) : mandats GOUVERNEMENT / PRESREP avec dates, mais certains
    mandats d'anciens gouvernements ne sont jamais clôturés, et pas d'intitulé de portefeuille ;
  - HATVP (liste.csv) : intitulé exact de la fonction, mais pas de date de fin.
Règle : mandat ouvert à l'AN ET déclaration gouvernementale à la HATVP (hors fin de fonctions
postérieure). Les mandats AN non clôturés d'anciens ministres n'ont aucune ligne HATVP
« gouvernement » : ils tombent d'eux-mêmes.

Dépend de data/_cache/acteurs.zip (téléchargé par enrich_votes.fetch_zip) et data/raw/hatvp_liste.csv."""
import csv, json
from enrich_votes import fetch_zip, norm, aslist, ACTEURS, ROOT

RAW = ROOT / "data" / "raw"
OUT = RAW / "executif.json"


def val(x):
    return x if isinstance(x, str) else None  # les champs vides AN sont des objets xsi:nil


def main():
    hv = {}
    with open(RAW / "hatvp_liste.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["type_mandat"] in ("gouvernement", "president"):
                hv.setdefault((norm(r["prenom"]), norm(r["nom"])), []).append(r)

    z = fetch_zip(ACTEURS, "acteurs.zip")
    out = []
    for n in z.namelist():
        if "/acteur/" not in n or not n.endswith(".json"):
            continue
        a = json.loads(z.read(n))["acteur"]
        ident = a["etatCivil"]["ident"]
        ouverts = [m for m in aslist(a.get("mandats", {}).get("mandat"))
                   if m.get("typeOrgane") in ("GOUVERNEMENT", "PRESREP") and not val(m.get("dateFin"))]
        if not ouverts:
            continue
        m = max(ouverts, key=lambda m: val(m.get("dateDebut")) or "")
        debut = val(m.get("dateDebut")) or ""
        rs = sorted(hv.get((norm(ident["prenom"]), norm(ident["nom"])), []),
                    key=lambda r: r["date_depot"] or "")
        if any(r["type_document"] == "dspfm" and (r["date_depot"] or "") >= debut for r in rs):
            continue  # fin de fonctions déclarée après la nomination
        titre = next((r["qualite"] for r in reversed(rs) if r["type_document"] != "dspfm"), None)
        if not titre:
            continue  # mandat AN jamais clôturé d'un ancien ministre
        prof = (a.get("profession") or {}).get("libelleCourant")
        out.append({
            "prenom": ident["prenom"], "nom": ident["nom"],
            "sexe": "F" if ident.get("civ") == "Mme" else "H",
            "naissance": val(a["etatCivil"].get("infoNaissance", {}).get("dateNais")) or "",
            "profession": val(prof) or "",
            "chambre": "president" if m["typeOrgane"] == "PRESREP" else "gouvernement",
            "titre": titre, "debut": debut,
        })
    out.sort(key=lambda x: (x["chambre"] != "president", x["titre"] != "Premier ministre", x["nom"]))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} membres de l'exécutif -> {OUT}")
    for x in out[:3]:
        print(" ", x["prenom"], x["nom"], "|", x["titre"], "| depuis", x["debut"])


if __name__ == "__main__":
    main()
