#!/usr/bin/env python3
"""Résultats électoraux officiels (Ministère de l'Intérieur, data.gouv.fr), limités aux élus.

Sortie : data/raw/elections.json
  leg : { circonscription "0101" : {tour, inscrits, votants, exprimes, blancs, nuls, elu: [nom, prénom, voix]} }
        législatives des 30 juin et 7 juillet 2024, tour décisif (2nd tour s'il a eu lieu)
  reg : { région : {tour, …, listes: [[libellé, voix, sièges]]} }   régionales (et territoriales) de juin 2021, listes avec sièges
  dep : { canton « 0101 » : {tour, …, elus: binôme élu, voix} }       départementales de juin 2021
  mun : { commune INSEE : {tour, inscrits, votants, exprimes, blancs, nuls, listes: [[libellé, voix, sièges CM, sièges CC]]} }
        municipales des 15 et 22 mars 2026, tour décisif ; seules les listes qui ont obtenu des sièges (des élus)
Jamais : candidats ou listes sans élu (choix éditorial validé), nuances politiques (classement du ministère).
Sources (data/raw/elections/, récupérées par update.py) : résultats définitifs par circonscription (2024, tours 1 et 2),
résultats par commune (2026, tours 1 et 2), régionales par région et départementales par canton (2021, tours 1 et 2)."""
import csv, datetime, html, json, re, unicodedata, zipfile
from pathlib import Path

RAW = Path(__file__).parent / "data" / "raw"
E = RAW / "elections"
N = lambda x: int(float(x)) if re.fullmatch(r"\d+(\.\d+)?", (x or "").strip()) else 0


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def iso_date(x):  # « 1968-11-10 », « 24/01/1966 » ou numéro de série Excel -> AAAA-MM-JJ
    x = (x or "").strip()
    m = re.fullmatch(r"(\d\d)/(\d\d)/(\d{4})", x)
    if m:
        return f"{m[3]}-{m[2]}-{m[1]}"
    if re.fullmatch(r"\d+(\.\d+)?", x):
        return str(datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(x))))
    return x[:10]


def feuilles(path):
    """Classeur xlsx (stdlib) -> {nom de feuille: (en-tête, lignes)} ; cellules absentes = ""."""
    z = zipfile.ZipFile(path)
    ss = [html.unescape(re.sub(r"<[^>]+>", "", x)) for x in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)]
    cible = dict(re.findall(r'<Relationship [^>]*?Id="([^"]+)"[^>]*?Target="([^"]+)"', z.read("xl/_rels/workbook.xml.rels").decode()))
    col = lambda l: sum((ord(c) - 64) * 26 ** i for i, c in enumerate(reversed(l))) - 1
    out = {}
    for nom, rid in re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', z.read("xl/workbook.xml").decode()):
        lignes = []
        for r in re.findall(r"<row[^>]*>(.*?)</row>", z.read("xl/" + cible[rid]).decode(), re.S):
            vals = {}
            for c in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', r, re.S):
                v = re.search(r"<v>([^<]*)</v>", c[3] or "")
                vals[col(c[1])] = (ss[int(v[1])] if 't="s"' in c[2] and v else
                                   html.unescape(re.sub(r"<[^>]+>", "", c[3] or "")) if "inlineStr" in c[2] else (v[1] if v else ""))
            lignes.append([vals.get(i, "") for i in range(max(vals, default=-1) + 1)])
        out[nom] = ([h.strip() for h in lignes[0]], [l + [""] * (len(lignes[0]) - len(l)) for l in lignes[1:]])
    return out


def dep_code(c):  # « 1 » -> « 01 », codes outre-mer du ministère -> INSEE
    c = (c or "").strip()
    return c.zfill(2) if c.isdigit() and len(c) < 2 else DOM.get(c, c)


