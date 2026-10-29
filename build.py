#!/usr/bin/env python3
"""Assemble le site : fiches nationales (Parlement, gouvernement) -> site/data.js, puis élus locaux via
build_local.py. Lit les sorties des scripts enrich_*.py ; zéro dépendance (stdlib).
Normalement lancé par update.py, qui récupère les sources et contrôle le résultat."""
import csv, json, unicodedata, re, datetime
from pathlib import Path

RAW = Path(__file__).parent / "data" / "raw"
OUT = Path(__file__).parent / "site" / "data.js"


def _maj_rne():
    # Date de publication du RNE utilisé, relevée par update.py (repli : version initiale du prototype).
    try:
        d = json.load(open(RAW / "sources.json", encoding="utf-8"))["rne"]["maj"]
        return f"{d[8:10]}/{d[5:7]}/{d[:4]}"
    except Exception:
        return "11/08/2026"


MAJ = _maj_rne()

# Rémunérations brutes mensuelles, calculées sur la base légale commune : moyenne du traitement
# « hors échelle » le plus bas (HEA 1er chevron, IM 895) et le plus élevé (HEG, IM 1515), au point
# d'indice de 4,92278 € (grille au 1er janvier 2024, point gelé depuis juillet 2023).
# shortcut: constantes en dur, à mettre à jour si un décret revalorise le point ou la grille.
POINT, IM_HE_MIN, IM_HE_MAX = 4.92278, 895, 1515
MOY_HE = (IM_HE_MIN + IM_HE_MAX) / 2 * POINT  # 5 931,95 €


def remu(coef):
    # coef × moyenne HE, + indemnité de résidence 3 %, + indemnité de fonction 25 % (de base + résidence).
    return round(coef * MOY_HE * 1.03 * 1.25)


assert remu(1) == 7637 and remu(1.4) == 10692  # recoupe les montants publiés (AN, presse)

INDEMNITE = {  # (montant, source)
    "depute": (remu(1), "ordonnance n° 58-1210, art. 1 — calcul sur la grille hors échelle"),
    "senateur": (remu(1), "ordonnance n° 58-1210, art. 1 — calcul sur la grille hors échelle"),
    "eurodepute": (10075, "statut des députés européens — valeur non recalculée, à vérifier"),
}
COEF_EXEC = [  # (début de l'intitulé, coefficient, texte)
    ("Président de la République", 2.1, "décret n° 2012-983, art. 1 et 3"),
    ("Premier ministre", 2.1, "décret n° 2012-983, art. 1 et 3"),
    ("Première ministre", 2.1, "décret n° 2012-983, art. 1 et 3"),
    ("Secrétaire d'État", 1.33, "décret n° 2014-425, art. 2"),
    ("", 1.4, "décret n° 2012-983, art. 2"),  # ministres et ministres délégués
]
LABEL = {
    "depute": ("Député", "Députée"),
    "senateur": ("Sénateur", "Sénatrice"),
    "eurodepute": ("Député européen", "Députée européenne"),
}


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def titlecase(s):
    # Les noms RNE sont en MAJUSCULES ; on recapitalise chaque mot et chaque
    # élément de nom composé (séparé par - ou ') : "Marie-josé" -> "Marie-José".
    return re.sub(r"[A-Za-zÀ-ÿ]+",
                  lambda m: m.group(0).capitalize(), s.lower())


