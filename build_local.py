#!/usr/bin/env python3
"""Élus locaux (RNE, 9 fichiers) + géographie -> fichiers découpés pour le site.

Appelé par build.py avec la liste des personnes nationales (déjà enrichies). Une personne =
(nom, prénom, date de naissance) : ses mandats de tous les fichiers sont regroupés sur une fiche.

Sorties (site/) :
  c/<commune>.json   fiches complètes des personnes « rattachées » à la commune
  d/<dep>.json       communes du département + liste légère de tous les mandats du département
                     + fiches complètes des élus sans mandat communal (conseillers départementaux…)
  r/<region>.json    conseillers régionaux / membres d'assemblée (liste légère)
  n/<L>.json         annuaire par initiale du nom ; n/index.json : comptes + aperçu par lettre
  communes.json      recherche « me représente » (code, nom, département, codes postaux)
Les fiches nationales restent dans data.js (shard « fr »)."""
import csv, json, re, shutil, unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
GEO = RAW / "geo"
SITE = ROOT / "site"

# Ordre d'importance (le plus petit = mandat principal affiché en tête de fiche).
LEVEL = {"president": 0, "gouvernement": 1, "depute": 2, "senateur": 2, "eurodepute": 3,
         "ma": 4, "cr": 4, "cd": 5, "maire": 6, "adjoint": 7, "cc": 8, "ca": 9, "cm": 9,
         "cfe": 10, "afe": 10}
BASE = {  # libellé (homme, femme) quand le RNE ne donne pas de fonction particulière
    "cm": ("Conseiller municipal", "Conseillère municipale"),
    "cc": ("Conseiller communautaire", "Conseillère communautaire"),
    "cd": ("Conseiller départemental", "Conseillère départementale"),
    "cr": ("Conseiller régional", "Conseillère régionale"),
    "ca": ("Conseiller d'arrondissement", "Conseillère d'arrondissement"),
    "ma": ("Membre de l'assemblée", "Membre de l'assemblée"),
    "cfe": ("Conseiller des Français de l'étranger", "Conseillère des Français de l'étranger"),
    "afe": ("Conseiller à l'Assemblée des Français de l'étranger",
            "Conseillère à l'Assemblée des Français de l'étranger"),
}
# Table 2017 des circonscriptions : codes « Z* » de l'Intérieur -> code département / préfixe INSEE.
ZDEP = {"ZA": "971", "ZB": "972", "ZC": "973", "ZD": "974", "ZM": "976", "ZS": "975",
        "ZX": "977", "ZW": "986", "ZP": "987", "ZN": "988"}
COLL_NOMS = {"69M": "Métropole de Lyon", "94": "Collectivité de Corse", "972": "Collectivité territoriale de Martinique",
             "973": "Collectivité territoriale de Guyane"}
NATIONAUX = {"president", "gouvernement", "depute", "senateur", "eurodepute"}
COM_NOMS = {"975": "Saint-Pierre-et-Miquelon", "977": "Saint-Barthélemy", "978": "Saint-Martin",
            "986": "Wallis-et-Futuna", "987": "Polynésie française", "988": "Nouvelle-Calédonie"}


# Plafonds légaux des indemnités de fonction (brut mensuel), en % de l'indice brut terminal 1027.
# Maires/adjoints < 50 000 hab. : loi n° 2025-1249 du 22/12/2025 (note du préfet des Vosges, mars 2026) ;
# au-delà : CGCT L2123-23 / L2123-24, inchangés. Conseillers départementaux : L3123-16/17.
# shortcut: population municipale INSEE (la loi retient la population totale), sans majorations
# (chef-lieu, station de tourisme…) ni régimes de Paris/Lyon/Marseille ; à affiner commune par commune.
IBT = 4110.52  # indice brut 1027, valeur mensuelle depuis le 01/01/2024
MAIRE = [(500, 28.1), (1000, 44.3), (3500, 55.7), (10000, 58.3), (20000, 67.6), (50000, 90), (100000, 110), (10**9, 145)]
ADJOINT = [(500, 10.89), (1000, 11.77), (3500, 21.38), (10000, 23.32), (20000, 28.6), (50000, 33), (100000, 44),
           (200001, 66), (10**9, 72.5)]
