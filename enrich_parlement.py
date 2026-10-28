#!/usr/bin/env python3
"""Parlementaires en exercice (sources de chaque chambre) + fiches enrichies + photos.

Sorties :
  data/raw/roster.json     députés (Assemblée nationale, référentiel des acteurs : mandat en cours) et
                           sénateurs (Sénat, data.senat.fr : état ACTIF), avec groupe officiel et début de mandat.
                           Le RNE (Intérieur) retarde sur les changements en cours d'année : au 24/10/2026 il
                           comptait encore 70 sénateurs sortants du renouvellement de septembre 2026 et une
                           dizaine de députés partis. Chaque chambre fait donc foi pour ses propres membres.
  data/raw/parlement.json  par personne (clé « prénom|nom » normalisée) : photo + crédit, lieu de naissance,
                           e-mail professionnel, commissions et organes en cours, page officielle.
  site/photos/*.jpg        photos (source officielle de l'institution, sinon Wikimedia Commons via Wikidata),
                           réduites à 320 px. Les photos restent la propriété de leur auteur : crédit affiché.
Prérequis : data/_cache/acteurs.zip (enrich_votes.py), data/raw/senat/ODSEN_*.csv, data/raw/pe_membres.json
(curl, le site du PE refuse urllib), data/raw/executif.json, data/raw/geo/departements.json."""
import csv, json, re, unicodedata, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from enrich_votes import fetch_zip, norm, aslist, ACTEURS, ROOT
from build_local import reduire

RAW = ROOT / "data" / "raw"
PHOTOS = ROOT / "site" / "photos"
PRENOM, NOM = "Prénom de l'élu", "Nom de l'élu"
UA = {"User-Agent": "Mozilla/5.0 (compatible; Politiscope/0.1; prototype de transparence; contact@politiscope.example)"}
ORGANES = {"COMPER": "Commission permanente", "CNPE": "Commission d'enquête", "CNPS": "Commission spéciale",
           "DELEG": "Délégation", "MISINFO": "Mission d'information", "MISINFOCOM": "Mission d'information",
           "BUREAU": "Bureau de l'Assemblée", "OFFPAR": "Office parlementaire"}
FDE = "Français établis hors de France"


def val(x):
    return x if isinstance(x, str) else None


