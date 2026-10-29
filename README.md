# Politiscope — prototype

Transparence des élus français en données ouvertes.
**515 099 personnes** : Président, gouvernement, Parlement, eurodéputés et tous les élus locaux
(conseillers régionaux, départementaux, communautaires, municipaux, maires, adjoints…).
Feuille de route complète : `PARITE.md`.

## Ouvrir
Le site charge ses données à la demande : il faut le **servir en HTTP** (le double-clic ne suffit plus).
```bash
cd site && python3 -m http.server 8765   # puis http://localhost:8765
```

## Pages
Carte (régions → départements → communes) · page région, département, commune · « Me représente »
(commune ou code postal → tous ses élus) · Qui est qui (A–Z, filtres) · fiche par personne, tous mandats réunis.

## Structure
- `data/raw/` — sources brutes (12 fichiers RNE, HATVP, NosParlementaires…) ; `data/raw/geo/` — COG INSEE,
  communes geo.api, table des circonscriptions, contours simplifiés
- `data/_cache/` — gros téléchargements (scrutins AN, acteurs AN, contours des communes ~260 Mo), hors livrable
- `build_geo.py` — cartes SVG pré-projetées → `site/geo/`
- `build.py` — fiches nationales → `site/data.js` ; appelle `build_local.py` (élus locaux, fusion des mandats
  par nom + prénom + date de naissance) → `site/c/` (une fiche par commune), `site/d/` (département),
  `site/r/` (région), `site/n/` (annuaire par lettre), `site/communes.json` (recherche)
- `site/` — `index.html`, `styles.css`, `app.js` + données générées (~290 Mo non compressés, ~35 000 fichiers)

## Mettre à jour les données
Une seule commande, qui ne télécharge que ce qui a changé, vérifie tout et s'arrête au moindre doute :
```bash
python3 update.py          # sources -> vérification -> enrich_*.py -> build.py -> contrôles
python3 update.py --geo    # idem + cartes (contours des communes, une fois par an)
python3 update.py --check  # contrôle seulement le site déjà construit
```
- Une source injoignable, illisible ou nettement plus petite que la fois précédente : **arrêt, aucune donnée
  remplacée** (code de sortie 1).
- Après reconstruction, contrôles du site : nombre de députés, sénateurs, eurodéputés, Président, gouvernement,
  maires, personnes ; part des députés avec leurs votes ; part des responsables nationaux avec photo.
- Les dates de chaque source sont publiées sur la page « Mises à jour » du site (`site/sources.json`).
- Contours des communes : seulement avec `--geo` et s'ils manquent dans `data/_cache/contours/`.

Planifier (exemple, non installé) : une tâche chaque matin à 6 h 30, sur une machine allumée en permanence
(un petit serveur est préférable à un ordinateur portable) :
```
30 6 * * * cd /chemin/vers/Politiscope && /usr/bin/python3 update.py >> data/update.log 2>&1
```

