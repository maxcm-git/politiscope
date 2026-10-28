#!/usr/bin/env python3
"""Mise à jour complète et contrôlée des données du site.

  python3 update.py            récupère ce qui a changé, vérifie, reconstruit, contrôle
  python3 update.py --geo      idem + recalcule les cartes (contours des communes, à faire une fois par an)
  python3 update.py --check    contrôle seulement le site déjà construit

Déroulé :
 1. Pour chaque source, trouver la dernière version (API data.gouv pour le RNE et le COG, adresses fixes
    ailleurs) et comparer date de modification + taille à la dernière récupération (data/raw/sources.json).
 2. Télécharger ce qui a changé dans data/_staging/, puis VÉRIFIER chaque fichier (lisible, nombre de
    lignes cohérent avec la fois précédente). Au moindre doute : arrêt, rien n'est remplacé.
 3. Remplacer les fichiers, relancer toute la chaîne (enrich_*.py, build_geo.py si --geo, build.py).
 4. Contrôler le site produit (nombre de députés, sénateurs, couverture des votes et des photos…).
 5. Écrire site/sources.json (date de chaque source) pour la page « Mises à jour ».
Code de sortie : 0 si tout est bon, 1 si une source ou un contrôle échoue (pour une tâche planifiée)."""
import collections, os, json, re, shutil, subprocess, sys, urllib.request, zipfile, datetime
from pathlib import Path

ROOT = Path(__file__).parent
RAW, CACHE, STAGE, SITE = ROOT / "data" / "raw", ROOT / "data" / "_cache", ROOT / "data" / "_staging", ROOT / "site"
UA = {"User-Agent": "Mozilla/5.0 (compatible; Politiscope/0.1; prototype de transparence; contact@politiscope.example)"}
AN = "https://data.assemblee-nationale.fr/static/openData/repository/17"
RNE_FICHIERS = [  # fragment de l'adresse data.gouv -> fichier local (ordre : le plus spécifique d'abord)
    ("conseiller-municipal", "conseillers_municipaux.csv"), ("conseiller-communautaire", "conseillers_communautaires.csv"),
    ("conseiller-departemental", "conseillers_departementaux.csv"), ("conseiller-regional", "conseillers_regionaux.csv"),
    ("conseiller-darrondissement", "conseillers_arrondissement.csv"), ("membre-dune-assemblee", "membres_assemblee.csv"),
    ("parlement-europeen", "eurodeputes.csv"), ("conseillers-des-francais", "conseillers_fde.csv"),
    ("assemblee-des-francais", "afe.csv"), ("elus-maire", "maires.csv"), ("elus-senateur", "senateurs.csv"),
    ("elus-depute", "deputes.csv")]
# Plancher de lignes par fichier (première récupération) ; ensuite : au moins 90 % de la fois précédente.
MINIMUM = {"conseillers_municipaux.csv": 400000, "maires.csv": 30000, "deputes.csv": 500, "senateurs.csv": 300,
           "eurodeputes.csv": 75, "conseillers_departementaux.csv": 3500, "conseillers_regionaux.csv": 1500,
           "hatvp_liste.csv": 5000, "cog_communes.csv": 30000, "ODSEN_GENERAL.csv": 2000}


def http(url, methode="GET"):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA, method=methode), timeout=120)


def entete(url):
    try:
        with http(url, "HEAD") as r:
            return r.headers.get("Last-Modified", ""), int(r.headers.get("Content-Length") or 0)
    except Exception:
        return "", 0


def datagouv(dataset):
    with http(f"https://www.data.gouv.fr/api/1/datasets/{dataset}/") as r:
        return json.load(r)["resources"]