CD = [(250000, 40), (500000, 50), (1000000, 60), (1250000, 65), (10**10, 70)]


def taux(bareme, pop):
    return next(t for seuil, t in bareme if pop < seuil)


def plafond(m, pop_com, pop_dep):
    # m = [type, fonction, lieu code, …]. None quand le barème n'est pas vérifié ou ne s'applique pas.
    t, f = m[0], m[1]
    if t == "maire" and pop_com:
        return round(IBT * taux(MAIRE, pop_com) / 100, 2)
    if t == "adjoint" and pop_com:
        return round(IBT * taux(ADJOINT, pop_com) / 100, 2)
    if t == "cm":
        return round(IBT * 6 / 100, 2)  # L2123-24-1 : 6 % (de droit dès 100 000 hab., sinon si le conseil le vote)
    if t == "cd" and pop_dep:
        base = taux(CD, pop_dep)
        if f.startswith(("Président", "Présidente")):
            return round(IBT * 1.45, 2)
        return round(IBT * base / 100 * (1.4 if "ice-présid" in f else 1), 2)
    if t == "cr" and f.startswith(("Président", "Présidente")):
        return round(IBT * 1.45, 2)
    return None


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def norm_espaces(s):  # comme norm, en gardant espaces et tirets (découpage en mots)
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 -]", "", s.lower())


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def titlecase(s):
    return re.sub(r"[A-Za-zÀ-ÿ]+", lambda m: m.group(0).capitalize(), (s or "").lower())


def read(name, path=RAW):
    with open(path / name, encoding="utf-8-sig") as f:
        sample = f.readline()
        f.seek(0)
        return list(csv.DictReader(f, delimiter=";" if sample.count(";") > sample.count(",") else ","))


def feminise(f, femme):
    if not femme:
        return f
    f = re.sub(r"\b1er\b", "1re", f).replace("Conseiller métropolitain", "Conseillère métropolitaine")
    for a, b in (("Vice-président", "Vice-présidente"), ("Président", "Présidente"),
                 ("adjoint", "adjointe"), ("Conseiller", "Conseillère")):
        f = re.sub(rf"\b{a}\b", b, f)
    return f


def label(t, fonction, femme):
    if fonction:
        return feminise(fonction.replace("au Maire", "au maire").replace("eme ", "e ").replace("ème ", "e "), femme)
    if t == "maire":
        return "Maire"
    return BASE[t][1 if femme else 0]


def pad_dep(code):
    code = (code or "").strip()
    return code.zfill(2) if code.isdigit() and len(code) < 2 else code


def dep_of_commune(code):
    return code[:3] if code[:2] in ("97", "98") else code[:2]


# ---------- géographie ----------

def geographie():
    deps = {d["code"]: {"code": d["code"], "nom": d["nom"], "region": d["codeRegion"]}
            for d in json.load(open(GEO / "departements.json", encoding="utf-8"))}
    regions = {r["code"]: r["nom"] for r in json.load(open(GEO / "regions.json", encoding="utf-8"))}
    for code, nom in COM_NOMS.items():
        deps[code] = {"code": code, "nom": nom, "region": "COM"}
    deps["099"] = {"code": "099", "nom": "Français établis hors de France", "region": ""}
    regions["COM"] = "Collectivités d'outre-mer"

    canton = {r["COM"]: r["CAN"] for r in read("cog_communes.csv", GEO) if r["TYPECOM"] == "COM"}
    circos = {}
    for dep, com, circ in xlsx_rows(GEO / "circo_2017.xlsx", ("CODE DPT", "CODE COMMUNE", "CODE CIRC LEGISLATIVE")):
        d = ZDEP.get(dep, pad_dep(dep))  # la table écrit « 1 » pour l'Ain
        insee = (d[:2] if d in ZDEP.values() else d) + com.zfill(3)
        circos.setdefault(insee, set()).add(f"{d}{int(circ):02d}")
    # Table de 2017 : les communes nouvelles créées depuis héritent des circonscriptions de leurs
    # anciennes communes (événements du COG, dans l'ordre chronologique).
    for e in sorted(read("cog_mvt.csv", GEO), key=lambda e: e["DATE_EFF"]):
        if e["DATE_EFF"] >= "2017" and e["COM_AV"] in circos and e["COM_AV"] != e["COM_AP"]:
            circos.setdefault(e["COM_AP"], set()).update(circos[e["COM_AV"]])
    communes = {}
    for c in json.load(open(GEO / "communes.json", encoding="utf-8")):
        communes[c["code"]] = {
            "code": c["code"], "nom": c["nom"], "dep": c["codeDepartement"],
            "pop": c.get("population") or 0, "cp": c.get("codesPostaux") or [],
            "canton": canton.get(c["code"], ""), "circos": sorted(circos.get(c["code"], [])),
            "epci": c.get("codeEpci") or ""}
    return deps, regions, communes


