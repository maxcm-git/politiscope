#!/usr/bin/env python3
"""Portraits publiés par les sites officiels des collectivités, pour les élus de premier plan sans photo libre
(présidences de département ou de collectivité, maires des villes de 50 000 habitants et plus).

À lancer à la main (pas dans update.py) : `python3 photos_officielles.py cibles.json`, où cibles.json liste
{type: "dep"|"maire", code, lieu, prenom, nom, naissance, cle}. Pour chacun : adresses officielles probables
(ville-x.fr, x.fr, departementNN.fr…), puis les pages dont l'adresse évoque le maire, la présidence ou les élus.
Seule une image dont le texte alternatif, le titre ou le nom de fichier contient le nom de la personne est retenue.
Ces photos ne sont pas sous licence libre : crédit « © site » et lien vers la page source (choix validé par Max).

Sorties : data/raw/photos_officielles/<id>.jpg et data/raw/photos_officielles.json
  { "nom|prénom|naissance" : {"photo", "credit", "source"} }, complété à chaque passage (les trouvailles sont gardées)."""
import json, re, ssl, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from build_local import norm, reduire

RAW = Path(__file__).parent / "data" / "raw"
OUT = RAW / "photos_officielles"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Politiscope-prototype/0.1 (contact@politiscope.example)"}
PAGES = re.compile(r"maire|presid|elus?\b|elu-|conseil-municipal|conseil-departemental|equipe|majorit|institution", re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.liens, self.images = [], []

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "a" and a.get("href"):
            self.liens.append(a["href"])
        if tag == "img":
            src = a.get("data-src") or a.get("data-lazy-src") or a.get("src") or ""
            srcset = (a.get("srcset") or a.get("data-srcset") or "").split(",")
            plus_grande = srcset[-1].strip().split(" ")[0] if srcset[-1].strip() else ""
            self.images.append((plus_grande or src, " ".join(a.get(k) or "" for k in ("alt", "title"))))
        if tag == "meta" and a.get("property") == "og:image" and a.get("content"):
            self.images.append((a["content"], "og:image"))


def lire(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15, context=ssl.create_default_context())
        if "html" not in (r.headers.get("Content-Type") or ""):
            return None, url
        return r.read(2_000_000).decode("utf-8", "ignore"), r.geturl()
    except Exception:
        return None, url


def slug(s, sep="-"):
    return re.sub(r"[^a-z0-9]+", sep, norm_espace(s)).strip(sep)


def norm_espace(s):
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace("'", " ")


ANNUAIRE = "https://api-lannuaire.service-public.fr/api/explore/v2.1/catalog/datasets/api-lannuaire-administration/records"


def annuaire(c):
    """Site internet déclaré dans l'Annuaire de l'administration (service-public.fr) : mairie (code INSEE) ou conseil départemental."""
    where = (f'code_insee_commune="{c["code"]}" and nom like "Mairie - *"' if c["type"] == "maire"
             else f'nom like "Conseil départemental - {c["lieu"]}"')
    q = urllib.parse.urlencode({"where": where, "limit": 5, "select": "nom,site_internet"})
    try:
        rep = json.loads(urllib.request.urlopen(urllib.request.Request(f"{ANNUAIRE}?{q}", headers=UA), timeout=20).read())
    except Exception:
        return []
    nom = "Mairie - " if c["type"] == "maire" else f"Conseil départemental - {c['lieu']}"
    return [s["valeur"] for r in rep["results"] if r["nom"].startswith(nom) and (c["type"] == "maire" or r["nom"] == nom)
            for s in json.loads(r.get("site_internet") or "[]") if s.get("valeur")]


def adresses(c):
    s, s2 = slug(c["lieu"]), slug(c["lieu"], "")
    if c["type"] == "maire":
        bases = [f"ville-{s}", s, f"mairie-{s}", s2, f"ville{s2}", f"mairie{s2}"]
    else:
        bases = [s, s2, f"departement{c['code']}", f"departement-{s}", f"le{s2}", f"cd{c['code']}"]
    return annuaire(c) + [f"https://www.{b}.fr/" for b in bases]


def chercher(c):
    cible = norm(c["nom"])
    for depart in adresses(c):
        html, base = lire(depart)
        if not html:
            continue
        a_voir, vus = [base], set()
        p0 = Page(); p0.feed(html)
        dom = urllib.parse.urlparse(base).netloc
        for h in p0.liens:
            u = urllib.parse.urljoin(base, h).split("#")[0]
            if urllib.parse.urlparse(u).netloc == dom and PAGES.search(urllib.parse.urlparse(u).path) and u not in a_voir:
                a_voir.append(u)
        for u in a_voir[:14]:
            page_html = html if u == base else lire(u)[0]
            if not page_html or u in vus:
                continue
            vus.add(u)
            p = Page(); p.feed(page_html)
            for src, texte in p.images:
                fichier = urllib.parse.unquote(src.rsplit("/", 1)[-1])
                if cible and (cible in norm(texte) or cible in norm(fichier)) and not re.search(r"\.svg|logo|signature", src, re.I):
                    return {"image": urllib.parse.urljoin(u, src), "page": u, "site": dom}
        return {"site": dom}  # site trouvé, portrait non repéré
    return {}


def main():
    cibles = json.load(open(sys.argv[1], encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    res_f = RAW / "photos_officielles.json"
    res = json.loads(res_f.read_text(encoding="utf-8")) if res_f.exists() else {}
    rej_f = RAW / "photos_officielles_rejets.json"  # images écartées à la relecture : pas de nouvel essai automatique
    rejets = json.loads(rej_f.read_text(encoding="utf-8")) if rej_f.exists() else {}
    a_faire = [c for c in cibles if f"{norm(c['nom'])}|{norm(c['prenom'])}|{c['naissance']}" not in res | rejets.keys()]
    with ThreadPoolExecutor(12) as ex:
        trouves = list(ex.map(chercher, a_faire))
    rapport = []
    for c, t in zip(a_faire, trouves):
        k = f"{norm(c['nom'])}|{norm(c['prenom'])}|{c['naissance']}"
        if "image" not in t:
            rapport.append((c["lieu"], c["prenom"], c["nom"], t.get("site", "site non trouvé")))
            continue
        dest = OUT / (re.sub(r"[^a-z0-9]+", "-", k) + ".jpg")
        try:
            brut = dest.with_suffix(".src")
            url = urllib.parse.quote(t["image"], safe=":/?=&%#+,;@")  # adresses avec accents
            brut.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read())
            reduire(brut, dest)
            brut.unlink()
        except Exception as e:
            rapport.append((c["lieu"], c["prenom"], c["nom"], f"image illisible ({e.__class__.__name__})"))
            continue
        res[k] = {"photo": dest.name, "credit": f"© {t['site']}", "source": t["page"], "cle": c["cle"]}
    res_f.write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"portraits officiels : {len(res)} au total ; restent {len(rapport)} :")
    for r in rapport:
        print("  ", *r)


if __name__ == "__main__":
    main()
