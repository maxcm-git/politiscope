#!/usr/bin/env python3
"""Activité des députés (17e législature, open data de l'Assemblée nationale), clé « prénom|nom » normalisée.

Sorties :
  data/raw/activite.json         compteurs : propositions déposées (auteur) et cosignées, devenues lois,
                                 questions écrites (et répondues), orales, au gouvernement, amendements (auteur,
                                 adoptés, cosignés)
  data/raw/activite_detail.json  listes : propositions [date, type, titre, n° de loi, lien Légifrance] et
                                 dernières questions écrites [date, rubrique, analyse, ministère, répondue]
Sources (cache data/_cache/, téléchargées si absentes) : dossiers législatifs, questions écrites, orales
sans débat, au gouvernement, amendements. Les amendements (~350 Mo) sont lus dans l'archive sans extraction."""
import json, re
from enrich_votes import fetch_zip, norm, aslist, ACTEURS, ROOT

RAW = ROOT / "data" / "raw"
BASE = "https://data.assemblee-nationale.fr/static/openData/repository/17"
SRC = {"dossiers.zip": f"{BASE}/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip",
       "questions_ecrites.zip": f"{BASE}/questions/questions_ecrites/Questions_ecrites.json.zip",
       "questions_orales.zip": f"{BASE}/questions/questions_orales_sans_debat/Questions_orales_sans_debat.json.zip",
       "questions_gouvernement.zip": f"{BASE}/questions/questions_gouvernement/Questions_gouvernement.json.zip",
       "amendements.zip": f"{BASE}/loi/amendements_div_legis/Amendements.json.zip"}
TYPES = {"PION": "Proposition de loi", "PNRE": "Proposition de résolution", "PRJL": "Projet de loi"}


def val(x):
    return x if isinstance(x, str) else None


def cles_acteurs():
    z = fetch_zip(ACTEURS, "acteurs.zip")
    out = {}
    for n in z.namelist():
        if "/acteur/" in n and n.endswith(".json"):
            a = json.loads(z.read(n))["acteur"]
            i = a["etatCivil"]["ident"]
            out[n.rsplit("/", 1)[1][:-5]] = f"{norm(i['prenom'])}|{norm(i['nom'])}"
    return out


def chercher(d, cle):
    # Parcours récursif : renvoie toutes les valeurs d'une clé (structures AN profondément imbriquées).
    if isinstance(d, dict):
        for k, v in d.items():
            if k == cle:
                yield v
            yield from chercher(v, cle)
    elif isinstance(d, list):
        for v in d:
            yield from chercher(v, cle)


def main():
    K = cles_acteurs()
    stats, detail = {}, {}
    S = lambda ref: stats.setdefault(K.get(ref, ref), {})
    inc = lambda ref, k, n=1: S(ref).__setitem__(k, S(ref).get(k, 0) + n)

    # Dossiers : promulgation -> numéro de loi et lien Légifrance.
    z = fetch_zip(SRC["dossiers.zip"], "dossiers.zip")
    lois = {}
    for n in z.namelist():
        if "/dossierParlementaire/" in n:
            d = json.loads(z.read(n))["dossierParlementaire"]
            for a in chercher(d, "acteLegislatif"):
                for x in aslist(a):
                    if isinstance(x, dict) and x.get("codeActe") == "PROM-PUB" and x.get("codeLoi"):
                        lois[d["uid"]] = [x["codeLoi"], (x.get("infoJO") or {}).get("urlLegifrance") or ""]
    # Propositions déposées par des députés (auteur) et cosignées.
    for n in z.namelist():
        if "/document/" not in n:
            continue
        doc = json.loads(z.read(n))["document"]
        typ = (((doc.get("classification") or {}).get("type")) or {}).get("code")
        if doc.get("legislature") != "17" or typ not in ("PION", "PNRE"):
            continue
        loi = lois.get(doc.get("dossierRef"), ["", ""])
        titres = doc.get("titres") or {}
        titre = titres.get("titrePrincipalCourt") or titres.get("titrePrincipal") or ""
        date = (((doc.get("cycleDeVie") or {}).get("chrono") or {}).get("dateDepot") or "")[:10]
        for au in aslist((doc.get("auteurs") or {}).get("auteur")):
            ref = (au.get("acteur") or {}).get("acteurRef")
            if ref and (au["acteur"].get("qualite") == "auteur"):
                inc(ref, "propositions")
                if loi[0]:
                    inc(ref, "lois")
                detail.setdefault(K.get(ref, ref), {}).setdefault("propositions", []).append(
                    [date, TYPES[typ], titre[:1].upper() + titre[1:], loi[0], loi[1]])
        for co in aslist((doc.get("coSignataires") or {}).get("coSignataire")):
            ref = (co.get("acteur") or {}).get("acteurRef")
            if ref and not val(co.get("dateRetraitCosignature")):
                inc(ref, "cosignees")

    # Questions.
    for fichier, cle in (("questions_ecrites.zip", "qe"), ("questions_orales.zip", "qo"), ("questions_gouvernement.zip", "qag")):
        z = fetch_zip(SRC[fichier], fichier)
        for n in z.namelist():
            if not n.endswith(".json"):
                continue
            q = json.loads(z.read(n))["question"]
            ref = ((q.get("auteur") or {}).get("identite") or {}).get("acteurRef")
            if not ref:
                continue
            inc(ref, cle)
            if cle == "qe":
                repondue = bool(q.get("textesReponse"))
                inc(ref, "qe_repondues", int(repondue))
                date = next((v.get("dateJO") for v in chercher(q.get("minAttribs"), "infoJO") if isinstance(v, dict) and v.get("dateJO")), "")
                analyses = (q.get("indexationAN") or {}).get("analyses") or {}
                analyse = aslist(analyses.get("analyse"))[0] if analyses.get("analyse") else ""
                detail.setdefault(K.get(ref, ref), {}).setdefault("questions", []).append(
                    [(date or "")[:10], (q.get("indexationAN") or {}).get("rubrique") or "", analyse if isinstance(analyse, str) else "",
                     ((q.get("minInt") or {}).get("developpe") or ""), int(repondue)])

    # Amendements : lecture en flux, un JSON par amendement.
    z = fetch_zip(SRC["amendements.zip"], "amendements.zip")
    lus = 0
    for n in z.namelist():
        if not n.endswith(".json"):
            continue
        a = json.loads(z.read(n))["amendement"]
        sig = a.get("signataires") or {}
        au = sig.get("auteur") or {}
        if au.get("typeAuteur") == "Député" and val(au.get("acteurRef")):
            inc(au["acteurRef"], "amendements")
            sort = next((v for v in chercher(a.get("cycleDeVie"), "sort") if isinstance(v, str)), "")
            if sort.lower().startswith("adopt"):
                inc(au["acteurRef"], "amendements_adoptes")
        for ref in aslist((sig.get("cosignataires") or {}).get("acteurRef")):
            if isinstance(ref, str):
                inc(ref, "amendements_cosignes")
        lus += 1

    for d in detail.values():
        d.get("propositions", []).sort(reverse=True)
        d["questions"] = sorted(d.get("questions", []), reverse=True)[:40]
    stats = {k: v for k, v in stats.items() if not k.startswith("PA")}
    (RAW / "activite.json").write_text(json.dumps(stats, ensure_ascii=False), encoding="utf-8")
    (RAW / "activite_detail.json").write_text(json.dumps(detail, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(stats)} acteurs ; {len(lois)} lois promulguées ; {lus} amendements lus")


if __name__ == "__main__":
    main()