def reduire(src, dest, taille=320):
    """Photo -> JPEG de 320 px au plus. macOS : sips ; ailleurs (serveur de mise à jour Linux) : Pillow."""
    import shutil as sh, subprocess
    if sh.which("sips"):
        subprocess.run(["sips", "-s", "format", "jpeg", "-Z", str(taille), str(src), "--out", str(dest)], capture_output=True, check=True)
        return
    from PIL import Image
    im = Image.open(src)
    im.thumbnail((taille, taille))
    im.convert("RGB").save(dest, "JPEG", quality=85)


def xlsx_rows(path, cols):
    # Lecteur xlsx minimal (stdlib) : la table de l'Intérieur n'existe qu'en xlsx.
    import zipfile
    z = zipfile.ZipFile(path)
    ss = re.findall(r"<t[^>]*>([^<]*)</t>", z.read("xl/sharedStrings.xml").decode())
    rows = []
    for r in re.findall(r"<row[^>]*>(.*?)</row>", z.read("xl/worksheets/sheet1.xml").decode()):
        vals = {}
        for c in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*)>(?:<v>([^<]*)</v>)?', r):
            v = c.group(3)
            vals[c.group(1)] = ss[int(v)] if 't="s"' in c.group(2) and v else (v or "")
        rows.append(vals)
    head = {v: k for k, v in rows[0].items()}
    return [tuple(r.get(head[c], "") for c in cols) for r in rows[1:]]


# ---------- personnes et mandats ----------

class Personnes:
    def __init__(self):
        self.by_key = {}

    def get(self, nom, prenom, dob, sexe, prof):
        k = (norm(nom), norm(prenom), dob)
        p = self.by_key.get(k)
        if p is None:
            p = self.by_key[k] = {"nom": titlecase(nom), "prenom": titlecase(prenom), "sexe": sexe,
                                  "naissance": dob, "profession": prof, "m": []}
        return p

    def add(self, row, t, lc, lieu, dep, fonction="", debut_f=""):
        femme = row.get("Code sexe") == "F"
        p = self.get(row["Nom de l'élu"], row["Prénom de l'élu"], row.get("Date de naissance", ""),
                     "F" if femme else "H", row.get("Libellé de la catégorie socio-professionnelle", ""))
        if t == "cm" and fonction == "Maire":
            t = "maire"
        elif t == "cm" and "adjoint" in fonction.lower():
            t = "adjoint"
        p["m"].append([t, label(t, fonction, femme), lc, lieu, dep,
                       row.get("Date de début du mandat", ""), debut_f])