def sources():
    """Liste des sources : (id, nom, apport, fréquence en jours, [(url, destination, conversion)])."""
    rne = []
    for res in datagouv("5c34c4d1634f4173183a64f1"):
        nom = next((f for frag, f in RNE_FICHIERS if frag in res["url"]), None)
        if nom and res["url"].endswith(".csv"):
            rne.append((res["url"], RAW / nom, None))
    cog = {}
    for res in datagouv("58c984b088ee386cdb1261f3"):
        for motif, dest in ((r"/v_commune_(\d{4})\.csv$", "cog_communes.csv"), (r"/v_mvt_commune_(\d{4})\.csv$", "cog_mvt.csv")):
            m = re.search(motif, res["url"])
            if m and int(m.group(1)) > cog.get(dest, (0,))[0]:
                cog[dest] = (int(m.group(1)), res["url"])
    senat = [(f"https://data.senat.fr/data/senateurs/{f}.csv", RAW / "senat" / f"{f}.csv", "latin1")
             for f in ("ODSEN_GENERAL", "ODSEN_CUR_COMS", "ODSEN_ELUSEN", "ODSEN_HISTOGROUPES")]
    zips = lambda *l: [(f"{AN}/{u}", CACHE / d, None) for u, d in l]
    return [
        ("rne", "Répertoire national des élus", "tous les élus, état civil et mandats", 92, rne),
        ("cog", "Code officiel géographique (INSEE)", "communes, cantons, fusions", 365,
         [(u, RAW / "geo" / d, None) for d, (_, u) in cog.items()]),
        ("geo", "geo.api.gouv.fr", "communes, population, codes postaux, intercommunalités", 365,
         [("https://geo.api.gouv.fr/communes?fields=nom,code,codesPostaux,codeDepartement,codeRegion,population,codeEpci,centre&format=json",
           RAW / "geo" / "communes.json", None), ("https://geo.api.gouv.fr/departements", RAW / "geo" / "departements.json", None),
          ("https://geo.api.gouv.fr/regions", RAW / "geo" / "regions.json", None)]),
        ("an_acteurs", "Assemblée nationale : députés et organes", "qui siège, groupes, commissions, gouvernement", 1,
         zips(("amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip", "acteurs.zip"))),
        ("an_scrutins", "Assemblée nationale : scrutins", "votes nominatifs", 1, zips(("loi/scrutins/Scrutins.json.zip", "scrutins.zip"))),
        ("an_agenda", "Assemblée nationale : agenda", "séances, réunions de commission, présence en commission", 1,
         zips(("vp/reunions/Agenda.json.zip", "agenda.zip"))),
        ("an_activite", "Assemblée nationale : textes, amendements, questions", "propositions, lois, amendements, questions", 7,
         zips(("loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip", "dossiers.zip"),
              ("questions/questions_ecrites/Questions_ecrites.json.zip", "questions_ecrites.zip"),
              ("questions/questions_orales_sans_debat/Questions_orales_sans_debat.json.zip", "questions_orales.zip"),
              ("questions/questions_gouvernement/Questions_gouvernement.json.zip", "questions_gouvernement.zip"),
              ("loi/amendements_div_legis/Amendements.json.zip", "amendements.zip"))),
        ("elections", "Ministère de l'Intérieur : résultats électoraux", "législatives 2024, municipales 2026, régionales et départementales 2021, sénatoriales 2023 et 2026, européennes 2024 (élus seulement)", 365,
         [(f"https://static.data.gouv.fr/resources/{u}", RAW / "elections" / d, None) for u, d in (
             ("elections-legislatives-des-30-juin-et-7-juillet-2024-resultats-definitifs-du-1er-tour/20240710-171413/resultats-definitifs-par-circonscriptions-legislatives.csv", "leg2024_t1.csv"),
             ("elections-legislatives-des-30-juin-et-7-juillet-2024-resultats-definitifs-du-2nd-tour/20240710-170728/resultats-definitifs-par-circonscription.csv", "leg2024_t2.csv"),
             ("elections-municipales-2026-resultats-du-premier-tour/20260320-164339/municipales-2026-resultats-communes-2026-03-20.csv", "mun2026_t1.csv"),
             ("elections-municipales-2026-resultats-du-scond-tour/20260323-180124/municipales-2026-resultats-communes-2026-03-23-16h14.csv", "mun2026_t2.csv"),
             ("elections-regionales-2021-resultats-du-1er-tour-1/20210713-100257/resultats-par-niveau-reg-t1-france-entiere-2021-07-12-18h36.txt", "reg2021_t1.txt"),
             ("elections-regionales-2021-resultats-du-2eme-tour/20210713-095407/reg-resultats-par-niveau-reg-t2-france-entiere-2021-07-12-09h30.txt", "reg2021_t2.txt"),
             ("elections-departementales-2021-resultats-du-1er-tour/20210622-165856/resultats-par-niveau-can-t1-france-entiere.txt", "dep2021_t1.txt"),
             ("elections-departementales-2021-resultats-du-2eme-tour/20210713-101022/dep-resultats-par-niveau-can-t2-france-entiere-2021-07-12-10h16.txt", "dep2021_t2.txt"),
             ("elections-senatoriales-2023-resultats/20230928-104908/senatoriales-2023-resultats-publication.xlsx", "sen2023.xlsx"),
             ("elections-senatoriales-2023-candidatures-t1/20230918-172919/senatoriales-2023-candidatures-18-09-23-publication.xlsx", "sen2023_listes.xlsx"),
             ("elections-senatoriales-2026-resultats/20260927-235109/senatoriales-2026-candidats-elus.csv", "sen2026_elus.csv"),
             ("elections-senatoriales-2026-resultats/20260927-235109/senatoriales-2026-resultats-t1-scrutin-majoritaire-et-scrutin-proportionnel.csv", "sen2026_t1.csv"),
             ("elections-senatoriales-2026-resultats/20260927-235109/senatoriales-2026-resultats-t2-scrutin-majoritaire.csv", "sen2026_t2.csv"),
             ("elections-senatoriales-2026-candidatures-aux-scrutins-majoritaire-tour-1-et-proportionnel/20260918-152435/senatoriales-2026-candidatures-listes-scrutin-proportionnel.csv", "sen2026_listes.csv"),
             ("resultats-des-elections-europeennes-du-9-juin-2024/20240613-154909/resultats-definitifs-par-departement.csv", "eur2024_dep.csv"),
             ("elections-europeennes-du-9-juin-2024-candidatures-enregistrees/20240527-082635/candidats-eur-2024.csv", "eur2024_candidats.csv"))]),
        ("senat", "Sénat (data.senat.fr)", "qui siège, groupes, commissions", 1, senat),
        ("pe", "Parlement européen", "groupes et photos des eurodéputés", 30,
         [("https://www.europarl.europa.eu/meps/fr/full-list/xml", RAW / "pe_membres.json", "curl")]),
        ("hatvp", "HATVP", "déclarations d'intérêts (liste, contenu, PDF officiels)", 7,
         [("https://www.hatvp.fr/livraison/opendata/liste.csv", RAW / "hatvp_liste.csv", None),
          ("https://www.hatvp.fr/livraison/merge/declarations.xml", CACHE / "hatvp_declarations.xml", None)]),
    ]


