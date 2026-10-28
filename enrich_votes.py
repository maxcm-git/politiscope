#!/usr/bin/env python3
"""Agrège les votes nominatifs des députés depuis l'open data officiel de l'Assemblée
nationale (17e législature). Sorties (clé = « prénom|nom » normalisés) :
  data/raw/votes_deputes.json    totaux, participation, vote conforme à la majorité de son groupe
  data/raw/scrutins.json         [numéro, date, titre, résultat, pour, contre, abstention], du plus récent au plus ancien
  data/raw/scrutins_groupes.json par scrutin (même ordre) : [[groupe (organeRef), pour, contre, abst., non-votants], …]
  data/raw/votes_positions.json  par député : [indice du scrutin, position (0 pour, 1 contre, 2 abst., 3 non-votant),
                                 conforme à la majorité de son groupe (1/0, ou -1 si le groupe n'a pas de majorité)]

Sources (téléchargées dans un cache si absentes) :
  - Scrutins   : .../repository/17/loi/scrutins/Scrutins.json.zip  (un JSON par scrutin)
  - Acteurs    : .../repository/17/amo/.../AMO30_...historique.json.zip  (acteurRef -> nom)

Le Sénat ne publie pas ses votes nominatifs en open data (seulement en pages web sur senat.fr) :
pas de volet sénateurs ici.

Relancer après une mise à jour des scrutins. Idempotent."""
import json, re, io, zipfile, urllib.request, unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
CACHE = ROOT / "data" / "_cache"            # archives volumineuses, hors livrable
OUT = ROOT / "data" / "raw" / "votes_deputes.json"
BASE = "https://data.assemblee-nationale.fr/static/openData/repository/17"
SCRUTINS = f"{BASE}/loi/scrutins/Scrutins.json.zip"
ACTEURS = (f"{BASE}/amo/tous_acteurs_mandats_organes_xi_legislature/"
           "AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def fetch_zip(url, name):
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / name
    if not dest.exists():
        print("téléchargement", name, "…")
        urllib.request.urlretrieve(url, dest)
    return zipfile.ZipFile(dest)


def aslist(x):
    return [] if x is None else x if isinstance(x, list) else [x]


def tally_scrutins(zf):
    # Parcourt chaque scrutin -> position de chaque acteurRef et majorité de son groupe.
    acc, positions, scrutins, groupes = {}, {}, [], {}  # acc : acteurRef -> [pour, contre, abst, nonvotant]
    POS = {"pours": 0, "contres": 1, "abstentions": 2, "nonVotants": 3}
    MAJ = {"pour": 0, "contre": 1, "abstention": 2}
    for info in zf.infolist():
        if not info.filename.endswith(".json"):
            continue
        sc = json.loads(zf.read(info))["scrutin"]
        organe = sc.get("ventilationVotes", {}).get("organe")
        if not organe:
            continue
        organe = organe[0] if isinstance(organe, list) else organe
        sv = (sc.get("syntheseVote") or {}).get("decompte") or {}
        scrutins.append([sc["uid"], int(sc.get("numero") or 0), sc.get("dateScrutin", ""), (sc.get("titre") or "").strip(),
                         (sc.get("sort") or {}).get("code", ""), int(sv.get("pour") or 0), int(sv.get("contre") or 0),
                         int(sv.get("abstentions") or 0)])
        for g in aslist(organe.get("groupes", {}).get("groupe")):
            vote = g.get("vote", {})
            dv = vote.get("decompteVoix") or {}
            groupes.setdefault(sc["uid"], []).append([g.get("organeRef")] + [int(dv.get(c) or 0) for c in
                                                     ("pour", "contre", "abstentions", "nonVotants")])
            maj = MAJ.get(vote.get("positionMajoritaire"), -1)
            dn = vote.get("decompteNominatif") or {}
            for champ, idx in POS.items():
                blk = dn.get(champ)
                for v in aslist(blk.get("votant") if isinstance(blk, dict) else None):
                    ref = v.get("acteurRef")
                    if ref:
                        acc.setdefault(ref, [0, 0, 0, 0])[idx] += 1
                        conf = -1 if maj < 0 or idx == 3 else int(idx == maj)
                        positions.setdefault(ref, []).append([sc["uid"], idx, conf])
    return acc, positions, scrutins, groupes


def name_of(zf_names, zf, ref):
    path = next((n for n in zf_names if n.endswith(f"/acteur/{ref}.json")), None)
    if not path:
        return None
    ident = json.loads(zf.read(path))["acteur"]["etatCivil"]["ident"]
    return ident.get("prenom"), ident.get("nom")


def main():
    acc, positions, scrutins, groupes = tally_scrutins(fetch_zip(SCRUTINS, "scrutins.zip"))
    print(f"{len(acc)} acteurs votants agrégés sur {len(scrutins)} scrutins")
    scrutins.sort(key=lambda s: (s[2], s[1]), reverse=True)
    idx = {s[0]: i for i, s in enumerate(scrutins)}
    za = fetch_zip(ACTEURS, "acteurs.zip")
    names = za.namelist()
    out, pos_out = {}, {}
    manquants = 0
    for ref, (p, c, a, nv) in acc.items():
        nm = name_of(names, za, ref)
        if not nm:
            manquants += 1
            continue
        exprimes = p + c + a
        total = exprimes + nv  # scrutins où le groupe était ventilé le concernant
        conf = [x[2] for x in positions[ref] if x[2] >= 0]
        k = f"{norm(nm[0])}|{norm(nm[1])}"
        out[k] = {
            "pour": p, "contre": c, "abstention": a, "nonvotant": nv,
            "exprimes": exprimes, "scrutins": total,
            "participation": round(100 * exprimes / total) if total else None,
            # vote conforme à la position majoritaire de son groupe (l'AN publie la majorité, pas la consigne)
            "conforme": round(100 * sum(conf) / len(conf)) if conf else None, "conforme_n": len(conf),
        }
        pos_out[k] = sorted([idx[u], i, cf] for u, i, cf in positions[ref])
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    (OUT.parent / "scrutins.json").write_text(json.dumps([s[1:] for s in scrutins], ensure_ascii=False,
                                                          separators=(",", ":")), encoding="utf-8")
    (OUT.parent / "scrutins_groupes.json").write_text(json.dumps([groupes.get(s[0], []) for s in scrutins],
                                                                  separators=(",", ":")), encoding="utf-8")
    (OUT.parent / "votes_positions.json").write_text(json.dumps(pos_out, separators=(",", ":")), encoding="utf-8")
    print(f"{len(out)} députés écrits -> {OUT} ({manquants} acteurRef sans nom)")


if __name__ == "__main__":
    main()