def lire_mandats(deps):
    P = Personnes()
    for r in read("conseillers_municipaux.csv"):
        dep = r["Code du département"] or r["Code de la collectivité à statut particulier"]
        P.add(r, "cm", r["Code de la commune"], r["Libellé de la commune"], dep,
              r["Libellé de la fonction"], r["Date de début de la fonction"])
    for r in read("conseillers_communautaires.csv"):
        dep = r["Code du département"] or r["Code de la collectivité à statut particulier"]
        P.add(r, "cc", r["Code de la commune de rattachement"], titlecase(r["Libellé de l'EPCI"]), dep,
              r["Libellé de la fonction"], r["Date de début de la fonction"])
        P.by_key[(norm(r["Nom de l'élu"]), norm(r["Prénom de l'élu"]), r["Date de naissance"])]["m"][-1].append(r["N° SIREN"])
    for r in read("conseillers_arrondissement.csv"):
        P.add(r, "ca", r["Code de la commune"], r["Libellé du secteur"], r["Code du département"],
              r["Libellé de la fonction"], r["Date de début de la fonction"])
    for r in read("conseillers_departementaux.csv"):
        P.add(r, "cd", r["Code du canton"], titlecase(r["Libellé du canton"]), r["Code du département"],
              r["Libellé de la fonction"], r["Date de début de la fonction"])
    for r in read("conseillers_regionaux.csv"):
        P.add(r, "cr", r["Code de la région"], titlecase(r["Libellé de la région"]),
              pad_dep(r["Code de la section départementale"]),
              r["Libellé de la fonction"], r["Date de début de la fonction"])
    for r in read("membres_assemblee.csv"):
        coll = r["Code de la collectivité à statut particulier"]
        dep = ("69" if coll == "69M" else pad_dep(r["Code de la section - collectivité à statut particulier"])
               if coll == "94" else coll if coll else r["Code du département"])
        if coll == "94" and dep not in ("2A", "2B"):
            dep = "2A"  # shortcut: section corse non renseignée -> Corse-du-Sud ; à affiner si besoin
        lieu = COLL_NOMS.get(coll) or titlecase(r["Libellé de la collectivité à statut particulier"]) or titlecase(r["Libellé de la région"])
        f = "" if r["Libellé de la fonction"] in ("", "Autre membre") else r["Libellé de la fonction"]
        f = f or ("Conseiller métropolitain" if coll == "69M" else "")
        P.add(r, "ma", coll or r["Code de la région"], lieu, dep, f, r["Date de début de la fonction"])
    for r in read("conseillers_fde.csv"):
        P.add(r, "cfe", r["Code de la circonscription consulaire"], r["Libellé de la circonscription consulaire"],
              "etr", r["Libellé de la fonction"], r["Date de début de la fonction"])
    for r in read("afe.csv"):
        P.add(r, "afe", r["Code de la circ. AFE"], r["Libellé la circ. AFE"], "etr",
              r["Libellé de la fonction"], r["Date de début de la fonction"])
    return P


def mandat_national(p, deps):
    # Fiche nationale -> même forme de mandat que les fiches locales (noms officiels, pas la casse du RNE).
    lc = p.get("circo_code") or p.get("dep") or ""
    dep_nom = deps.get(p.get("dep") or "", {}).get("nom") or p.get("departement", "")
    if p.get("circo_code"):
        n = int(p["circo_code"][-2:])
        lieu = f"{n}{'re' if n == 1 else 'e'} circonscription · {dep_nom}"
    else:
        lieu = dep_nom or {"president": "République française", "gouvernement": "Gouvernement",
                           "eurodepute": "Parlement européen"}.get(p["chambre"], "")
    return [p["chambre"], p.get("titre") or p["fonction"], lc, lieu, p.get("dep") or "fr", p.get("debut", ""), ""]


# ---------- assemblage ----------

