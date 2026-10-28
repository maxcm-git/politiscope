#!/usr/bin/env python3
"""Agenda du Parlement et présence en commission (open data de l'Assemblée nationale, 17e législature).

Sorties :
  data/raw/agenda.json          réunions de J-7 à J+28, de la plus proche à la plus lointaine :
                                {d: début ISO, t: "seance"|"commission"|"autre", ch: "AN"|"Sénat", o: organe,
                                 e: état, p: [objets à l'ordre du jour]} ; réunions annulées ou supprimées exclues
  data/raw/presence_com.json    par député (clé « prénom|nom ») : [présent, excusé, absent] aux réunions de
                                commission dont l'AN publie le relevé de présence
  data/raw/organes_an.json      organeRef -> [libellé, abrégé] (groupes politiques), pour les scrutins par groupe
Source : .../repository/17/vp/reunions/Agenda.json.zip (une réunion par fichier ; l'AN y reprend aussi les
séances publiques du Sénat)."""
import json, datetime
from enrich_votes import fetch_zip, aslist, ACTEURS, ROOT
from enrich_activite import cles_acteurs, val

RAW = ROOT / "data" / "raw"
AGENDA = "https://data.assemblee-nationale.fr/static/openData/repository/17/vp/reunions/Agenda.json.zip"
TYPES = {"seance_type": "seance", "reunionCommission_type": "commission"}
POS = {"présent": 0, "excusé": 1, "absent": 2}


def main():
    za = fetch_zip(ACTEURS, "acteurs.zip")
    organes = {}
    for n in za.namelist():
        if "/organe/" in n and n.endswith(".json"):
            o = json.loads(za.read(n))["organe"]
            organes[o["uid"]] = [o.get("libelle") or "", val(o.get("libelleAbrev")) or "", o.get("codeType")]
    zd = fetch_zip("https://data.assemblee-nationale.fr/static/openData/repository/17/loi/dossiers_legislatifs/"
                   "Dossiers_Legislatifs.json.zip", "dossiers.zip")
    dossiers = {}
    for n in zd.namelist():
        if "/dossierParlementaire/" in n:
            d = json.loads(zd.read(n))["dossierParlementaire"]
            dossiers[d["uid"]] = (d.get("titreDossier") or {}).get("titre") or ""

    K = cles_acteurs()
    today = datetime.date.today()
    debut, fin = str(today - datetime.timedelta(days=7)), str(today + datetime.timedelta(days=29))
    z = fetch_zip(AGENDA, "agenda.zip")
    agenda, presence = [], {}
    for n in z.namelist():
        if not n.endswith(".json"):
            continue
        r = json.loads(z.read(n))["reunion"]
        etat = (r.get("cycleDeVie") or {}).get("etat")
        for p in aslist(((r.get("participants") or {}).get("participantsInternes") or {}).get("participantInterne")):
            i = POS.get(p.get("presence"))
            if i is not None and p.get("acteurRef") in K:
                presence.setdefault(K[p["acteurRef"]], [0, 0, 0])[i] += 1
        quand = r.get("timeStampDebut") or ""
        if etat in ("Annulé", "Supprimé") or not debut <= quand[:10] <= fin:
            continue
        points = []
        odj = r.get("ODJ") or {}
        for pt in aslist((odj.get("pointsODJ") or {}).get("pointODJ")):
            if (pt.get("cycleDeVie") or {}).get("etat") == "Supprimé":
                continue
            ref = (pt.get("dossiersLegislatifsRefs") or {}).get("dossierRef")
            ref = ref[0] if isinstance(ref, list) else ref
            objet = pt.get("objet") or ""
            # « Discussion » seul : le titre du dossier dit de quoi il s'agit
            points.append(f"{objet} : {dossiers[ref]}" if ref in dossiers and len(objet) < 30 else objet)
        if not points:
            points = [x for x in aslist((odj.get("resumeODJ") or {}).get("item")) if isinstance(x, str)]
        org = organes.get(r.get("organeReuniRef"), ["", ""])
        agenda.append({"d": quand[:16], "t": TYPES.get(r.get("@xsi:type"), "autre"),
                       "ch": "Sénat" if r["uid"].startswith("RUSN") else "AN", "o": org[0],
                       "e": etat, "p": [x.strip(" –-") for x in points if x.strip()]})
    agenda.sort(key=lambda a: a["d"])
    (RAW / "agenda.json").write_text(json.dumps(agenda, ensure_ascii=False), encoding="utf-8")
    (RAW / "presence_com.json").write_text(json.dumps(presence), encoding="utf-8")
    (RAW / "organes_an.json").write_text(json.dumps(
        {k: v[:2] for k, v in organes.items() if v[2] == "GP"}, ensure_ascii=False), encoding="utf-8")
    print(f"agenda : {len(agenda)} réunions du {debut} au {fin} ; présence en commission : {len(presence)} députés")


if __name__ == "__main__":
    main()