def read(fname):
    with open(RAW / fname, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def age(dob):
    try:
        d = datetime.date.fromisoformat(dob)
        t = datetime.date.today()
        return t.year - d.year - ((t.month, t.day) < (d.month, d.day))
    except Exception:
        return None


def anciennete(debut):
    try:
        d = datetime.date.fromisoformat(debut)
        return round((datetime.date.today() - d).days / 365.25, 1)
    except Exception:
        return None


def norm(s):
    # Clé de rapprochement insensible aux accents/casse/ponctuation.
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def load_json(fname):
    with open(RAW / fname, encoding="utf-8") as f:
        return json.load(f)


def hatvp_interets():
    # HATVP liste.csv : déclarations d'INTÉRÊTS seulement (di/dia + modificatives). Les dsp*
    # (patrimoine) sont exclues : non publiables en France. On garde méta + lien officiel,
    # sans republier le contenu.
    MANDAT = {"depute": "depute", "senateur": "senateur", "europe": "eurodepute",
              "gouvernement": "gouvernement", "president": "president"}
    out = {}
    for r in read("hatvp_liste.csv"):
        ch = MANDAT.get(r["type_mandat"])
        if ch and r["type_document"].startswith("dsp") and r["statut_publication"] == "Livrée":
            # patrimoine : seule la date de mise à disposition est reprise (consultation en préfecture ou sur hatvp.fr)
            d = out.setdefault((ch, norm(r["prenom"]), norm(r["nom"])), {"url": "", "nb": 0, "derniere": None, "statut": "", "_depot": "", "pdfs": []})
            d["url"] = d["url"] or ("https://www.hatvp.fr" + r["url_dossier"] if r["url_dossier"] else "")
            d["patrimoine"] = max(d.get("patrimoine") or "", r["date_publication"] or "") or None
        if not ch or r["type_document"] not in ("di", "dia", "dim", "diam"):
            continue
        d = out.setdefault((ch, norm(r["prenom"]), norm(r["nom"])), {
            "url": "https://www.hatvp.fr" + r["url_dossier"] if r["url_dossier"] else "",
            "nb": 0, "derniere": None, "statut": "", "_depot": "", "pdfs": []})
        d["nb"] += 1
        if r["nom_fichier"] and r["statut_publication"] == "Livrée":  # PDF officiel, copié dans site/hatvp/ par build_local
            d["pdfs"].append([r["date_depot"], r["type_document"], r["nom_fichier"]])
        if r["statut_publication"] == "Livrée" and r["date_publication"] > (d["derniere"] or ""):
            d["derniere"] = r["date_publication"]
        if (r["date_depot"] or "") >= d["_depot"]:
            d["_depot"], d["statut"] = r["date_depot"] or "", r["statut_publication"]
    for d in out.values():
        del d["_depot"]
        d["pdfs"].sort(reverse=True)
    return out


def fonction_courte(x):
    # Intitulé HATVP complet -> libellé court pour l'annuaire (déjà genré dans la source).
    t = x["titre"]
    if x["chambre"] == "president":
        return "Président de la République"
    if t.startswith(("Premier ministre", "Première ministre")):
        return t
    if t.startswith("Ministre délégué"):
        return t.split(",")[0].split(" auprès")[0]
    return "Ministre"


def remu_exec(fonction):
    coef, texte = next((c, t) for debut, c, t in COEF_EXEC if fonction.startswith(debut))
    return {"indemnite": remu(coef),
            "indemnite_source": f"{texte} — calcul sur la grille hors échelle"}


def mk_exec(x):
    # Membres de l'exécutif (data/raw/executif.json, cf. enrich_executif.py).
    return {
        "slug": "", "nom": x["nom"], "prenom": x["prenom"],
        "chambre": x["chambre"], "fonction": fonction_courte(x), "titre": x["titre"],
        "sexe": x["sexe"], "naissance": x["naissance"], "age": age(x["naissance"]),
        "departement": "", "circonscription": "", "dep": "", "circo_code": "",
        "profession": x["profession"],
        "debut": x["debut"], "anciennete": anciennete(x["debut"]),
        **remu_exec(fonction_courte(x) if x["chambre"] != "president" else "Président de la République"),
        "groupe": None, "groupe_label": "",
    }


def mk_roster(x):
    # Député (Assemblée nationale) ou sénateur (Sénat) en exercice, cf. enrich_parlement.py.
    ch, femme = x["chambre"], x["sexe"] == "F"
    return {
        "slug": "", "nom": x["nom"], "prenom": x["prenom"],
        "chambre": ch, "fonction": LABEL[ch][1 if femme else 0], "sexe": x["sexe"],
        "naissance": x["naissance"], "age": age(x["naissance"]),
        "departement": x["departement"], "circonscription": "", "dep": x["dep"], "circo_code": x["circo_code"],
        "profession": x["profession"], "debut": x["debut"], "anciennete": anciennete(x["debut"]),
        "indemnite": INDEMNITE[ch][0], "indemnite_source": INDEMNITE[ch][1],
        "groupe": x["groupe"] or None, "groupe_label": x["groupe_label"] or "",
    }


def mk(row, chambre):
    nom, prenom = titlecase(row["Nom de l'élu"]), titlecase(row["Prénom de l'élu"])
    dob = row.get("Date de naissance", "")
    debut = row.get("Date de début du mandat", "")
    dep = row.get("Libellé du département", "") or row.get(
        "Libellé de la collectivité à statut particulier", "")
    circo = row.get("Libellé de la circonscription législative", "")
    femme = row.get("Code sexe") == "F"
    return {
        "slug": "", "nom": nom, "prenom": prenom,
        "chambre": chambre, "fonction": LABEL[chambre][1 if femme else 0],
        "sexe": "F" if femme else "H",
        "naissance": dob, "age": age(dob),
        "departement": dep, "circonscription": titlecase(circo) if circo else "",
        "dep": row.get("Code du département", "") or row.get("Code de la collectivité à statut particulier", ""),
        "circo_code": row.get("Code de la circonscription législative", ""),
        "profession": row.get("Libellé de la catégorie socio-professionnelle", ""),
        "debut": debut, "anciennete": anciennete(debut),
        "indemnite": INDEMNITE[chambre][0], "indemnite_source": INDEMNITE[chambre][1],
        "groupe": None, "groupe_label": "",
    }


def eurodeputes():
    """Eurodéputés : le Parlement européen fait foi pour qui siège (le RNE retarde : en octobre 2026 il gardait un eurodéputé
    devenu sénateur). État civil : RNE, ou à défaut la liste des candidatures aux européennes 2024 (remplaçants)."""
    rne = [mk(r, "eurodepute") for r in read("eurodeputes.csv")]
    if not (RAW / "pe_membres.json").exists():
        return rne
    pe = [m for m in load_json("pe_membres.json")["list"] if m.get("countryLabel") == "France"]
    noms = {norm(m["fullName"]) for m in pe}
    cle = lambda p: {norm(p["prenom"] + p["nom"]), norm(p["nom"] + p["prenom"])}
    garde = [p for p in rne if cle(p) & noms]
    connus = set().union(*map(cle, garde))
    cand = {}
    for r in read("elections/eur2024_candidats.csv"):
        n, pr = r["Nom sur le bulletin de vote"], r["Prénom sur le bulletin de vote"]
        cand[norm(pr + n)] = cand[norm(n + pr)] = r
    ajouts = []
    for m in pe:
        r = cand.get(norm(m["fullName"]))
        if norm(m["fullName"]) in connus:
            continue
        if not r:
            print("eurodéputé sans état civil, non affiché :", m["fullName"])
            continue
        j, mo, a = r["Date de naissance"].split("/")
        ajouts.append(mk({"Nom de l'élu": r["Nom sur le bulletin de vote"], "Prénom de l'élu": r["Prénom sur le bulletin de vote"],
                          "Code sexe": r["Sexe"], "Date de naissance": f"{a}-{mo}-{j}",
                          "Libellé de la catégorie socio-professionnelle": re.sub(r"^\(\d+\) - ", "", r["Profession"])}, "eurodepute"))
    print("eurodéputés : retirés car absents du Parlement européen :", [f"{p['prenom']} {p['nom']}" for p in rne if p not in garde],
          "· ajoutés depuis le Parlement européen :", [f"{p['prenom']} {p['nom']}" for p in ajouts])
    return garde + ajouts


def main():
    # Députés et sénateurs : chaque chambre fait foi pour ses membres (roster.json, enrich_parlement.py) ;
    # le RNE retarde sur les changements en cours d'année. Repli sur le RNE si le roster est absent.
    if (RAW / "roster.json").exists():
        people = [mk_roster(x) for x in load_json("roster.json")]
    else:
        people = [mk(r, "depute") for r in read("deputes.csv")] + [mk(r, "senateur") for r in read("senateurs.csv")]
    parl = {(norm(p["prenom"]), norm(p["nom"])) for p in people}
    eur = eurodeputes()
    # Mandat européen incompatible avec un siège au Parlement : la chambre fait foi (RNE en retard, sans liste du PE).
    print("Eurodéputé devenu parlementaire national, ligne européenne retirée :",
          [f"{p['prenom']} {p['nom']}" for p in eur if (norm(p["prenom"]), norm(p["nom"])) in parl])
    people += [p for p in eur if (norm(p["prenom"]), norm(p["nom"])) not in parl]
    if (RAW / "executif.json").exists():
        execs = [mk_exec(x) for x in load_json("executif.json")]
        ek = {(norm(x["prenom"]), norm(x["nom"])) for x in execs}
        doublons = [f"{p['prenom']} {p['nom']} ({p['chambre']})" for p in people
                    if (norm(p["prenom"]), norm(p["nom"])) in ek]
        if doublons:
            # Un ministre ne peut pas siéger (incompatibilité) : la source parlementaire est en retard, l'exécutif prime.
            print("Fonction gouvernementale incompatible, ligne parlementaire retirée :", doublons)
            people = [p for p in people if (norm(p["prenom"]), norm(p["nom"])) not in ek]
        people += execs

    # Votes nominatifs des députés (open data AN, via enrich_votes.py). Absent -> pas de volet votes.
    votes = load_json("votes_deputes.json") if (RAW / "votes_deputes.json").exists() else {}
    vmiss = 0
    for p in people:
        if p["chambre"] == "depute":
            v = votes.get(f"{norm(p['prenom'])}|{norm(p['nom'])}")
            p["votes"] = v
            if not v:
                vmiss += 1
    print("députés sans votes rapprochés:", vmiss, "/", sum(p["chambre"] == "depute" for p in people))

    # Déclarations d'intérêts HATVP (3 chambres).
    hv = hatvp_interets()
    hmiss = {ch: 0 for ch in {p["chambre"] for p in people}}
    for p in people:
        p["interets"] = hv.get((p["chambre"], norm(p["prenom"]), norm(p["nom"])))
        if not p["interets"]:
            hmiss[p["chambre"]] += 1
    print("sans déclaration d'intérêts rapprochée:", hmiss)

    # Groupe des eurodéputés (Parlement européen) ; députés et sénateurs l'ont déjà (source officielle).
    if (RAW / "pe_membres.json").exists():
        pe = {norm(m["fullName"]): m for m in load_json("pe_membres.json")["list"] if m.get("countryLabel") == "France"}
        for p in people:
            if p["chambre"] == "eurodepute":
                m = pe.get(norm(p["prenom"] + p["nom"])) or pe.get(norm(p["nom"] + p["prenom"]))
                if m:
                    p["groupe"] = p["groupe_label"] = m["politicalGroupLabel"]
                    p["parti_national"] = m.get("nationalPoliticalGroupLabel", "")

    # Fiches enrichies : photo, lieu de naissance, contact professionnel, commissions (enrich_parlement.py).
    details = load_json("parlement.json") if (RAW / "parlement.json").exists() else {}
    for p in people:
        p.update(details.get(f"{norm(p['prenom'])}|{norm(p['nom'])}", {}))
    cc = load_json("credits_commons.json") if (RAW / "credits_commons.json").exists() else {}
    for p in people:  # Commons : auteur et licence (attribution exigée par CC BY / BY-SA), page source
        c = cc.get(f"{norm(p['prenom'])}|{norm(p['nom'])}")
        if c:
            p["photo_credit"], p["photo_source"] = c["credit"], c["source"]
    print("photos :", sum(bool(p.get("photo")) for p in people), "/", len(people))

    # slugs uniques et déterministes
    seen = {}
    for p in sorted(people, key=lambda x: (x["nom"], x["prenom"])):
        base = slugify(f"{p['prenom']}-{p['nom']}")
        n = seen.get(base, 0) + 1
        seen[base] = n
        p["slug"] = base if n == 1 else f"{base}-{n}"

    # Détail des votes : un fichier par député (site/v/<slug>.json) + table des scrutins, chargés à la demande.
    import shutil
    vdir = OUT.parent / "v"
    shutil.rmtree(vdir, ignore_errors=True)
    vdir.mkdir(parents=True)
    positions = load_json("votes_positions.json") if (RAW / "votes_positions.json").exists() else {}
    for p in people:
        pos = positions.get(f"{norm(p['prenom'])}|{norm(p['nom'])}") if p["chambre"] == "depute" else None
        if pos:
            (vdir / f"{p['slug']}.json").write_text(json.dumps(pos, separators=(",", ":")), encoding="utf-8")
            p["votes_detail"] = True
    if (RAW / "scrutins.json").exists():
        shutil.copy(RAW / "scrutins.json", OUT.parent / "scrutins.json")

    # Activité à l'Assemblée (enrich_activite.py) : compteurs sur la fiche, listes dans site/a/<slug>.json.
    adir = OUT.parent / "a"
    shutil.rmtree(adir, ignore_errors=True)
    adir.mkdir(parents=True)
    act = load_json("activite.json") if (RAW / "activite.json").exists() else {}
    act_det = load_json("activite_detail.json") if (RAW / "activite_detail.json").exists() else {}
    for p in people:
        if p["chambre"] != "depute":
            continue
        k = f"{norm(p['prenom'])}|{norm(p['nom'])}"
        p["activite"] = act.get(k, {})
        if act_det.get(k):
            (adir / f"{p['slug']}.json").write_text(json.dumps(act_det[k], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            p["activite_detail"] = True

    # Législatives 2024 (enrich_elections.py) : résultat de la personne élue dans sa circonscription, si c'est elle.
    elec = load_json("elections.json") if (RAW / "elections.json").exists() else {}
    leg, sen, eur = elec.get("leg", {}), elec.get("sen", {}), elec.get("eur", {})
    for p in people:  # sénatoriales 2023/2026 et européennes 2024 : nom + date de naissance
        k = f"{norm(p['nom'])}|{p.get('naissance', '')}"
        if p["chambre"] == "senateur" and k in sen:
            p["election"] = sen[k]
        elif p["chambre"] == "eurodepute" and k in eur.get("candidats", {}):
            p["election"] = {"europe": True, "panneau": eur["candidats"][k][0], "ordre": eur["candidats"][k][1]}
    print("sénatoriales / européennes rapprochées :", sum(p["chambre"] == "senateur" and bool(p.get("election")) for p in people), "/",
          sum(p["chambre"] == "senateur" for p in people), "·", sum(p["chambre"] == "eurodepute" and bool(p.get("election")) for p in people))
    for p in people:
        r = leg.get(p.get("circo_code") or "") if p["chambre"] == "depute" else None
        if r:
            nom, prenom, _ = r["elu"]
            mots = lambda x: {norm(w) for w in re.split(r"[\s\-()]+", x) if len(norm(w)) >= 3}  # « Taché » / « TACHE DE LA PAGERIE »
            meme = bool(mots(nom) & mots(p["nom"])) and norm(prenom)[:3] == norm(p["prenom"])[:3]
            p["election"] = r if meme else {"autre": True}  # siège obtenu autrement (partielle, remplacement)
    print("législatives 2024 rapprochées :", sum(p["chambre"] == "depute" and "tour" in (p.get("election") or {}) for p in people), "/",
          sum(p["chambre"] == "depute" for p in people))

    # Présence en commission (enrich_agenda.py) : [présent, excusé, absent] aux réunions dont l'AN publie le relevé.
    pres = load_json("presence_com.json") if (RAW / "presence_com.json").exists() else {}
    for p in people:
        if p["chambre"] == "depute" and pres.get(f"{norm(p['prenom'])}|{norm(p['nom'])}"):
            p["presence_com"] = pres[f"{norm(p['prenom'])}|{norm(p['nom'])}"]
    taux = sorted(x[0] / sum(x) for x in (p.get("presence_com") for p in people) if x and sum(x) >= 10)
    mediane_com = round(100 * taux[len(taux) // 2]) if taux else None

    # Parlement en direct : agenda + résultat de chaque scrutin par groupe (site/s/<bloc>.json, 500 scrutins par bloc).
    if (RAW / "agenda.json").exists():
        shutil.copy(RAW / "agenda.json", OUT.parent / "agenda.json")
    sdir = OUT.parent / "s"
    shutil.rmtree(sdir, ignore_errors=True)
    sdir.mkdir(parents=True)
    org = load_json("organes_an.json") if (RAW / "organes_an.json").exists() else {}
    sg = load_json("scrutins_groupes.json") if (RAW / "scrutins_groupes.json").exists() else []
    for i in range(0, len(sg), 500):
        bloc = sg[i:i + 500]
        (sdir / f"{i // 500}.json").write_text(json.dumps(bloc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    people.sort(key=lambda x: (x["nom"], x["prenom"]))
    departements = sorted({p["departement"] for p in people if p["departement"]})
    groupes = sorted({p["groupe"] for p in people if p["groupe"]})
    meta = {
        "maj": MAJ,
        "build": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),  # invalide le cache des JSON chargés à la demande
        "counts": {
            "total": len(people),
            "depute": sum(p["chambre"] == "depute" for p in people),
            "senateur": sum(p["chambre"] == "senateur" for p in people),
            "eurodepute": sum(p["chambre"] == "eurodepute" for p in people),
            "president": sum(p["chambre"] == "president" for p in people),
            "gouvernement": sum(p["chambre"] == "gouvernement" for p in people),
        },
        "departements": departements,
        "groupes": groupes,
        "presence_com_mediane": mediane_com,
        "groupes_an": {r: org.get(r, ["", r]) for r in {g[0] for s in sg for g in s}},  # organeRef -> [libellé, sigle]
        "agenda_maj": datetime.date.today().isoformat(),
        "europeennes": {k: v for k, v in eur.items() if k != "candidats"},  # 9 juin 2024, listes ayant des sièges
        "base_parl": round(MOY_HE, 2),  # indemnité parlementaire de base (plafond de cumul)
    }
    import build_local  # élus locaux + fichiers découpés ; complète `people` (mandats) et `meta`
    build_local.build(people, meta)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "window.META=" + json.dumps(meta, ensure_ascii=False) + ";\n"
        "window.DATA=" + json.dumps(people, ensure_ascii=False) + ";\n",
        encoding="utf-8")
    print(f"{len(people)} élus -> {OUT}")
    print(meta["counts"])


if __name__ == "__main__":
    main()