def build(national, meta):
    deps, regions, communes = geographie()
    P = lire_mandats(deps)

    # 1. Nationaux : on rattache leurs mandats locaux à leur fiche nationale (shard « fr »).
    nat_keys = {}
    for p in national:
        k = (norm(p["nom"]), norm(p["prenom"]), p.get("naissance", ""))
        loc = P.by_key.pop(k, None)
        p["m"] = [mandat_national(p, deps)] + (loc["m"] if loc else [])
        p["shard"] = "fr"
        nat_keys[k] = p
    locaux = list(P.by_key.values())
    print(f"{len(locaux)} personnes avec seulement des mandats locaux ;",
          sum(len(p["m"]) > 1 for p in national), "nationaux avec aussi un mandat local")

    # 2. Shard et slug de chaque personne locale.
    COMMUNAL = ("maire", "adjoint", "cm", "ca", "cc")
    for p in locaux:
        p["m"].sort(key=lambda m: LEVEL[m[0]])
        com = next((m for m in sorted(p["m"], key=lambda m: LEVEL[m[0]]) if m[0] in COMMUNAL and m[0] != "cc"), None) \
            or next((m for m in p["m"] if m[0] == "cc"), None)
        p["shard"] = com[2] if com else ("etr" if p["m"][0][4] == "etr" else "d" + p["m"][0][4])
    for p in national:
        p["m"].sort(key=lambda m: LEVEL[m[0]])
    by_shard = {}
    for p in locaux:
        by_shard.setdefault(p["shard"], []).append(p)
    for lst in by_shard.values():
        seen = {}
        for p in sorted(lst, key=lambda x: (x["nom"], x["prenom"], x["naissance"])):
            base = slugify(f"{p['prenom']}-{p['nom']}") or "elu"
            n = seen[base] = seen.get(base, 0) + 1
            p["slug"] = base if n == 1 else f"{base}-{n}"
    everyone = national + locaux

    # 3. Communes absentes de geo.api (collectivités d'outre-mer) : reconstituées depuis le RNE.
    for p in locaux:
        for m in p["m"]:
            if m[0] in ("maire", "adjoint", "cm") and m[2] not in communes:
                communes[m[2]] = {"code": m[2], "nom": m[3], "dep": m[4], "pop": 0, "cp": [],
                                  "canton": "", "circos": [], "epci": ""}

    # Nom officiel des communes (INSEE) plutôt que celui du RNE (« Chéry-Lès-Rozoy » -> « Chéry-lès-Rozoy »).
    for p in everyone:
        for m in p["m"]:
            if m[0] in ("maire", "adjoint", "cm") and m[2] in communes:
                m[3] = communes[m[2]]["nom"]

    # Plafonds légaux d'indemnité, alignés sur la liste des mandats (None = barème non vérifié / sans objet).
    pop_dep = {}
    for c in communes.values():
        pop_dep[c["dep"]] = pop_dep.get(c["dep"], 0) + c["pop"]
    for p in everyone:
        p["ind"] = [None if m[0] in NATIONAUX else
                    plafond(m, communes.get(m[2], {}).get("pop", 0), pop_dep.get(m[4], 0)) for m in p["m"]]

    # Déclarations d'intérêts HATVP (enrich_hatvp.py) : contenu dans site/h/<id>.json ; les PDF restent sur hatvp.fr (lien direct).
    hv = json.loads((RAW / "hatvp_contenu.json").read_text(encoding="utf-8")) if (RAW / "hatvp_contenu.json").exists() else {}
    fiches_h, par_nom = {}, {}
    for k, l in hv.items():
        par_nom.setdefault(k.split("|")[0], []).append(l)
    # un mot du prénom en commun, sur ses 3 premières lettres (« Marie-Do » / « Marie-Dominique », « Martens Carlos »)
    mots = lambda x: {w[:3] for w in re.split(r"[\s-]+", norm_espaces(x)) if w}
    for p in everyone:
        meme = lambda e: mots(e["p"]) & mots(p["prenom"])
        if p.get("naissance"):
            l = [e for e in hv.get(f"{norm(p['nom'])}|{p['naissance']}", []) if meme(e)]
        else:  # date de naissance inconnue (certains membres du gouvernement) : nom + prénom, sans ambiguïté
            c = [l for l in par_nom.get(norm(p["nom"]), []) if meme(l[0])]
            l = c[0] if len(c) == 1 else []
        if l:
            p["hatvp"] = f"{norm(p['nom'])}-{p.get('naissance') or norm(p['prenom'])}"
            fiches_h[p["hatvp"]] = l
    shutil.rmtree(SITE / "h", ignore_errors=True)
    (SITE / "h").mkdir(parents=True)
    for hid, l in fiches_h.items():
        (SITE / "h" / f"{hid}.json").write_text(json.dumps(l, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"HATVP : {len(fiches_h)} fiches avec déclaration d'intérêts ({sum(p['shard'] == 'fr' for p in everyone if p.get('hatvp'))} nationaux)")

    # Photos des élus locaux (enrich_photos.py, Wikimedia Commons) -> site/photos/l/.
    ph = json.loads((RAW / "photos_locales.json").read_text(encoding="utf-8")) if (RAW / "photos_locales.json").exists() else {}
    off = json.loads((RAW / "photos_officielles.json").read_text(encoding="utf-8")) if (RAW / "photos_officielles.json").exists() else {}
    shutil.rmtree(SITE / "photos" / "l", ignore_errors=True)
    (SITE / "photos" / "l").mkdir(parents=True)
    for p in locaux:
        k = f"{norm(p['nom'])}|{norm(p['prenom'])}|{p['naissance']}"
        # 1. licence libre (Commons) ; 2. portrait du site officiel de la collectivité, relu à la main (photos_officielles.py)
        for dossier, x in (("photos_locales", ph.get(k)), ("photos_officielles", off.get(k))):
            if x and (RAW / dossier / x["photo"]).exists():
                shutil.copy(RAW / dossier / x["photo"], SITE / "photos" / "l" / x["photo"])
                p["photo"], p["photo_credit"], p["photo_source"] = f"photos/l/{x['photo']}", x["credit"], x["source"]
                break
    print("élus locaux avec photo :", sum(bool(p.get("photo")) for p in locaux))

    # 4. Écriture.
    for d in ("c", "d", "r", "n"):
        shutil.rmtree(SITE / d, ignore_errors=True)
        (SITE / d).mkdir(parents=True)
    light = lambda p, m: [p["shard"], p["slug"], p["nom"], p["prenom"], p["sexe"], m[0], m[1], m[2]] + (
        [p["photo"]] if p["shard"] != "fr" and p.get("photo") else [])  # vignette des élus locaux (nationaux : data.js)

    par_dep, par_reg = {}, {}
    for p in everyone:
        for m in p["m"]:
            if m[0] == "cr" or (m[0] == "ma" and m[2] != "69M"):  # Métropole de Lyon : élus métropolitains
                par_reg.setdefault(deps.get(m[4], {}).get("region") or m[2], []).append(light(p, m))
            if m[4] and m[4] not in ("fr", "etr"):
                par_dep.setdefault(m[4], []).append(light(p, m))
            elif m[0] in ("cfe", "afe"):
                par_dep.setdefault("etr", []).append(light(p, m))

    for code, lst in by_shard.items():
        if code.startswith("d") or code == "etr":
            continue
        (SITE / "c" / f"{code}.json").write_text(json.dumps(lst, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    full_dep = {code[1:]: lst for code, lst in by_shard.items() if code.startswith("d")}
    full_dep["etr"] = by_shard.get("etr", [])

    epcis = {}
    for p in everyone:
        for m in p["m"]:
            if m[0] == "cc" and len(m) > 7:
                epcis[m[7]] = m[3]
    cantons = {}
    for p in everyone:
        for m in p["m"]:
            if m[0] == "cd":
                cantons.setdefault(m[4], {})[m[2]] = m[3]
    # Municipales 2026 (enrich_elections.py) : participation et listes ayant obtenu des sièges, par commune.
    elec = json.loads((RAW / "elections.json").read_text(encoding="utf-8")) if (RAW / "elections.json").exists() else {}
    mun, dep21 = elec.get("mun", {}), elec.get("dep", {})
    # Départementales 2021 : seuls les conseillers EN PLACE issus du binôme élu sont cités (par leur slug) ; les noms du
    # binôme ne sont pas publiés (l'un des deux a pu quitter ses fonctions depuis).
    en_place = {}
    for p in everyone:
        for m in p["m"]:
            if m[0] == "cd" and m[2] in dep21 and norm(p["nom"]) in norm(dep21[m[2]]["elus"]):
                en_place.setdefault(m[2], []).append(f"{p['shard']}/{p['slug']}")
    dep21 = {k: {**{c: v for c, v in r.items() if c != "elus"}, "en_place": en_place.get(k, [])} for k, r in dep21.items()}
    deps_out = {}
    for code in sorted(set(par_dep) | set(deps)):
        info = deps.get(code, {"code": code, "nom": "Français de l'étranger" if code == "etr" else code, "region": ""})
        coms = sorted((c for c in communes.values() if c["dep"] == code), key=lambda c: norm(c["nom"]))
        ep = {c["epci"] for c in coms}
        data = {**info,
                "communes": [[c["code"], c["nom"], c["pop"], " ".join(c["cp"]), c["canton"], c["circos"], c["epci"],
                              [plafond(["maire", ""], c["pop"], 0), plafond(["adjoint", ""], c["pop"], 0)]] for c in coms],
                "epcis": {k: v for k, v in epcis.items() if k in ep},
                # nom des cantons : les communes partagées (pseudo-cantons 8x/9x) s'y retrouvent par nom
                "cantons": cantons.get(code, {}),
                "municipales": {c["code"]: mun[c["code"]] for c in coms if c["code"] in mun},
                "departementales": {k: dep21[k] for k in cantons.get(code, {}) if k in dep21},  # juin 2021, binôme élu
                "elus": par_dep.get(code, []), "fiches": full_dep.get(code, [])}
        (SITE / "d" / f"{code}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        deps_out[code] = {"nom": info["nom"], "region": info["region"], "communes": len(coms),
                          "elus": len({(e[0], e[1]) for e in par_dep.get(code, [])})}

    for code, lst in par_reg.items():
        (SITE / "r" / f"{code}.json").write_text(json.dumps(
            {"code": code, "nom": regions.get(code, code), "elus": lst,
             "regionales": elec.get("reg", {}).get(code)}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Annuaire par initiale : [shard, slug, nom, prénom, fonction principale, lieu, niveau].
    lettres = {}
    for p in everyone:
        m = p["m"][0]
        L = (norm(p["nom"])[:1] or "#").upper()
        L = L if L.isalpha() else "#"
        lettres.setdefault(L, []).append([p["shard"], p["slug"], p["nom"], p["prenom"], m[1], m[3], LEVEL[m[0]]]
                                         + ([p["photo"]] if p["shard"] != "fr" and p.get("photo") else []))
    index = {}
    for L, lst in sorted(lettres.items()):
        lst.sort(key=lambda e: (norm(e[2]), norm(e[3])))
        (SITE / "n" / f"{L}.json").write_text(json.dumps(lst, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        index[L] = [len(lst), sorted(lst, key=lambda e: (e[6], norm(e[2]), norm(e[3])))[:10]]
    (SITE / "n" / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    (SITE / "communes.json").write_text(json.dumps(
        [[c["code"], c["nom"], c["dep"], " ".join(c["cp"])] for c in sorted(communes.values(), key=lambda c: -c["pop"])],
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Contrôles de cohérence des jointures (affichés au build).
    cd_codes = {m[2] for p in everyone for m in p["m"] if m[0] == "cd"}
    dep_circos = {p.get("circo_code") for p in national if p["chambre"] == "depute"}
    coms_metro = [c for c in communes.values() if c["dep"] in deps and deps[c["dep"]]["region"] != "COM"]
    print("communes avec canton reconnu :", sum(c["canton"] in cd_codes for c in coms_metro), "/", len(coms_metro))
    print("communes avec circonscription reconnue :", sum(any(x in dep_circos for x in c["circos"]) for c in coms_metro), "/", len(coms_metro))
    print("intercommunalités nommées :", len(epcis))

    counts = {}
    for p in everyone:
        for t in {m[0] for m in p["m"]}:
            counts[t] = counts.get(t, 0) + 1
    meta["counts"].update({k: v for k, v in counts.items() if k not in meta["counts"]})
    meta["counts"]["personnes"] = len(everyone)
    meta["regions"] = {k: v for k, v in regions.items()}
    meta["deps"] = deps_out
    return everyone
