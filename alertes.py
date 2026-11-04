#!/usr/bin/env python3
"""Alertes par e-mail : une fois par jour au plus, chaque personne qui l'a demandé (case « Me prévenir par e-mail »
sur « Mes élus ») reçoit un résumé de ce qui a changé pour les élus qu'elle suit : nouvelle fonction ou fin d'une
fonction, nouveaux scrutins à l'Assemblée, nouvelle déclaration HATVP, élu qui n'est plus en fonction.

Lancé par le workflow après update.py, sur le site construit (site/). Inactif tant que ces réglages manquent :
  ALERTES_JETON       jeton créé par supabase.sql (secret GitHub) : seule clé qui ouvre la liste des destinataires
  BREVO_CLE           clé d'API Brevo (secret GitHub), pour l'envoi
  ALERTES_EXPEDITEUR  adresse d'expédition validée dans Brevo (variable GitHub)
État : data/raw/alertes_etat.json = ce que contenait chaque fiche suivie lors du dernier envoi.
Essai sans rien envoyer : python3 alertes.py --essai fr/<slug> [d75/<slug> …] (montre l'e-mail d'un suivi fictif)."""
import collections, html, json, os, re, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
SITE, ETAT = ROOT / "site", ROOT / "data" / "raw" / "alertes_etat.json"
ADRESSE = "https://maxcm-git.github.io/politiscope/"
JOUR = 20 * 3600  # un envoi par jour au plus (marge pour l'heure du passage)


def fiches(ids):
    """Fiche actuelle de chaque élu suivi (None s'il n'est plus en fonction)."""
    s = (SITE / "data.js").read_text(encoding="utf-8")
    nat = {p["slug"]: p for p in json.JSONDecoder().raw_decode(s, s.index("window.DATA=") + 12)[0]}
    out, lus = {}, {}
    for i in ids:
        shard, slug = i.split("/", 1)
        if shard == "fr":
            out[i] = nat.get(slug)
            continue
        f = SITE / ("d/etr.json" if shard == "etr" else f"d/{shard[1:]}.json" if shard.startswith("d") else f"c/{shard}.json")
        if f not in lus:
            d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
            lus[f] = {p["slug"]: p for p in (d if isinstance(d, list) else d["fiches"])}
        out[i] = lus[f].get(slug)
    return out


def signature(p):
    return {"nom": f"{p['prenom']} {p['nom']}", "m": [[m[1], m[3]] for m in p["m"]],
            "scrutins": (p.get("votes") or {}).get("scrutins"), "hatvp": (p.get("interets") or {}).get("derniere")}


def changements(avant, apres):
    """Phrases décrivant ce qui a changé entre deux signatures (apres = None : plus en fonction)."""
    if apres is None:
        return ["n'apparaît plus parmi les élus en fonction"]
    l = [f"nouvelle fonction : {f} ({lieu})" for f, lieu in apres["m"] if [f, lieu] not in avant["m"]]
    l += [f"n'exerce plus : {f} ({lieu})" for f, lieu in avant["m"] if [f, lieu] not in apres["m"]]
    n = (apres["scrutins"] or 0) - (avant["scrutins"] or 0)
    if n > 0:
        l.append(f"a voté lors de {n} nouveau{'x' if n > 1 else ''} scrutin{'s' if n > 1 else ''} à l'Assemblée")
    if apres["hatvp"] and apres["hatvp"] != avant["hatvp"]:
        a, m, j = apres["hatvp"].split("-")
        l.append(f"nouvelle déclaration d'intérêts publiée par la HATVP le {j}/{m}/{a}")
    return l


def courriel(par_elu):
    """Sujet, texte et HTML d'un résumé : {id: (nom, [phrases])}."""
    n = len(par_elu)
    sujet = f"Politiscope : du nouveau pour {next(iter(par_elu.values()))[0]}" if n == 1 else f"Politiscope : du nouveau pour {n} élus que vous suivez"
    texte = "\n\n".join(f"{nom}\n" + "\n".join(f"- {x}" for x in l) + f"\n{ADRESSE}#/p/{i}" for i, (nom, l) in par_elu.items())
    pied = f"Vous recevez ce message parce que vous avez demandé ces alertes sur Politiscope. Pour les arrêter : {ADRESSE}#/suivis"
    corps = "".join(f'<h3 style="margin:18px 0 4px"><a href="{ADRESSE}#/p/{html.escape(i)}">{html.escape(nom)}</a></h3><ul>'
                    + "".join(f"<li>{html.escape(x)}</li>" for x in l) + "</ul>" for i, (nom, l) in par_elu.items())
    return sujet, f"{texte}\n\n{pied}", (f'<div style="font-family:sans-serif;max-width:560px">{corps}<p style="color:#666;font-size:13px">'
                                         f'{html.escape(pied.split(" : ")[0])} : <a href="{ADRESSE}#/suivis">Mes élus</a>.</p></div>')