def lignes(path):
    if path.suffix in (".zip", ".xlsx"):  # un classeur xlsx est une archive zip : illisible si tronqué
        return len(zipfile.ZipFile(path).namelist())
    if path.suffix == ".xml":  # analyse complète : un fichier tronqué lève une erreur
        import xml.etree.ElementTree as ET
        return sum(1 for _, e in ET.iterparse(path) if e.tag == "declaration")
    if path.suffix == ".json":
        d = json.load(open(path, encoding="utf-8"))
        return len(d["list"] if isinstance(d, dict) and "list" in d else d)
    # .txt : fichiers électoraux 2021 du ministère, en latin-1
    with open(path, encoding="latin-1" if path.suffix == ".txt" else "utf-8", errors="strict") as f:
        return sum(1 for l in f if not l.startswith("%")) - 1


def telecharger(url, dest, conversion):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if conversion == "curl":  # le site du Parlement européen refuse le client HTTP de Python
        subprocess.run(["curl", "-s", "--max-time", "120", "-o", str(dest), url], check=True)
        return
    for essai in range(3):  # coupures ponctuelles : on réessaie, puis on passe par curl (certains sites refusent urllib)
        try:
            with http(url) as r, open(dest, "wb") as f:
                shutil.copyfileobj(r, f)
            break
        except Exception:
            if essai == 2:
                subprocess.run(["curl", "-sfL", "--retry", "2", "--max-time", "900", "-o", str(dest), url], check=True)
    if conversion == "latin1":
        dest.write_text(dest.read_bytes().decode("latin-1"), encoding="utf-8")