def http(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def senat_csv(f):
    with open(RAW / "senat" / f, encoding="utf-8") as fh:
        return list(csv.DictReader(l for l in fh if not l.startswith("%")))


def deps_par_nom():
    deps = {norm(d["nom"]): d["code"] for d in json.load(open(RAW / "geo" / "departements.json", encoding="utf-8"))}
    deps[norm(FDE)] = "099"
    return deps


def assemblee(z):
    organes = {}
    for n in z.namelist():
        if "/organe/" in n and n.endswith(".json"):
            o = json.loads(z.read(n))["organe"]
            organes[o["uid"] if isinstance(o["uid"], str) else o["uid"].get("#text")] = (o.get("libelle", ""), val(o.get("libelleAbrev")) or "")
    rne_csp = {}
    with open(RAW / "deputes.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            rne_csp[(r["Date de naissance"], norm(r[PRENOM]))] = r["Libellé de la catégorie socio-professionnelle"]
    deps = {d["code"]: d["nom"] for d in json.load(open(RAW / "geo" / "departements.json", encoding="utf-8"))}
    deps["099"] = FDE
    roster, details = [], {}
    for n in z.namelist():
        if "/acteur/" not in n or not n.endswith(".json"):
            continue
        a = json.loads(z.read(n))["acteur"]
        uid = a["uid"] if isinstance(a["uid"], str) else a["uid"].get("#text")
        i, nais = a["etatCivil"]["ident"], a["etatCivil"].get("infoNaissance") or {}
        ms = aslist(a.get("mandats", {}).get("mandat"))
        k = f"{norm(i['prenom'])}|{norm(i['nom'])}"
        mails = [val(x.get("valElec")) for x in aslist((a.get("adresses") or {}).get("adresse"))
                 if x.get("typeLibelle") == "Mèl" and val(x.get("valElec"))]
        coms = []
        for m in ms:
            if m.get("typeOrgane") in ORGANES and not val(m.get("dateFin")):
                ref = (m.get("organes") or {}).get("organeRef")
                ref = ref[0] if isinstance(ref, list) else ref
                coms.append([organes.get(ref, (ORGANES[m["typeOrgane"]],))[0],
                             val((m.get("infosQualite") or {}).get("libQualite")) or "Membre", val(m.get("dateDebut")) or ""])
        legs = sorted({val(m.get("legislature")) for m in ms if m.get("typeOrgane") == "ASSEMBLEE" and val(m.get("legislature"))}, reverse=True)
        d = {"num": uid[2:], "legs": legs, "lieu_naissance": ", ".join(x for x in (val(nais.get("villeNais")), val(nais.get("depNais"))) if x),
             "email": mails[0] if mails else "", "commissions": coms}
        if k not in details or (details[k]["legs"] or [""])[0] < (legs or [""])[0]:
            details[k] = d  # homonymes : on garde le plus récent à l'Assemblée
        an = next((m for m in ms if m.get("typeOrgane") == "ASSEMBLEE" and val(m.get("legislature")) == "17" and not val(m.get("dateFin"))), None)
        if not an:
            continue
        lieu = (an.get("election") or {}).get("lieu") or {}
        dep = (val(lieu.get("numDepartement")) or "").zfill(2)
        gp = next((m for m in ms if m.get("typeOrgane") == "GP" and not val(m.get("dateFin"))), None)
        gref = (gp or {}).get("organes", {}).get("organeRef") if gp else None
        glib, gabr = organes.get(gref, ("", ""))
        roster.append({"chambre": "depute", "nom": i["nom"], "prenom": i["prenom"], "sexe": "F" if i.get("civ") == "Mme" else "H",
                       "naissance": val(nais.get("dateNais")) or "", "dep": dep, "departement": deps.get(dep, dep),
                       "circo_code": f"{dep}{int(val(lieu.get('numCirco')) or 0):02d}", "debut": val(an.get("mandature", {}).get("datePriseFonction")) or val(an.get("dateDebut")) or "",
                       "profession": rne_csp.get((val(nais.get("dateNais")) or "", norm(i["prenom"])), ""),
                       "groupe": gabr, "groupe_label": glib, "_k": k})
    return roster, details


def senat():
    deps = deps_par_nom()
    groupes = {}
    for r in senat_csv("ODSEN_HISTOGROUPES.csv"):
        if not r["Date de fin d'appartenance"]:
            groupes[r["Matricule"]] = r["Nom court du groupe politique"]
    debut = {}
    for r in senat_csv("ODSEN_ELUSEN.csv"):
        if not r["Date de fin de mandat"]:
            debut[r["Matricule"]] = r["Date de début de mandat"][:10]
    coms = {}
    for r in senat_csv("ODSEN_CUR_COMS.csv"):
        if not r["Fin d'appartenance"]:
            coms.setdefault(r["Matricule"], []).append([r["Nom commission"][:1].upper() + r["Nom commission"][1:],
                                                        r["Fonction"] or "Membre", r["Début d'appartenance"][:10]])
    roster, details = [], {}
    for r in senat_csv("ODSEN_GENERAL.csv"):
        if r["État"] != "ACTIF":
            continue
        k, mat = f"{norm(r['Prénom usuel'])}|{norm(r['Nom usuel'])}", r["Matricule"]
        dep = deps.get(norm(r["Circonscription"]), "")
        roster.append({"chambre": "senateur", "nom": r["Nom usuel"], "prenom": r["Prénom usuel"],
                       "sexe": "F" if r["Qualité"].startswith("Mme") else "H", "naissance": r["Date naissance"][:10],
                       "dep": dep, "departement": r["Circonscription"], "circo_code": "", "debut": debut.get(mat, ""),
                       "profession": r["Description de la profession"] or r["Catégorie professionnelle"],
                       "groupe": r["Groupe politique"], "groupe_label": groupes.get(mat, r["Groupe politique"]), "_k": k})
        base = f"{slug(r['Nom usuel'])}_{slug(r['Prénom usuel'])}{mat.lower()}"
        details[k] = {"commissions": coms.get(mat, []), "email": r["Courrier électronique"] if "@" in r["Courrier électronique"] else "",
                      "page": f"https://www.senat.fr/senateur/{base}.html", "_photo": f"https://www.senat.fr/senimg/{base}_carre.jpg"}
    return roster, details


def wikidata_photo(nom):
    # Dernier recours : Wikimedia Commons (licence libre), seulement pour une fiche décrivant un responsable politique.
    q = urllib.parse.urlencode({"action": "wbsearchentities", "search": nom, "language": "fr", "uselang": "fr",
                                "format": "json", "limit": 3})
    for hit in json.loads(http(f"https://www.wikidata.org/w/api.php?{q}")).get("search", []):
        if not re.search(r"politi|d'état|présiden|ministre|député|sénat|haut fonctionnaire|dirigeant",
                         (hit.get("description") or "").lower()):
            continue
        e = json.loads(http(f"https://www.wikidata.org/wiki/Special:EntityData/{hit['id']}.json"))["entities"][hit["id"]]
        nature = [c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in e.get("claims", {}).get("P31", [])]
        if "Q5" not in nature:
            continue  # pas un être humain (film, événement…) : écarté
        p18 = e.get("claims", {}).get("P18")
        if p18:
            f = p18[0]["mainsnak"]["datavalue"]["value"]
            return f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(f)}?width=400", f"Wikimedia Commons ({f})"
    # Sinon, portrait officiel du gouvernement versé sur Commons (« Portrait officiel de Prénom Nom… »), licence libre.
    q = urllib.parse.urlencode({"action": "query", "list": "search", "srnamespace": 6, "format": "json",
                                "srsearch": f'intitle:"Portrait officiel de {nom}"'})
    for hit in json.loads(http(f"https://commons.wikimedia.org/w/api.php?{q}"))["query"]["search"]:
        f = hit["title"][5:]
        if f.lower().startswith(f"portrait officiel de {nom}".lower()):
            return f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(f)}?width=400", f"Wikimedia Commons ({f})"
    return None