def destinataires(jeton):
    """[(e-mail, id suivi)] des comptes confirmés qui ont demandé les alertes (fonction alertes_destinataires, supabase.sql)."""
    cfg = (SITE / "config.js").read_text(encoding="utf-8")
    url, cle = (re.search(rf'{k}:\s*"([^"]+)"', cfg)[1] for k in ("supabaseUrl", "supabaseKey"))
    req = urllib.request.Request(f"{url}/rest/v1/rpc/alertes_destinataires", data=json.dumps({"jeton": jeton}).encode(),
                                 headers={"apikey": cle, "Content-Type": "application/json"})
    return [(r["email"], r["personne"]) for r in json.loads(urllib.request.urlopen(req, timeout=60).read())]


def envoyer(cle, expediteur, a, sujet, texte, html_):
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email", headers={"api-key": cle, "Content-Type": "application/json"},
                                 data=json.dumps({"sender": {"name": "Politiscope", "email": expediteur}, "to": [{"email": a}],
                                                  "subject": sujet, "textContent": texte, "htmlContent": html_,
                                                  "headers": {"List-Unsubscribe": f"<{ADRESSE}#/suivis>"}}).encode())
    urllib.request.urlopen(req, timeout=60).read()


def essai(ids):
    """Montre l'e-mail qu'un suivi recevrait si chaque fiche avait changé (sans rien envoyer)."""
    for i, p in fiches(ids).items():
        assert p, f"fiche introuvable : {i}"
        apres = signature(p)
        avant = {**apres, "m": apres["m"][1:] + [["Conseiller municipal", "Exemple"]],
                 "scrutins": (apres["scrutins"] or 0) - 3 if apres["scrutins"] else None, "hatvp": None}
        l = changements(avant, apres)
        assert any("nouvelle fonction" in x for x in l) and any("n'exerce plus" in x for x in l)
        assert changements(apres, apres) == [] and changements(apres, None)
        print(courriel({i: (apres["nom"], l)})[1], end="\n\n")


def main():
    if "--essai" in sys.argv:
        return essai(sys.argv[sys.argv.index("--essai") + 1:])
    jeton, cle, expediteur = (os.environ.get(k) for k in ("ALERTES_JETON", "BREVO_CLE", "ALERTES_EXPEDITEUR"))
    if not (jeton and cle and expediteur):
        print("Alertes par e-mail : non configurées (ALERTES_JETON, BREVO_CLE, ALERTES_EXPEDITEUR), rien envoyé.")
        return
    try:
        suivis = destinataires(jeton)
    except Exception as e:  # Supabase injoignable : on réessaiera au prochain passage
        print(f"⚠ Alertes : liste des destinataires illisible ({e.__class__.__name__}), rien envoyé.")
        return
    etat = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {"envoi": 0, "fiches": {}}
    actuel = {i: signature(p) if p else None for i, p in fiches({i for _, i in suivis}).items()}
    # Élu suivi pour la première fois : point de départ enregistré, sans alerte.
    nouveaux = {i: s for i, s in actuel.items() if s and i not in etat["fiches"]}
    etat["fiches"].update(nouveaux)
    modifie = bool(nouveaux)
    if time.time() - etat["envoi"] >= JOUR:
        diff = {i: changements(etat["fiches"][i], s) for i, s in actuel.items() if i in etat["fiches"]}
        par_personne = collections.defaultdict(dict)
        for email, i in suivis:
            if diff.get(i):
                par_personne[email][i] = (etat["fiches"][i]["nom"], diff[i])
        # shortcut: un envoi par personne et par jour, plafond gratuit de Brevo à 300 e-mails/jour ; au-delà, offre payante.
        envoyes = 0
        for email, par_elu in par_personne.items():
            try:
                envoyer(cle, expediteur, email, *courriel(par_elu))
                envoyes += 1
            except Exception as e:
                print(f"⚠ Alerte non envoyée ({e.__class__.__name__})")
        etat["envoi"], modifie = time.time(), True
        etat["fiches"].update({i: s for i, s in actuel.items() if s})
        for i in [i for i, s in actuel.items() if s is None]:
            etat["fiches"].pop(i, None)
        print(f"Alertes par e-mail : {envoyes} envoyée(s) sur {len(par_personne)}, {len(actuel)} élus suivis.")
    else:
        print("Alertes par e-mail : déjà envoyées aujourd'hui.")
    if modifie:
        ETAT.parent.mkdir(parents=True, exist_ok=True)
        ETAT.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")
    if os.environ.get("GITHUB_OUTPUT"):
        open(os.environ["GITHUB_OUTPUT"], "a").write(f"etat={'modifie' if modifie else 'inchange'}\n")


if __name__ == "__main__":
    main()