def recuperer(force=False):
    etat = json.load(open(RAW / "sources.json", encoding="utf-8")) if (RAW / "sources.json").exists() else {}
    shutil.rmtree(STAGE, ignore_errors=True)
    a_remplacer, problemes, nouvel_etat = [], [], {}
    for sid, nom, apport, freq, fichiers in sources():
        prev = etat.get(sid, {})
        dates = []  # date de la source = la plus récente modification de ses fichiers
        info = {"nom": nom, "apport": apport, "frequence": freq, "fichiers": {}, "maj": "",
                "verifie": datetime.date.today().isoformat()}
        for url, dest, conv in fichiers:
            lm, taille = entete(url) if conv != "curl" else ("", 0)
            if lm:
                dates.append(datetime.datetime.strptime(lm, "%a, %d %b %Y %H:%M:%S %Z").date().isoformat())
            ancien = prev.get("fichiers", {}).get(dest.name, {})
            # Inchangé : même date de modification et même taille, ou fichier local identique en taille (1re fois).
            inchange = dest.exists() and not force and conv != "curl" and (
                (lm and ancien.get("last_modified") == lm and ancien.get("taille") == taille)
                or (not ancien and taille and dest.stat().st_size == taille))
            if inchange:
                info["fichiers"][dest.name] = {"url": url, "last_modified": lm, "taille": taille,
                                              "lignes": ancien.get("lignes") or lignes(dest)}
                continue
            tmp = STAGE / dest.name
            try:
                telecharger(url, tmp, conv)
                n = lignes(tmp)
            except Exception as e:
                problemes.append(f"{nom} — {dest.name} : illisible ou injoignable ({e})")
                continue
            plancher = max(MINIMUM.get(dest.name, 1), int(0.9 * (ancien.get("lignes") or 0)))
            if n < plancher:
                problemes.append(f"{nom} — {dest.name} : {n} lignes, attendu au moins {plancher}")
                continue
            a_remplacer.append((tmp, dest))
            info["fichiers"][dest.name] = {"url": url, "last_modified": lm, "taille": taille, "lignes": n}
        info["maj"] = max(dates) if dates else ""  # vide : la source ne communique pas sa date de modification
        nouvel_etat[sid] = info
    return a_remplacer, problemes, nouvel_etat


def lancer(script):
    print(f"→ {script}")
    subprocess.run([sys.executable, str(ROOT / script)], check=True, cwd=ROOT)