def main():
    PHOTOS.mkdir(parents=True, exist_ok=True)
    z = fetch_zip(ACTEURS, "acteurs.zip")
    dep_roster, an_details = assemblee(z)
    sen_roster, sen_details = senat()
    print(f"en exercice : {len(dep_roster)} députés (Assemblée), {len(sen_roster)} sénateurs (Sénat)")
    (RAW / "roster.json").write_text(json.dumps(dep_roster + sen_roster, ensure_ascii=False, indent=0), encoding="utf-8")

    pe = {norm(m["fullName"]): m["persId"] for m in json.load(open(RAW / "pe_membres.json", encoding="utf-8"))["list"]
          if m.get("countryLabel") == "France"}
    # Eurodéputés : la liste du Parlement européen fait foi (« Prénom NOM » : le nom est en capitales).
    euro = []
    for nom_pe in pe:
        m = next(m for m in json.load(open(RAW / "pe_membres.json", encoding="utf-8"))["list"] if norm(m["fullName"]) == nom_pe)
        mots = m["fullName"].split()
        prenom, nom = " ".join(w for w in mots if not w.isupper()), " ".join(w for w in mots if w.isupper())
        euro.append((f"{norm(prenom)}|{norm(nom)}", m["fullName"]))
    execs = json.load(open(RAW / "executif.json", encoding="utf-8"))

    out, sources = {}, {}
    for x in dep_roster:
        a = an_details[x["_k"]]
        out[x["_k"]] = {"lieu_naissance": a["lieu_naissance"], "email": a["email"], "commissions": a["commissions"],
                        "page": f"https://www.assemblee-nationale.fr/dyn/deputes/PA{a['num']}"}
        sources[x["_k"]] = [(f"https://www.assemblee-nationale.fr/dyn/static/tribun/17/photos/carre/{a['num']}.jpg", "Assemblée nationale")]
    for x in sen_roster:
        s = sen_details[x["_k"]]
        out[x["_k"]] = {k: v for k, v in s.items() if not k.startswith("_")}
        sources[x["_k"]] = [(s["_photo"], "Sénat")]
    for k, nom in euro:
        pid = pe.get(norm(nom)) or pe.get(norm(" ".join(reversed(nom.split(" ", 1)))))
        out[k] = {"page": f"https://www.europarl.europa.eu/meps/fr/{pid}"} if pid else {}
        sources[k] = [(f"https://www.europarl.europa.eu/mepphoto/{pid}.jpg", "Parlement européen")] if pid else []
    for x in execs:
        k = f"{norm(x['prenom'])}|{norm(x['nom'])}"
        a = an_details.get(k)
        out[k] = {"lieu_naissance": a["lieu_naissance"]} if a else {}
        sources[k] = [(f"https://www.assemblee-nationale.fr/dyn/static/tribun/{leg}/photos/carre/{a['num']}.jpg", "Assemblée nationale")
                      for leg in (a["legs"][:3] if a else [])] + [("wikidata", f"{x['prenom']} {x['nom']}")]

    def photo(k):
        f = PHOTOS / (k.replace("|", "-") + ".jpg")
        for url, credit in sources.get(k, []):
            try:
                if url == "wikidata":
                    w = wikidata_photo(credit)
                    if not w:
                        continue
                    url, credit = w
                if not f.exists():
                    data = http(url, binary=True)
                    if len(data) < 2000 or not (data[:3] == b"\xff\xd8\xff" or data[:4] == b"\x89PNG"):
                        continue
                    f.write_bytes(data)
                    reduire(f, f)  # 320 px, JPEG (certaines images Commons sont en PNG)
                out[k].update(photo=f"photos/{f.name}", photo_credit=credit)
                return
            except Exception:
                continue
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(photo, list(sources)))
    (RAW / "parlement.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    groupes = {"depute": dep_roster, "senateur": sen_roster, "eurodepute": [{"_k": k} for k, _ in euro],
               "gouvernement": [{"_k": f"{norm(x['prenom'])}|{norm(x['nom'])}"} for x in execs]}
    print("photos :", {g: f"{sum(bool(out.get(x['_k'], {}).get('photo')) for x in l)}/{len(l)}" for g, l in groupes.items()})


if __name__ == "__main__":
    main()