## Données
- **Qui siège au Parlement : chaque chambre fait foi** (`enrich_parlement.py` → `data/raw/roster.json`).
  Le RNE retarde sur les changements en cours d'année : au 24/10/2026 il comptait encore 70 sénateurs sortants
  du renouvellement de septembre 2026 et une dizaine de députés partis.
  - Députés : Assemblée nationale (référentiel des acteurs, mandat en cours), groupe officiel de l'AN.
  - Sénateurs : Sénat (data.senat.fr, état ACTIF), groupe officiel, début de mandat, commissions.
  - Eurodéputés : le Parlement européen fait foi (liste des membres, `build.py` `eurodeputes()`) ; état civil du RNE, ou des
    candidatures 2024 pour un remplaçant absent du RNE. Au 28/10/2026, le RNE gardait encore un eurodéputé devenu sénateur.
  - Contrôle : aucun responsable national ne peut apparaître deux fois (`update.py --check`).
  - Élus locaux : RNE seul (pas d'autre source officielle) ; il ne contient que des mandats en cours, mais avec retard.
- **Fiches enrichies** (`data/raw/parlement.json`) : lieu de naissance, e-mail professionnel, commissions et
  organes en cours, page officielle. **Photos** (`site/photos/`, 320 px) : Assemblée nationale, Sénat, Parlement
  européen ; à défaut Wikimedia Commons via Wikidata (entité humaine décrite comme responsable politique).
  à défaut, portrait officiel du gouvernement versé sur Commons (« Portrait officiel de … »). 1 038/1 038 nationaux.
- **Photos des élus locaux** (`enrich_photos.py`) : Wikimedia Commons via Wikidata (personne française avec image, rattachée
  par date de naissance + nom + début du prénom) → `site/photos/l/` ; 878 élus locaux. Crédit complet sous chaque photo
  (auteur, licence, lien vers la page Commons), exigé par les licences CC BY / BY-SA ; aussi appliqué aux nationaux
  illustrés par Commons. Les sites des mairies ne sont pas utilisés automatiquement (formats hétérogènes, photos sans
  licence de réutilisation). Les autres élus locaux restent en initiales.
- **RNE** (Ministère de l'Intérieur, data.gouv.fr) — élus locaux et eurodéputés ; `deputes.csv`/`senateurs.csv`
  ne servent plus que de repli et pour la catégorie socio-professionnelle des députés.
- **Assemblée nationale** (open data, 17e législature) — votes nominatifs : 9 097 scrutins agrégés par
  `enrich_votes.py` → totaux, participation, **vote comme la majorité de son groupe** (l'AN publie la position
  majoritaire de chaque groupe, pas sa consigne), et chaque vote (`site/v/<député>.json` + `site/scrutins.json`).
  Rapprochement : 574/574 députés.
- **HATVP** (`liste.csv` + `merge/declarations.xml`, `enrich_hatvp.py` → `data/raw/hatvp_contenu.json`) — déclarations
  d'**intérêts** seulement (di, dia et modificatives). La plus récente est reprise sur la fiche (`site/h/<id>.json`) :
  activités professionnelles et rémunérations déclarées, consultant, organes dirigeants, participations financières,
  fonctions bénévoles, mandats, observations. Exclus : conjoint et collaborateurs (tiers ; lisibles dans le PDF),
  mentions « [Données non publiées] », déclarations de patrimoine (dsp*). Les PDF officiels ne sont pas copiés :
  le lien renvoie vers hatvp.fr (`https://www.hatvp.fr/livraison/dossiers/<fichier>`). Rapprochement : nom + date de
  naissance + un mot du prénom ; 2 857 fiches dont 809 nationaux (+ 26 avec PDF seulement). Rapprochement : 569/574 députés, 347/347 sénateurs, 81/81 eurodéputés, 36/36 exécutif.
- **Plafonds d'indemnité des élus locaux** (`build_local.py`, `plafond()`) : maires et adjoints selon la loi
  n° 2025-1249 (< 50 000 hab., note du préfet des Vosges, mars 2026) et le CGCT au-delà ; conseillers municipaux
  6 % ; conseillers départementaux L3123-16/17 ; présidence de région 145 %. Base : indice brut 1027 = 4 110,52 €.
  Population municipale INSEE (la loi retient la population totale), sans majorations ni régimes de
  Paris/Lyon/Marseille. Conseillers régionaux (hors présidence) et intercommunalités : barème non vérifié, non affiché.
- **Rémunérations** : calculées dans `build.py` (`remu()`) sur la base légale commune, la moyenne du
  traitement « hors échelle » le plus bas (HEA 1er chevron, IM 895) et le plus élevé (HEG, IM 1515)
  au point de 4,92278 € = 5 931,95 €, + 3 % de résidence + 25 % de fonction (× 1,2875) :
  - parlementaires : × 1 → **7 637 €** brut/mois (ordonnance n° 58-1210) ;
  - ministres et ministres délégués : × 1,4 → **10 692 €** (décret n° 2012-983, art. 2) ;
  - Président et Premier ministre : × 2,1 → **16 039 €** (décret n° 2012-983, art. 1 et 3) ;
  - secrétaires d'État : × 1,33 → 10 158 € (décret n° 2014-425 ; aucun dans le gouvernement actuel).
  Recoupé avec les montants publiés (un `assert` le vérifie au build). À mettre à jour si un décret
  revalorise le point d'indice ou la grille (gelés depuis 2023/2024).
  Eurodéputés : 10 075 € codé en dur, non recalculé, à vérifier (statut européen, autre base).

- **Exécutif** (Président + gouvernement) → `enrich_executif.py` → `data/raw/executif.json`.
  Aucune source unique ne dit « qui est en poste » : l'AN a les dates mais laisse des mandats
  d'anciens ministres ouverts, la HATVP a l'intitulé exact mais pas de date de fin. Règle : mandat
  ouvert à l'AN **et** déclaration gouvernementale à la HATVP (sans fin de fonctions postérieure).
  Résultat : 1 président + 35 membres du gouvernement. Si une personne figure aussi comme parlementaire
  (source en retard, ex. Françoise Gatel encore « active » au Sénat), l'exécutif prime et le build le signale.

## Pages ajoutées aux étapes 2 et 3
Comparer (2 à 5 personnes), Signaler une erreur et Droit de réponse (formulaires qui ouvrent la messagerie vers
l'adresse provisoire contact@politiscope.example, rien n'est stocké), À propos et méthode, mode sombre,
Qui fait quoi (fonctions expliquées), Mises à jour, écouter la page (synthèse vocale), partager.

## Parlement en direct, présence, rémunération perçue
`enrich_agenda.py` (agenda open data AN, qui reprend aussi les séances du Sénat) → `site/agenda.json` (J-7 à J+28) et
présence de chaque député aux réunions de commission (`presence_com`, relevés publiés par l'AN ; médiane affichée).
`enrich_votes.py` produit aussi le décompte de chaque scrutin par groupe → `site/s/<bloc>.json` (500 scrutins par bloc).
Pages `#/parlement` et `#/scrutin/<n>`. Fiches : montant perçu depuis le début du mandat (estimation : mois × montant
actuel) et plafond de cumul (1,5 × indemnité parlementaire de base, CGCT L2123-20 ; ordonnance 58-1210 art. 4).

## Élections (élus seulement)
`enrich_elections.py` (Ministère de l'Intérieur, data.gouv.fr) → `data/raw/elections.json`. Législatives 2024 : pour chaque
député élu en 2024, son résultat au tour décisif (voix, part des exprimés, « sur 100 inscrits ») ; ceux arrivés depuis
(partielle, remplacement) sont signalés comme tels. Municipales 2026 : participation et listes ayant obtenu des sièges
(dans `site/d/<dep>.json`, clé `municipales`). Régionales et territoriales 2021 : participation et listes ayant des
sièges (`site/r/<région>.json`, clé `regionales` ; outre-mer affiché sur la page département). Départementales 2021 :
binôme élu par canton (`site/d/<dep>.json`, clé `departementales`), repris sur la fiche du conseiller s'il en faisait partie.
Sénatoriales 2023 (xlsx) et 2026 : résultat de chaque sénateur (sa liste au proportionnel, ou son score au majoritaire),
rapprochement nom + date de naissance (341/347). Européennes 2024 : listes ayant des sièges (total national = somme des
départements, 81 sièges vérifiés) et, pour chaque eurodéputé, sa liste et sa position (fichier des candidatures).
Jamais de candidat ou de liste sans élu, ni de nuance politique. Fichiers 2021 en latin-1 (`.txt`).

## Activité des députés
`enrich_activite.py` (open data AN) : propositions déposées et cosignées, devenues lois (numéro, lien Légifrance),
amendements déposés, adoptés, cosignés (142 546 amendements lus dans l'archive), questions écrites (avec réponse),
orales et au gouvernement. Compteurs sur la fiche, listes dans `site/a/<slug>.json`.

## Identité visuelle
Motif de l'hémicycle en points (logo, accueil) ; cartes en aplats pastel (une teinte par région).
Lisibilité : résumé « En bref » en puces en tête de fiche, jauges (participation, vote avec son groupe, présence en
commission avec repère de la médiane), barre des plafonds cumulés, sections longues repliables (HATVP, propositions,
questions), scrutin en barres par groupe, Comparer avec une couleur par personne (ordre d'ajout, jamais le parti).
Pages de lieu : « En bref » (présidences, députés et sénateurs nommés, chiffres clés), part de femmes (repère à 50 %),
composition du conseil municipal, plafonds d'indemnité, communes par taille ou par département, listes A–Z repliables
sur mobile (ouvertes sur grand écran). Fraunces (titres, chiffres), Instrument Sans (texte), IBM Plex Mono (sources). Palette papier et encre, un accent bleu ; couleurs de niveau sans rouge (pas de lecture
partisane). Mode sombre automatique.

NB : le drapeau `active` de NosParlementaires est peu fiable côté Sénat → le RNE fait autorité sur
« qui siège », NosParlementaires ne fournit que le groupe.

### Votes : asymétrie AN / Sénat
Les votes nominatifs des **députés** sont publiés (AN, open data) → branchés. Le **Sénat ne publie
pas les votes nominatifs** en open data (vote souvent par groupe) : data.senat.fr couvre sénateurs,
textes, amendements, questions — pas les votes. Affiché tel quel sur les fiches, non inventé.
La « participation aux scrutins publics » n'est pas la présence physique.

### Pas encore branché
- **Rémunération des eurodéputés** recalculée depuis le statut européen.
- Groupe des **eurodéputés** (NosParlementaires ne couvre pas le PE),
  comparaison de deux élus, signaler une erreur.

### Limite juridique (≠ Brésil) : déclarations de patrimoine
Jamais republiées (loi n° 2013-907, art. 26 III : peines de l'art. 226-1 du code pénal) ; seules les déclarations
d'*intérêts* sont réutilisables (art. 5 IV et 12 I). Chaque fiche dit où les consulter (vérifié sur Légifrance le 28/10/2026) :
- Président et gouvernement : publiées par la HATVP sur hatvp.fr (art. 5) ;
- députés et sénateurs : préfecture du département d'élection, pour tout électeur inscrit (code électoral LO 135-2, LO 296) ;
  préfecture de Paris (Français de l'étranger), haut-commissariat (Nouvelle-Calédonie, Polynésie française) ;
- députés européens : toutes les préfectures (art. 12 II) ;
- élus locaux : ni publiées ni consultables.
La date de mise à disposition vient de `hatvp_liste.csv` (lignes dsp* « Livrée ») : seule cette date est reprise.

Nom « Politiscope » = titre de travail, à valider.

## Suivre des élus, image à partager
- **Mes élus** (`site/suivi.js`) : bouton ☆ Suivre sur chaque fiche, page `#/suivis`, bandeau sous le menu (masquable).
  Sans configuration (`site/config.js` vide) : *mode local de test*, compte et suivis gardés dans le navigateur.
  En ligne : Supabase (comptes + table `suivis`, schéma `supabase.sql`, chacun ne voit que ses lignes), clés dans `site/config.js`.
  Consentement explicite à la création du compte (la liste des élus suivis peut révéler une opinion politique, RGPD art. 9).
- **Image** (`site/partage.js`, bouton « Image » en haut) : story 1080×1920 ou carré 1080×1080, à partir des puces,
  chiffres et jauges de la page ; partage par la feuille de partage du téléphone, ou téléchargement. Tout se fait dans le navigateur.

## Mise en ligne et mise à jour automatique
- Hébergement : **GitHub Pages** (gratuit ; pas de limite de nombre de fichiers, 1 Go par site ; le site fait ~410 Mo).
  Vercel gratuit refusait plus de 15 000 fichiers / 100 Mo ; Vercel Pro (20 $/mois) écarté.
- `.github/workflows/mise-a-jour.yml` : toutes les heures, `update.py` (sans nouveauté : arrêt, rien n'est republié) ;
  sinon reconstruction, contrôles, publication sur GitHub Pages. Le cache GitHub garde téléchargements et site construit ;
  premier passage (ou « Run workflow » avec « complet ») : tout est retéléchargé (`--force`).
- Versionnés : le code, `site/geo/` (cartes, refaites à la main une fois par an avec `update.py --geo`, contours dans
  `data/_cache/contours/`), `data/raw/geo/` (circonscriptions 2017, contours régions et départements), portraits officiels
  relus (`data/raw/photos_officielles*`). Le reste est régénéré (`.gitignore`).
- Images : `sips` sur Mac, Pillow sur le serveur (`build_local.reduire`).
- GitHub suspend une tâche programmée après 60 jours sans activité sur le dépôt : un clic sur « Enable workflow » la relance.