def senat(annee, elus, t1, t2, listes):
    """Sénatoriales d'une série : pour chaque élu, son résultat (liste au proportionnel, ou personnel au majoritaire).
    elus : [(dép., nom, naissance)] ; t1, t2 : [(en-tête, lignes)] ; listes : {(dép., nom, naissance): libellé}."""
    res = {}
    for tour, feuilles_t in ((1, t1), (2, t2)):
        for h, rows in feuilles_t:
            for x in rows:
                d = dict(zip(h, x))
                if d.get("Code département"):
                    res.setdefault(dep_code(d["Code département"]), []).append((tour, d, list(blocs(h, x, "Voix"))))
    out = {}
    for dep, nom, naiss in elus:
        lib = listes.get((dep, norm(nom), naiss))
        for tour, d, bl in sorted(res.get(dep, []), key=lambda r: -r[0]):  # 2nd tour d'abord
            if lib:
                c = next((c for c in bl if norm(lib) in (norm(c.get("Libellé de liste")), norm(c.get("Libellé abrégé de liste")))), None)
                r = c and {"mode": "liste", "liste": lib, "sieges": N(c.get("Sièges")), "sieges_dep": sum(N(b.get("Sièges")) for b in bl)}
            else:
                c = next((c for c in bl if norm(c.get("Nom candidat")) == norm(nom) and c.get("Elu", "").lower().startswith("élu")), None)
                r = c and {"mode": "majoritaire"}
            if c:
                out[f"{norm(nom)}|{naiss}"] = {"annee": annee, "dep": dep, "tour": tour, **totaux(d), "voix": N(c.get("Voix")), **r}
                break
    return out
BASE = ("Inscrits", "Votants", "Exprimés", "Blancs", "Nuls")


def circo(c):  # codes du ministère -> codes du site (« 201 » -> « 0201 », Français de l'étranger, Saint-Barthélemy/Saint-Martin)
    c = c.strip()
    if c.isdigit() and len(c) < 4:
        return c.zfill(4)
    return "099" + c[2:] if c.startswith("ZZ") else "97701" if c == "ZX01" else c


DOM = {"ZA": "971", "ZB": "972", "ZC": "973", "ZD": "974", "ZM": "976"}  # codes du ministère (2021) -> INSEE


def blocs_fixes(f, premier):
    """Fichiers 2021 (latin-1) : colonnes de base, puis un bloc de colonnes non numérotées par liste ou binôme."""
    r = csv.reader(open(f, encoding="latin-1"), delimiter=";")
    h = next(r)
    i = h.index(premier)
    for x in r:
        d = dict(zip(h[:i], x[:i]))
        yield d, [dict(zip(h[i:], x[j:j + len(h) - i])) for j in range(i, len(x), len(h) - i) if any(x[j:j + len(h) - i])]


def lignes(f):
    r = csv.reader(open(f, encoding="utf-8-sig"), delimiter=";")
    h = next(r)
    for x in r:
        yield h, dict(zip(h, x)), x


def totaux(d):
    return dict(zip(("inscrits", "votants", "exprimes", "blancs", "nuls"), (N(d[k]) for k in BASE)))


def blocs(h, x, cle):  # colonnes répétées « … 1 », « … 2 » : un dict par candidat ou liste
    i = 1
    while f"{cle} {i}" in h:
        d = {k[:-len(str(i)) - 1]: v for k, v in zip(h, x) if k.endswith(f" {i}")}
        if any(d.values()):
            yield d
        i += 1


