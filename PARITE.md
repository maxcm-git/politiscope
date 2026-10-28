# Grille de parité Politicômetro → France

Inventaire fait le 24/10/2026 sur politicometro.org : accueil, carte, `/quem` (+ 7 sous-pages
par institution), `/representantes`, `/comparar`, `/cargos`, `/congresso`, `/governos` (+ `/governos/sp`),
`/impostos`, `/eleicoes`, `/propostas`, `/stf`, `/mais-vistos`, `/dados-abertos`, `/sobre`,
`/atualizacoes`, `/mcp`, `/sugestoes`, `/canal`, page d'État (`/uf/sp`), page de ville
(`/uf/sp?esfera=cidades&municipio=…`), fiches président (Lula), députée fédérale (Adriana Ventura),
conseiller municipal (Gustavo Petta).

**Légende**
- Légal : ✅ affichable · ⚠️ affichable sous condition (voir note) · ❌ interdit ou à proscrire
- Source : ✔ vérifiée pendant ce projet · ? à vérifier avant de coder
- Chez nous : ✅ fait · 🟡 partiel · ⬜ rien
- Priorité : 1 (d'abord) → 5

---

## A. Couverture : qui est sur le site

| # | Politicômetro | Équivalent France | Source FR | Légal | Chez nous | Prio |
|---|---|---|---|---|---|---|
| A1 | 70 908 élus en exercice, du conseiller municipal au président | Tous les élus : maires, adjoints, conseillers municipaux, communautaires, départementaux, régionaux, d'arrondissement, de Corse/outre-mer, députés, sénateurs, eurodéputés, conseillers des Français de l'étranger | RNE, 12 fichiers ✔ | ✅ | ✅ | 1 |
| A2 | Élus 2026 « en attente de prise de fonctions » | Élus pas encore installés (entre élection et installation) | Résultats Intérieur ? | ✅ | ⬜ | 4 |
| A3 | Président, vice-président | Président de la République, Premier ministre, gouvernement | AN (AMO) + HATVP ✔ | ✅ | ✅ | — |
| A4 | Juges de la Cour suprême (STF) | Membres du Conseil constitutionnel | conseil-constitutionnel.fr ? | ✅ | ⬜ | 4 |
| A5 | Photo de chaque personne | Photos des députés et sénateurs (sites AN/Sénat) ; élus locaux : pas de source | AN/Sénat ?, Wikimedia Commons ? | ⚠️ droits d'image à vérifier, sinon initiales | ✅ | 2 |

## B. Navigation et découverte

| # | Politicômetro | Équivalent France | Source FR | Légal | Chez nous | Prio |
|---|---|---|---|---|---|---|
| B1 | Carte en points, colorée par région, cliquable : région → État → ville (« 3 clics ») | Carte France (métropole + outre-mer) : région → département → commune | Contours IGN Admin Express / geo.api.gouv.fr ? | ✅ (Licence Ouverte) | ✅ | 1 |
| B2 | Page d'État : carte des villes, liste des 645 villes, tous les élus de l'État | Page de département et de région | RNE + contours | ✅ | ✅ | 1 |
| B3 | Page de ville : maire, adjoints, conseillers, nombre de députés/sénateurs, « ce que la ville publie » | Page de commune (~35 000) | RNE + INSEE (population) | ✅ | ✅ | 1 |
| B4 | « Me représente » : je tape ma ville → tous mes élus, de la mairie à Brasília | Ma commune → maire, conseil municipal, conseiller départemental (canton), région, député (circonscription), sénateurs, eurodéputés | RNE + table commune→canton (INSEE) + commune→circonscription ? | ✅ | ✅ | 1 |
| B5 | Annuaire A-Z, filtres fonction / État / parti / nom | Idem, filtres fonction / département / groupe ou nuance / nom | — | ✅ | ✅ | 1 |
| B6 | Listes par institution (`/quem/camara`…) avec stats : par État, par parti, femmes/hommes | Idem par institution | — | ✅ | 🟡 | 2 |
| B7 | Recherche par nom partout | Idem | — | ✅ | 🟡 | 2 |
| B8 | Fil d'Ariane Brasil › Região › Estado | France › Région › Département › Commune | — | ✅ | ✅ | 1 |

## C. Fiche d'un élu (« crachá »)

| # | Politicômetro | Équivalent France | Source FR | Légal | Chez nous | Prio |
|---|---|---|---|---|---|---|
| C1 | En-tête : fonction, lieu, parti, âge, lieu de naissance | Idem ; parti = groupe (parlement) ou nuance politique (élus locaux) | RNE ✔, AN AMO ✔, nuances Intérieur ? | ✅ | 🟡 | 2 |
| C2 | « Élu N fois, réélu N fois » | Calculé depuis l'historique des candidatures | Résultats Intérieur ? | ✅ | ⬜ | 3 |
| C3 | Mandat en cours (dates, titulaire/suppléant) + prochain mandat si élu | Idem | RNE ✔ | ✅ | 🟡 | 2 |
| C4 | Salaire mensuel + annuel | Parlementaires/exécutif : calcul légal ✔ ; élus locaux : **plafond légal** selon la population de la commune/département/région (le montant réellement voté n'est pas publié en open data) | CGCT + INSEE ✔/? | ✅ (afficher « plafond légal ») | 🟡 | 2 |
| C5 | Salaire cumulé perçu depuis l'entrée en fonction | Calcul indemnité × mois de mandat | — | ✅ (mention « estimation ») | ✅ estimation au barème actuel + plafond de cumul légal | 3 |
| C6 | Cote parlementaire : chaque dépense, fournisseur, note fiscale | Avance de frais de mandat (AFM) des députés : **non publiée** ligne par ligne | — | — (rien à publier) | ⬜ → afficher « non publié » | 3 |
| C7 | Équipe du cabinet (noms, niveau, date d'entrée) + enveloppe utilisée | Collaborateurs parlementaires (noms publiés par l'AN et le Sénat) ; enveloppe : montant légal du crédit collaborateur | AN/Sénat ? | ⚠️ noms publiés par les chambres ; ne pas aller au-delà | ⬜ | 3 |
| C8 | « Combien coûte le mandat » : salaire + cabinet + logement + cote | Indemnité + crédit collaborateurs + AFM (montants légaux) | Règlements AN/Sénat ? | ✅ | ⬜ | 3 |
| C9 | Présence séance par séance, % vs moyenne | AN : participation aux scrutins ✔ ; présence en commission (comptes rendus) ? ; présence en séance **non publiée** | AN open data ✔/? | ✅ (libeller exactement) | ✅ AN : scrutins + présence en commission (relevés de l'agenda) ; Sénat non publié | 2 |
| C10 | Comment il a voté : chaque scrutin, résultat, position du parti | AN : votes nominatifs ✔ ; Sénat : analyses nominatives sur senat.fr (pages web, pas d'open data) ? | AN ✔, senat.fr ? | ✅ | 🟡 | 2 |
| C11 | % de votes alignés sur la consigne du parti | AN publie la « position majoritaire » du groupe (pas la consigne) → « vote conforme à la majorité de son groupe » | AN scrutins ✔ | ✅ (libeller exactement) | ✅ | 2 |
| C12 | Propositions déposées, par thème, filtrables, « peut devenir loi » | Propositions de loi, amendements, questions écrites/orales | AN open data ?, Sénat (Ameli, questions) ? | ✅ | ✅ | 2 |
| C13 | Projets devenus lois | Lois issues de ses propositions | AN dossiers législatifs ?, Légifrance ? | ✅ | ✅ | 3 |
| C14 | Interventions en séance, résumées, par thème | Interventions en séance (comptes rendus) | AN (débats) ?, Sénat ? | ✅ (citer, pas réécrire) | ⬜ | 3 |
| C15 | Commissions (rôle, dates) | Commissions, délégations, groupes d'études | AN AMO ✔, Sénat ? | ✅ | ✅ | 2 |
| C16 | Voyages et missions officielles | Missions/déplacements : pas de source ouverte systématique | ? | ✅ | ⬜ | 5 |
| C17 | Argent des campagnes : recettes par origine, dépenses par poste, plus gros fournisseurs | Comptes de campagne CNCCFP : totaux recettes/dépenses par poste ; **pas de nom des donateurs particuliers** | CNCCFP / data.gouv ? | ⚠️ jamais de donateur personne physique | ⬜ | 3 |
| C18 | Chronologie de toutes les candidatures, élu ou non, depuis 2008 | Historique des candidatures (législatives, municipales, départementales, régionales, européennes, sénatoriales, présidentielle) | Résultats Intérieur (data.gouv) ? | ✅ pour les élus | ⬜ | 3 |
| C19 | Patrimoine déclaré, par année | **Interdit** (loi 2013-907, sanction pénale) | — | ❌ | ✅ (affiché « non publiable ») | — |
| C20 | Déclarations d'intérêts | HATVP : contenu des déclarations d'intérêts (activités, participations, fonctions) | HATVP liste.csv ✔, declarations.xml ✔ | ✅ intérêts seulement, jamais le patrimoine | ✅ contenu sur la fiche (sans conjoint ni collaborateurs) + lien vers le PDF officiel sur hatvp.fr | 2 |
| C21 | Données et contact : nom civil, naissance, scolarité, bureau, téléphone, e-mail | Contact professionnel (AN/Sénat), naissance (RNE) ; scolarité : pas de source | AN AMO ✔, RNE ✔ | ✅ contact professionnel uniquement | ✅ | 2 |
| C22 | Programme de gouvernement (PDF) + « comparer avec les autres candidats » | Professions de foi (législatives, présidentielle) | Intérieur ? | ✅ | ⬜ | 4 |
| C23 | Sélecteur d'année : toute la fiche bascule sur l'année | Idem | — | ✅ | ⬜ | 3 |
| C24 | Badge « ce qui est publié / ce qui ne l'est pas », avec la raison | Idem | — | ✅ | ✅ | — |
| C25 | « Comparer avec une autre personne » | Idem | — | ✅ | ✅ | 2 |
| C26 | Signaler une erreur | Idem (formulaire) | — | ⚠️ mention RGPD | ✅ | 2 |
| C27 | Droit de réponse | **Obligation légale** pour un service de presse en ligne (LCEN, art. 6 IV) | — | ✅ obligatoire | ✅ | 2 |

## D. Pages thématiques

| # | Politicômetro | Équivalent France | Source FR | Légal | Chez nous | Prio |
|---|---|---|---|---|---|---|
| D1 | `/cargos` : chaque fonction expliquée, pouvoirs, durée du mandat, schéma « qui élit / contrôle / juge qui », articles de la Constitution | Idem : Président, gouvernement, députés, sénateurs, Conseil constitutionnel, maires, conseillers… | Constitution, CGCT (Légifrance) | ✅ | ✅ | 3 |
| D2 | `/congresso` : Parlement en direct, agenda, ordre du jour, chaque vote, résultat par parti, filtres par thème | Assemblée + Sénat : agenda, ordre du jour, scrutins, résultat par groupe | AN open data ✔/?, Sénat ? | ✅ | ✅ agenda AN + séances Sénat, chaque scrutin AN par groupe (filtre thème : recherche texte) | 3 |
| D3 | `/governos` : mandats présidentiels côte à côte, indicateurs officiels année par année, temps forts (lois, posses) | Présidents / Premiers ministres : PIB, chômage, inflation, dette, déficit… ; lois marquantes | INSEE ?, Banque de France ?, Légifrance ? | ✅ (sans note ni couleur bon/mauvais) | ⬜ | 4 |
| D4 | `/governos/<État>` et `/governos/<ville>` | Régions, départements, communes : budgets et indicateurs par mandat | OFGL / DGFiP (comptes des collectivités) ? | ✅ | ⬜ | 4 |
| D5 | `/impostos` : recettes fiscales fédérales par mois, par impôt, par État, carte | Recettes fiscales de l'État par mois et par impôt ; par département si publié | DGFiP / Situation mensuelle budgétaire ? | ✅ | ⬜ | 4 |
| D6 | `/eleicoes` : résultats officiels depuis 1994, par lieu, tous les candidats, carte du vainqueur par État | Présidentielles (depuis 1965 ?), législatives, européennes, municipales, régionales, départementales, sénatoriales | Intérieur (data.gouv) ? | ⚠️ candidats non élus : à valider (RGPD) | ✅ élus seulement : législatives 2024 (résultat de la personne élue, sur 100 inscrits), municipales 2026 (participation, sièges des listes ayant des élus), régionales et départementales 2021 (listes avec sièges, binôme élu par canton), sénatoriales 2023/2026, européennes 2024 (liste et position) ; ni candidats non élus ni nuances | 3 |
| D7 | Résultats en direct le soir de l'élection | Résultats Intérieur en direct | Intérieur ? | ✅ | ⬜ | 5 |
| D8 | `/propostas` : programmes côte à côte par thème, extraits sans réécriture, recherche | Professions de foi / programmes déposés | Intérieur ? | ✅ (extraits fidèles) | ⬜ | 4 |
| D9 | `/stf` : agenda, décisions, procédures en cours, membres | Conseil constitutionnel : décisions, saisines en cours, membres | conseil-constitutionnel.fr, Légifrance (CONSTIT) ? | ✅ | ⬜ | 4 |
| D10 | `/dados-abertos` : qui publique quoi (communes, assemblées), carte | Quelles collectivités publient leurs données (délibérations, budgets, indemnités) | data.gouv (SCDL) ? | ✅ | ⬜ | 4 |
| D11 | `/mais-vistos` : fiches les plus consultées, visiteurs en direct, sans cookie ; liste neutre pendant l'élection | Idem | Mesure d'audience maison | ⚠️ sans cookie (exemption CNIL) ; neutralité en période électorale | ⬜ | 4 |
| D12 | `/sobre` : neutralité, méthode, sources, confidentialité | Idem (+ mentions légales) | — | ✅ (mentions légales obligatoires) | ✅ | 2 |
| D13 | `/atualizacoes` : date de dernière mise à jour par source, alerte si en retard | Idem | — | ✅ | ✅ | 3 |
| D14 | `/mcp` : serveur MCP pour assistants IA | Idem | — | ✅ | ⬜ | 5 |
| D15 | `/sugestoes` : formulaire de suggestion | Idem | — | ⚠️ RGPD | ⬜ | 4 |

## E. Interface et fonctions transverses

| # | Politicômetro | Équivalent France | Légal | Chez nous | Prio |
|---|---|---|---|---|---|
| E1 | Identité visuelle : fond gris-vert, Big Shoulders (chiffres), Public Sans (texte), IBM Plex Mono (sources), couleurs par niveau (fédéral, État, commune) | Identité propre, même rigueur (polices libres) | ✅ | ✅ | 1 |
| E2 | Badge de fiche : liseré coloré par niveau, photo, nom condensé, pastilles, grille de chiffres | Idem | ✅ | ✅ | 1 |
| E3 | Barre de navigation à onglets (Carte, Qui est qui, …) + bandeau d'annonce | Idem | ✅ | ✅ | 1 |
| E4 | Mode sombre | Idem | ✅ | ✅ | 2 |
| E5 | « Écouter cette page » (synthèse vocale) | Idem (synthèse vocale du navigateur) | ✅ | ✅ | 3 |
| E6 | Copier le lien, partager sur WhatsApp | Idem | ✅ | ✅ | 3 |
| E7 | Fenêtre d'accueil : tutoriel en 3 étapes + vidéo | Idem | ✅ | ⬜ | 4 |
| E8 | Chaîne WhatsApp, « ajouter à l'agenda » (.ics) | Idem (choix du canal à faire) | ✅ | ⬜ | 5 |
| E9 | Pied de chaque bloc : « Fonte : … · atualizado em … » | Idem | ✅ | ✅ | 2 |
| E10 | Neutralité : ordre alphabétique, aucune note, couleurs jamais partisanes, pas de consigne de vote | Idem | ✅ | ✅ | — |
| E11 | Adapté au mobile | Idem | ✅ | ✅ | 1 |

## F. Ce qui est illégal ou à proscrire en France

| Élément | Raison |
|---|---|
| Patrimoine déclaré (montant, biens) | Loi 2013-907 : reproduction des déclarations de patrimoine pénalement sanctionnée |
| Nom des donateurs personnes physiques | Non publiés par la CNCCFP ; données personnelles de particuliers |
| Adresses privées, informations familiales | RGPD : hors du mandat |
| Condamnations, procédures judiciaires | Pas de source ouverte fiable ; risque de diffamation et RGPD (données d'infraction) |
| Notes, classements, « meilleurs/pires » | Pas illégal, mais contraire à la neutralité du modèle |

## G. Arbitrages (Max, 24/10/2026)

1. **Photos** : oui, depuis les sites publics, de campagne, des partis… Priorité aux photos
   officielles AN/Sénat ; les photos de campagne/parti restent la propriété de leur auteur
   (risque droit d'auteur plus élevé) → créditer la source sous chaque photo.
2. **Candidats non élus** : **non publiés** (ni résultats nominatifs, ni historique).
3. **Nom du site** : « Politiscope » conservé comme titre de travail.
4. **Alertes et formulaires** : adresse temporaire ; destinataire définitif plus tard.
5. **Éditeur responsable** (mentions légales, droit de réponse) : plus tard.

## H. Ordre de reprise (par impact)

**Étape 3 (troisième lot) livré le 28/10/2026** : élections (élus seulement), pages de lieu en puces et graphiques, Comparer en couleurs par personne.

**Étape 3 (deuxième lot) livré le 28/10/2026** : Parlement en direct (agenda, scrutins par groupe), présence en commission, montant perçu et plafond de cumul, contenu HATVP et liens vers les PDF officiels, police Fraunces et Instrument Sans (conservée), cartes en aplats pastel.

**Étape 3 (premier lot) livrée le 28/10/2026** : activité des députés (propositions, lois, amendements, questions), mise à jour automatique et contrôlée (`update.py`), pages Qui fait quoi et Mises à jour, écouter, partager, nouvelle identité visuelle.

**Étape 2 livrée le 24/10/2026** : photos (1 035/1 038 nationaux), fiches enrichies (naissance, contact, commissions, chaque vote, vote conforme au groupe), plafonds d'indemnité locaux, Comparer, Signaler, Droit de réponse, À propos, mode sombre. Reste de l'étape 2 : C12 (propositions, amendements, questions), présence en commission (C9), contenu des déclarations d'intérêts (C20).

**Correction de sources (24/10/2026)** : le RNE retarde sur les changements en cours d'année (70 sénateurs sortants du renouvellement de septembre 2026, une dizaine de députés partis). Députés : Assemblée nationale ; sénateurs : Sénat ; le RNE reste la source des élus locaux et des eurodéputés.

**Étape 1 livrée le 24/10/2026** : tous les élus locaux, carte, pages région/département/commune, « Me représente », design aligné, mobile.


1. A1, B1–B5, B8, E1–E3, E11 : tous les élus locaux, carte, pages département/commune, « me représente », design aligné.
2. C1, C3, C4, C9–C12, C15, C20, C21, C25–C27, D12, E4, E9, A5 : fiche enrichie, comparer, signaler, droit de réponse.
3. C2, C5, C7, C8, C13, C14, C17, C18, C23, D1, D2, D6, D13, E5, E6 : historique électoral, Parlement en direct, fonctions expliquées.
4. A2, A4, C22, D3–D5, D8–D11, D15, E7 : gouvernements, impôts, Conseil constitutionnel, programmes, audience.
5. C16, D7, D14, E8 : direct électoral, MCP, alertes.