def controler():
    t = (SITE / "data.js").read_text(encoding="utf-8")
    meta = json.loads(re.search(r"window\.META=(\{.*?\});\n", t, re.S).group(1))
    data = json.loads(re.search(r"window\.DATA=(\[.*\]);", t, re.S).group(1))
    c = meta["counts"]
    deputes = [p for p in data if p["chambre"] == "depute"]
    regles = [  # (libellé, valeur, minimum, maximum)
        ("députés", c.get("depute", 0), 550, 577), ("sénateurs", c.get("senateur", 0), 330, 348),
        ("députés européens", c.get("eurodepute", 0), 75, 81), ("Président", c.get("president", 0), 1, 1),
        ("membres du gouvernement", c.get("gouvernement", 0), 15, 50), ("personnes", c.get("personnes", 0), 450000, 600000),
        ("maires", c.get("maire", 0), 30000, 36000),
        ("% de députés avec leurs votes", round(100 * sum(bool(p.get("votes")) for p in deputes) / max(len(deputes), 1)), 95, 100),
        ("% de députés avec présence en commission", round(100 * sum(bool(p.get("presence_com")) for p in deputes) / max(len(deputes), 1)), 90, 100),
        ("réunions à l'agenda du Parlement", len(json.loads((SITE / "agenda.json").read_text(encoding="utf-8"))) if (SITE / "agenda.json").exists() else 0, 1, 2000),
        ("% de responsables nationaux avec déclaration HATVP lisible", round(100 * sum(bool(p.get("hatvp") or (p.get("interets") or {}).get("pdfs")) for p in data) / max(len(data), 1)), 70, 100),
        ("% de sénateurs avec leur élection", round(100 * sum(bool(p.get("election")) for p in data if p["chambre"] == "senateur") / max(c.get("senateur", 0), 1)), 90, 100),
        ("députés européens avec leur liste", sum(bool(p.get("election")) for p in data if p["chambre"] == "eurodepute"), 75, 81),
        ("% de députés avec leur élection (résultat ou siège obtenu après 2024)", round(100 * sum(bool(p.get("election")) for p in deputes) / max(len(deputes), 1)), 90, 100),
        ("% de responsables nationaux avec photo", round(100 * sum(bool(p.get("photo")) for p in data) / max(len(data), 1)), 90, 100),
    ]
    # une personne ne siège qu'à un endroit : un doublon trahit une source en retard (ex. eurodéputé devenu sénateur)
    vus = collections.Counter((p["nom"].lower(), p["prenom"].lower()) for p in data)
    regles.append(("responsables nationaux présents deux fois", sum(n > 1 for n in vus.values()), 0, 0))
    echecs = [f"{l} : {v} (attendu entre {a} et {b})" for l, v, a, b in regles if not a <= v <= b]
    for l, v, a, b in regles:
        print(f"  {'✓' if a <= v <= b else '✗'} {l} : {v}")
    return echecs


def main():
    if "--check" in sys.argv:
        e = controler()
        sys.exit(1 if e else 0)
    print("1. Récupération et vérification des sources")
    a_remplacer, problemes, etat = recuperer(force="--force" in sys.argv)
    if problemes:
        print("ARRÊT — aucune donnée remplacée :")
        for p in problemes:
            print("  ✗", p)
        sys.exit(1)
    print(f"   {len(a_remplacer)} fichier(s) nouveau(x), le reste est inchangé")
    if not a_remplacer and "--force" not in sys.argv and "--geo" not in sys.argv:
        # passage fréquent (toutes les heures) : sans nouveauté, on ne reconstruit ni ne republie rien
        print("Rien de nouveau : site inchangé.")
        if os.environ.get("GITHUB_OUTPUT"):
            open(os.environ["GITHUB_OUTPUT"], "a").write("nouveau=non\n")
        sys.exit(0)
    if os.environ.get("GITHUB_OUTPUT"):
        open(os.environ["GITHUB_OUTPUT"], "a").write("nouveau=oui\n")
    for tmp, dest in a_remplacer:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp), dest)
    (RAW / "sources.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print("2. Chaîne de construction")
    for s in ["enrich_votes.py", "enrich_activite.py", "enrich_agenda.py", "enrich_hatvp.py", "enrich_elections.py", "enrich_executif.py", "enrich_parlement.py", "enrich_photos.py"] \
            + (["build_geo.py"] if "--geo" in sys.argv else []) + ["build.py"]:
        lancer(s)
    print("3. Contrôles du site produit")
    echecs = controler()
    (SITE / "sources.json").write_text(json.dumps(
        [{"id": k, "nom": v["nom"], "apport": v["apport"], "frequence": v["frequence"], "maj": v["maj"], "verifie": v["verifie"]}
         for k, v in etat.items()], ensure_ascii=False), encoding="utf-8")
    if echecs:
        print("ATTENTION — contrôles en échec, vérifier avant de publier :")
        for e in echecs:
            print("  ✗", e)
        sys.exit(1)
    print("Terminé : données à jour et contrôlées.")


if __name__ == "__main__":
    main()