def main():
    leg = {}
    for tour in (1, 2):  # le 2nd tour écrase le 1er là où il a eu lieu
        for h, d, x in lignes(E / f"leg2024_t{tour}.csv"):
            elu = next((c for c in blocs(h, x, "Voix") if c.get("Elu", "").lower().startswith("élu")), None)
            if elu:
                leg[circo(d["Code circonscription législative"])] = {"tour": tour, **totaux(d),
                                                             "elu": [elu["Nom candidat"], elu["Prénom candidat"], N(elu["Voix"])]}
    reg, dep = {}, {}
    for tour in (1, 2):
        for d, listes in blocs_fixes(E / f"reg2021_t{tour}.txt", "N°Liste"):
            l = sorted(([c["Libellé Etendu Liste"] or c["Libellé Abrégé Liste"], N(c["Voix"]), N(c["Sièges"])] for c in listes if N(c.get("Sièges"))),
                       key=lambda x: -x[2])
            if l:
                reg[d["Code de la région"]] = {"tour": tour, **totaux(d), "listes": l}
        for d, binomes in blocs_fixes(E / f"dep2021_t{tour}.txt", "N°Panneau"):
            elu = next((b for b in binomes if b.get("Siège", "").lower().startswith("elu")), None)
            if elu:
                dep[DOM.get(d["Code du département"], d["Code du département"]) + d["Code du canton"]] = {
                    "tour": tour, **totaux(d), "elus": elu["Binôme"], "voix": N(elu["Voix"])}
    # Sénatoriales : série 1 (septembre 2023, classeur xlsx) et série 2 (septembre 2026, csv).
    f23, l23 = feuilles(E / "sen2023.xlsx"), feuilles(E / "sen2023_listes.xlsx")
    h, rows = f23["Liste des élus"]
    elus23 = [(dep_code(r[h.index("CODE DPT")]), r[h.index("NOM")], iso_date(r[h.index("DATE NAISSANCE")])) for r in rows if r[0]]
    h, rows = l23["Scrutin proportionnel"]
    listes23 = {(dep_code(r[h.index("Code département")]), norm(r[h.index("Nom candidat")]), iso_date(r[h.index("Date de naissance candidat")])):
                r[h.index("Libellé de la liste")] for r in rows}
    sen = senat(2023, elus23, [f23["MAJ - T1"], f23["PROP"]], [f23["MAJ - T2"]], listes23)
    lit = lambda f: (lambda r: (next(r), list(r)))(csv.reader(open(E / f, encoding="utf-8-sig"), delimiter=";"))
    h, rows = lit("sen2026_elus.csv")
    elus26 = [(dep_code(r[h.index("CODDPT")]), r[h.index("NOMPSN")], iso_date(r[h.index("DATNAIPSN")])) for r in rows]
    h, rows = lit("sen2026_listes.csv")
    listes26 = {(dep_code(r[h.index("Code circonscription")]), norm(r[h.index("Nom sur le bulletin de vote")]), iso_date(r[h.index("Date de naissance")])):
                r[h.index("Libellé de la liste")] for r in rows}
    sen.update(senat(2026, elus26, [lit("sen2026_t1.csv")], [lit("sen2026_t2.csv")], listes26))

    # Européennes 2024 : circonscription unique, total national = somme des départements (Français de l'étranger compris).
    h, rows = lit("eur2024_dep.csv")
    tot, listes = dict.fromkeys(("inscrits", "votants", "exprimes", "blancs", "nuls"), 0), {}
    for x in rows:
        for k, v in totaux(dict(zip(h, x))).items():
            tot[k] += v
        for c in blocs(h, x, "Voix"):
            l = listes.setdefault(c["Numéro de panneau"], [c["Libellé de liste"], 0, N(c.get("Sièges"))])
            l[1] += N(c["Voix"])
    eur = {**tot, "listes": sorted(([*l, k] for k, l in listes.items() if l[2]), key=lambda l: -l[2])}
    h, rows = lit("eur2024_candidats.csv")
    avec_sieges = {l[3] for l in eur["listes"]}
    eur["candidats"] = {f"{norm(r[h.index('Nom sur le bulletin de vote')])}|{iso_date(r[h.index('Date de naissance')])}":
                        [r[h.index("Numéro de panneau")], N(r[h.index("Ordre")])] for r in rows if r[h.index("Numéro de panneau")] in avec_sieges}

    mun = {}
    for tour in (1, 2):
        for h, d, x in lignes(E / f"mun2026_t{tour}.csv"):
            listes = [[c.get("Libellé de liste") or c.get("Libellé abrégé de liste") or "", N(c.get("Voix")),
                       N(c.get("Sièges au CM")), N(c.get("Sièges au CC"))] for c in blocs(h, x, "Voix")]
            listes = sorted((l for l in listes if l[2] > 0), key=lambda l: -l[2])
            if listes:
                mun[d["Code commune"]] = {"tour": tour, **totaux(d), "listes": listes}
    assert len(leg) > 550 and len(mun) > 30000 and len(reg) >= 17 and len(dep) > 1900 and len(sen) > 300, (len(leg), len(mun), len(reg), len(dep), len(sen))
    assert sum(l[2] for l in eur["listes"]) == 81, eur["listes"]  # 81 sièges français
    (RAW / "elections.json").write_text(json.dumps({"leg": leg, "mun": mun, "reg": reg, "dep": dep, "sen": sen, "eur": eur},
                                                   ensure_ascii=False), encoding="utf-8")
    print(f"élections : {len(leg)} circonscriptions (législatives 2024), {len(mun)} communes (municipales 2026), "
          f"{len(reg)} régions et {len(dep)} cantons (2021), {len(sen)} sénateurs (2023, 2026), {len(eur['listes'])} listes européennes")


if __name__ == "__main__":
    main()
