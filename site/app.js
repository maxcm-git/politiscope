// Politiscope — rendu client. Données nationales embarquées (data.js), le reste chargé à la demande :
// d/<dep>.json (communes + liste des élus), c/<commune>.json (fiches), r/<région>.json, n/<lettre>.json,
// geo/*.json (cartes pré-projetées), communes.json (recherche).
const DATA = window.DATA || [], META = window.META || {counts: {}};
const app = document.getElementById("app");
const BY = Object.fromEntries(DATA.map(p => [p.slug, p]));

const T = {  // type de mandat -> [libellé de liste, niveau]
  president: ["Présidence", "national"], gouvernement: ["Gouvernement", "national"],
  depute: ["Députés", "national"], senateur: ["Sénateurs", "national"], eurodepute: ["Députés européens", "europe"],
  cr: ["Conseillers régionaux", "region"], ma: ["Membres d'assemblée territoriale", "region"],
  cd: ["Conseillers départementaux", "departement"], cc: ["Conseillers communautaires", "interco"],
  maire: ["Maires", "commune"], adjoint: ["Adjoints au maire", "commune"], cm: ["Conseillers municipaux", "commune"],
  ca: ["Conseillers d'arrondissement", "commune"],
  cfe: ["Conseillers des Français de l'étranger", "etranger"], afe: ["Conseillers à l'AFE", "etranger"],
};
const INSTIT = {president: "Présidence de la République", gouvernement: "Gouvernement", depute: "Assemblée nationale",
  senateur: "Sénat", eurodepute: "Parlement européen", cr: "Conseil régional", ma: "Assemblée territoriale",
  cd: "Conseil départemental", cc: "Intercommunalité", maire: "Conseil municipal", adjoint: "Conseil municipal",
  cm: "Conseil municipal", ca: "Conseil d'arrondissement", cfe: "Conseil consulaire", afe: "Assemblée des Français de l'étranger"};
const RANG = {president: 0, gouvernement: 1, depute: 2, senateur: 2, eurodepute: 3, ma: 4, cr: 4, cd: 5,
  maire: 6, adjoint: 7, cc: 8, ca: 9, cm: 9, cfe: 10, afe: 10};  // mêmes valeurs que LEVEL (build_local.py)
const NATIONAL = new Set(["president", "gouvernement", "depute", "senateur", "eurodepute"]);
const COMMUNAL = new Set(["maire", "adjoint", "cm", "ca", "cc"]);
// Couleur = région (carte) ; aucun lien avec un parti. Une teinte par région, voisines bien distinctes :
// aplat pastel franc, le même sur la carte, les listes et les graphiques (RP).
const TEINTE = {"11": 350, "24": 55, "27": 265, "28": 100, "32": 205, "44": 30, "52": 300, "53": 175, "75": 150,
  "76": 330, "84": 220, "93": 15, "94": 160, "01": 280, "02": 20, "03": 140, "04": 200, "06": 320};
const RP = Object.fromEntries(Object.entries(TEINTE).map(([k, h]) => [k, `hsl(${h} 80% 79%)`]));
RP.COM = "#c9ccd1";
const DROM = new Set(["01", "02", "03", "04", "06"]);

const nf = n => (n ?? 0).toLocaleString("fr-FR");
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const norm = s => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
const fdate = s => { const d = new Date(s); return isNaN(d) ? "—" : d.toLocaleDateString("fr-FR", {day: "2-digit", month: "long", year: "numeric"}); };
const ageOf = s => { const d = new Date(s); if (isNaN(d)) return null; const n = new Date();
  return n.getFullYear() - d.getFullYear() - (n < new Date(n.getFullYear(), d.getMonth(), d.getDate()) ? 1 : 0); };
const ans = x => `${x.toLocaleString("fr-FR", {maximumFractionDigits: 1})} an${x >= 2 ? "s" : ""}`;
const lvlOf = t => (T[t] || [])[1] || "commune";
const depOf = c => (c.startsWith("97") || c.startsWith("98")) ? c.slice(0, 3) : c.slice(0, 2);
const initiales = (p, n) => ((p || "")[0] || "") + ((n || "")[0] || "");
const depNom = c => (META.deps?.[c] || {}).nom || c;
const eur = n => `${Math.round(n).toLocaleString("fr-FR")} €`;
const CONTACT = "contact@politiscope.example";  // adresse provisoire (arbitrage de Max)
const photoDe = e => e.shard === "fr" ? BY[e.slug]?.photo : e.photo;
const regNom = c => (META.regions || {})[c] || c;

const cache = new Map();
function get(url) {
  if (!cache.has(url)) cache.set(url, fetch(`${url}?v=${META.build || ""}`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .catch(e => { cache.delete(url); throw e; }));
  return cache.get(url);
}
let jeton = 0;  // évite qu'une page lente écrase la page suivante
const encore = j => j === jeton;

/* ---------- briques ---------- */

function setTab(r) { document.querySelectorAll("nav.tabs a").forEach(a => a.classList.toggle("on", a.dataset.r === r)); }
const src = t => `<p class="src">${t}</p>`;
const lien = e => `#/p/${e.shard}/${e.slug}`;

function visage(e) {  // e : {shard, slug, nom, prenom, f, lieu, t}
  const ph = photoDe(e);
  return `<a class="visage lvl-${lvlOf(e.t)}" href="${lien(e)}">${ph ? `<img class="ini" src="${ph}" alt="" loading="lazy">`
    : `<span class="ini">${esc(initiales(e.prenom, e.nom))}</span>`}
    <span><b>${esc(e.prenom)} ${esc(e.nom)}</b><small>${esc(e.f)}${e.lieu ? " · " + esc(e.lieu) : ""}</small></span></a>`;
}
const visages = l => l.length ? `<div class="visages">${l.map(visage).join("")}</div>` : `<p class="vide">Personne dans cette liste.</p>`;
const deNat = p => ({shard: "fr", slug: p.slug, nom: p.nom, prenom: p.prenom, sexe: p.sexe, t: p.chambre,
  f: p.titre || p.fonction, lieu: p.dep ? depNom(p.dep) : ""});
const deLeger = e => ({shard: e[0], slug: e[1], nom: e[2], prenom: e[3], sexe: e[4], t: e[5], f: e[6], lc: e[7], photo: e[8]});
const deIndex = e => ({shard: e[0], slug: e[1], nom: e[2], prenom: e[3], f: e[4], lieu: e[5], photo: e[7],
  t: Object.keys(RANG).find(k => RANG[k] === e[6])});
const tri = l => l.sort((a, b) => norm(a.nom).localeCompare(norm(b.nom)) || norm(a.prenom).localeCompare(norm(b.prenom)));
function unique(l) {  // une personne une fois, avec son mandat le plus important
  const m = new Map();
  for (const e of l) { const k = e.shard + "/" + e.slug, o = m.get(k); if (!o || RANG[e.t] < RANG[o.t]) m.set(k, e); }
  return [...m.values()];
}

// Liste A–Z avec rendu progressif (certaines lettres comptent des dizaines de milliers de noms).
function az(box, items, pas = 400) {
  tri(items);
  let n = pas;
  const lettre = e => (norm(e.nom)[0] || "#").toUpperCase();
  const dessine = () => {
    const vus = items.slice(0, n), groupes = {};
    vus.forEach(e => (groupes[lettre(e)] ||= []).push(e));
    const L = [...new Set(items.map(lettre))];
    box.innerHTML = `<p class="compte num">${nf(items.length)} ${items.length > 1 ? "personnes" : "personne"}, de A à Z</p>
      ${L.length > 1 ? `<div class="az-nav">${L.map(l => `<a href="javascript:void 0" data-l="${l}">${l}</a>`).join("")}</div>` : ""}
      ${Object.entries(groupes).map(([l, g]) => `<div class="az-l" id="az-${l}">${l}</div>${visages(g)}`).join("")}
      ${items.length > n ? `<button class="plus">Afficher ${nf(Math.min(pas, items.length - n))} de plus (${nf(items.length - n)} restants)</button>` : ""}`;
    box.querySelector(".plus")?.addEventListener("click", () => { n += pas; dessine(); });
    box.querySelectorAll(".az-nav a").forEach(a => a.addEventListener("click", () => {
      const i = items.findIndex(e => lettre(e) === a.dataset.l);
      if (i >= n) { n = i + pas; dessine(); }
      document.getElementById("az-" + a.dataset.l)?.scrollIntoView({behavior: "smooth"});
    }));
  };
  dessine();
}

/* ---------- cartes (SVG pré-projeté, aplats) ---------- */

function carte({viewBox, formes, etiquettes = [], encarts = []}) {
  return `<svg viewBox="${viewBox.join(" ")}" role="img">
    ${encarts.map(([code, x, y, w, h]) => `<g class="inset"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="6"/>
      <text x="${x + 6}" y="${y + 15}">${esc(depNom(code))}</text></g>`).join("")}
    ${formes.map(f => `<path d="${f.d}" fill="${f.c}" fill-rule="evenodd" data-href="${f.href}"
      class="${f.cls || ""}"><title>${esc(f.titre)}</title></path>`).join("")}
    ${etiquettes.map(([x, y, t]) => `<text x="${x}" y="${y}" text-anchor="middle">${esc(t)}</text>`).join("")}
  </svg>`;
}
function cliquable(box) {
  box.querySelectorAll("path[data-href]").forEach(p => p.addEventListener("click", () => { location.hash = p.dataset.href; }));
}
const unir = bs => { const b = [Infinity, Infinity, -Infinity, -Infinity];
  bs.forEach(x => { b[0] = Math.min(b[0], x[0]); b[1] = Math.min(b[1], x[1]); b[2] = Math.max(b[2], x[2]); b[3] = Math.max(b[3], x[3]); });
  const m = Math.max(b[2] - b[0], b[3] - b[1]) * 0.04; return [b[0] - m, b[1] - m, b[2] - b[0] + 2 * m, b[3] - b[1] + 2 * m]; };

/* ---------- recherche de lieu (communes + départements) ---------- */

function chercheLieu(input, box, vers) {
  let liste = null, choix = [];
  const rendu = async () => {
    const q = norm(input.value);
    if (q.length < 2) { box.innerHTML = ""; return; }
    liste ||= await get("communes.json");
    const deps = Object.entries(META.deps || {}).filter(([c, d]) => norm(d.nom).startsWith(q) || c.toLowerCase() === input.value.trim().toLowerCase())
      .map(([c, d]) => ({href: `#/d/${c}`, t: d.nom, s: `département ${c}`}));
    const chiffres = /^\d{2,5}$/.test(input.value.trim());
    const coms = [];
    for (const [code, nom, dep, cps] of liste) {
      if (chiffres ? cps.split(" ").some(cp => cp.startsWith(input.value.trim())) || code.startsWith(input.value.trim())
                   : norm(nom).startsWith(q)) coms.push({href: vers(code), t: nom, s: `${depNom(dep)} · ${cps.split(" ")[0] || code}`});
      if (coms.length >= 8) break;
    }
    choix = [...deps.slice(0, 3), ...coms].slice(0, 9);
    box.innerHTML = choix.length ? `<div class="suggestions">${choix.map((c, i) =>
      `<a href="${c.href}" class="${i ? "" : "on"}">${esc(c.t)} <small>${esc(c.s)}</small></a>`).join("")}</div>` : "";
  };
  input.addEventListener("input", rendu);
  input.addEventListener("focus", () => get("communes.json"));
  input.addEventListener("keydown", e => { if (e.key === "Enter" && choix[0]) location.hash = choix[0].href; });
}

/* ---------- accueil ---------- */

function hemicycle() {
  // Symbole, pas une donnée : six rangs, du centre (national) vers l'extérieur (communes).
  const rangs = ["national", "europe", "region", "departement", "interco", "commune"];
  let s = "";
  rangs.forEach((niv, i) => {
    const r = 46 + i * 24, n = Math.round(r / 7.2);
    for (let k = 0; k < n; k++) {
      const a = Math.PI * k / (n - 1);
      s += `<circle cx="${(200 - r * Math.cos(a)).toFixed(1)}" cy="${(196 - r * Math.sin(a)).toFixed(1)}" r="5.2" fill="var(--${niv})"/>`;
    }
  });
  return `<figure class="hemicycle"><svg viewBox="0 0 400 204" role="img" aria-label="Hémicycle : du centre vers l'extérieur, de l'Élysée à la mairie">${s}</svg>
    <figcaption>Du centre vers l'extérieur : national, européen, région, département, intercommunalité, commune</figcaption></figure>`;
}

async function accueil(j) {
  setTab("carte");
  const c = META.counts;
  const cm = (c.cm || 0) + (c.maire || 0) + (c.adjoint || 0);
  const comptes = [
    ["president", c.president, "Président de la République"], ["gouvernement", c.gouvernement, "Gouvernement"],
    ["depute", c.depute, "Députés"], ["senateur", c.senateur, "Sénateurs"], ["eurodepute", c.eurodepute, "Députés européens"],
    ["cr", (c.cr || 0) + (c.ma || 0), "Conseillers régionaux et territoriaux"], ["cd", c.cd, "Conseillers départementaux"],
    ["cc", c.cc, "Conseillers communautaires"], ["maire", c.maire, "Maires"], ["cm", cm, "Conseillers municipaux (dont maires et adjoints)"],
  ];
  app.innerHTML = `
    <section class="hero"><div><div class="big num">${nf(c.personnes)}</div>
      <p>élus et membres du gouvernement en fonction aujourd'hui, de la mairie à l'Élysée. Ce que chacun fait de son mandat, d'après les sources officielles.</p></div>
      ${hemicycle()}</section>
    <div class="compteurs">${comptes.map(([t, n, l]) => `<a href="#/annuaire?t=${t}"><div class="big num">${nf(n)}</div><span>${l}</span></a>`).join("")}</div>
    ${src(`Source : Répertoire national des élus, Ministère de l'Intérieur · mis à jour le ${META.maj} · Assemblée nationale et HATVP pour le gouvernement`)}
    <section class="carte"><div><p class="titre">France</p><span class="hint">Touchez une région</span><div id="map" class="charge">Chargement de la carte…</div></div>
      <aside class="panneau"><input class="recherche" id="lieu" placeholder="Commune, code postal ou département" autocomplete="off"><div id="sug"></div>
        <h3 style="margin-top:16px">Choisissez une région</h3><div class="regions" id="regs"></div>
        <p class="note">La couleur indique seulement la région. Aucun lien avec un parti ni avec une note.</p></aside></section>
    <section class="sec"><h2>Tout le monde, de A à Z</h2><p class="intro">Les premiers noms de chaque lettre, des institutions nationales aux conseils municipaux.
      Touchez la carte pour filtrer par lieu, ou cherchez un nom dans <a href="#/annuaire" style="color:var(--accent)">Qui est qui</a>.</p><div id="az" class="charge">Chargement…</div></section>`;
  chercheLieu(document.getElementById("lieu"), document.getElementById("sug"), code => `#/c/${code}`);
  const regs = Object.entries(META.regions || {}).filter(([k]) => k !== "COM")
    .sort(([a, x], [b, y]) => (DROM.has(a) - DROM.has(b)) || x.localeCompare(y));
  const depsDe = r => Object.entries(META.deps || {}).filter(([, d]) => d.region === r).map(([k]) => k).sort();
  document.getElementById("regs").innerHTML = regs.map(([k, nom]) => {
    const ds = depsDe(k);
    return `<a href="${DROM.has(k) ? `#/d/${ds[0]}` : `#/r/${k}`}"><span class="big num pastel" style="background:${RP[k]}">${ds.length}</span>
      <b>${esc(nom)}</b><small>${ds.join(" · ")}</small></a>`;
  }).join("");

  const [fr, idx] = await Promise.all([get("geo/france.json"), get("n/index.json")]);
  if (!encore(j)) return;
  const map = document.getElementById("map");
  map.classList.remove("charge");
  map.innerHTML = carte({viewBox: [0, 0, fr.w, fr.h], encarts: fr.insets,
    formes: fr.regions.map(([code, d]) => ({d, c: RP[code] || "#c9ccd1", titre: regNom(code),
      href: DROM.has(code) ? `#/d/${depsDe(code)[0]}` : `#/r/${code}`}))});
  cliquable(map);
  const azBox = document.getElementById("az");
  azBox.classList.remove("charge");
  azBox.innerHTML = `<div class="az-nav">${Object.keys(idx).map(l => `<a href="#/annuaire?l=${l}">${l}</a>`).join("")}</div>` +
    Object.entries(idx).map(([l, [n, top]]) => `<div class="az-l">${l}</div>${visages(top.map(deIndex))}
      <a class="plus" href="#/annuaire?l=${l}">Voir les ${nf(n)} noms en ${l} →</a>`).join("");
}

/* ---------- région ---------- */

async function region(code, j) {
  setTab("carte");
  const [fr, r] = await Promise.all([get("geo/france.json"), get(`r/${code}.json`).catch(() => ({elus: []}))]);
  if (!encore(j)) return;
  const deps = fr.deps.filter(d => d[1] === code);
  const elus = unique(r.elus.map(deLeger));
  const presidence = elus.filter(e => /^Présidente? du conseil|^Présidente? de l'assemblée/.test(e.f));
  const nbCom = deps.reduce((s, d) => s + ((META.deps[d[0]] || {}).communes || 0), 0);
  app.innerHTML = `
    <div class="ariane"><a href="#/">France</a> › <span>${esc(regNom(code))}</span></div>
    <div class="lieu-h"><div class="kicker">Région</div><h1>${esc(regNom(code))}</h1></div>
    <div class="chiffres"><div><span class="big num">${deps.length}</span><span>départements</span></div>
      <div><span class="big num">${nf(nbCom)}</span><span>communes</span></div>
      <div><span class="big num">${nf(elus.length)}</span><span>élus au conseil régional ou à l'assemblée</span></div></div>
    <section class="carte"><div><span class="hint">Touchez un département</span><div id="map"></div></div>
      <aside class="panneau"><h3>Les départements</h3><div class="regions">${deps.sort((a, b) => depNom(a[0]).localeCompare(depNom(b[0]))).map(d =>
        `<a href="#/d/${d[0]}"><span class="big num pastel" style="background:${RP[code]};font-size:26px">${d[0]}</span><b>${esc(depNom(d[0]))}</b>
        <small>${nf((META.deps[d[0]] || {}).communes)} communes</small></a>`).join("")}</div></aside></section>
    ${enBref([presidence.length ? `Présidence : ${noms(presidence)}` : "",
      `<b>${deps.length}</b> départements, <b>${nf(nbCom)}</b> communes`,
      `<b>${nf(elus.length)}</b> élus au conseil régional ou à l'assemblée de la collectivité`,
      elus.length ? `<b>${Math.round(100 * elus.filter(e => e.sexe === "F").length / elus.length)} %</b> de femmes parmi ces élus` : ""])}
    <div class="jauges">${parite(elus, "au conseil régional")}
      ${barresCarte("Communes par département", deps.map(d => [esc(depNom(d[0])), (META.deps[d[0]] || {}).communes || 0, RP[code]]))}</div>
    <section class="sec"><h2>Conseil régional</h2><p class="intro">Toutes les personnes élues, de A à Z. La présidence en premier.</p>
      ${presidence.length ? visages(presidence.map(e => ({...e, lieu: regNom(code)}))) : ""}${pli("Tous les élus, de A à Z", nf(elus.length), `<div id="liste"></div>`, large())}
      ${src(`Source : Répertoire national des élus · mis à jour le ${META.maj}`)}</section>
    ${r.regionales ? scrutinListes(`${["94", "02", "03"].includes(code) ? "Élections territoriales" : "Élections régionales"} de juin 2021`, r.regionales,
      ["94", "02", "03"].includes(code) ? "de l'assemblée" : "du conseil régional") : ""}`;
  const map = document.getElementById("map");
  map.innerHTML = carte({viewBox: unir(deps.map(d => d[4])),
    formes: deps.map(([c, , d]) => ({d, c: RP[code], titre: depNom(c), href: `#/d/${c}`})),
    etiquettes: deps.filter(d => d[3]).map(d => [d[3][0], d[3][1], depNom(d[0])])});
  map.querySelectorAll("text").forEach(t => t.style.fontSize = (unir(deps.map(d => d[4]))[2] / 60) + "px");
  cliquable(map);
  az(document.getElementById("liste"), elus);
}

/* ---------- département et commune ---------- */

const TRANCHES = [["Moins de 500 hab.", 0, 500], ["500 à 1 999", 500, 2000], ["2 000 à 9 999", 2000, 10000],
  ["10 000 à 49 999", 10000, 50000], ["50 000 et plus", 50000, Infinity]];

async function chargeDep(dep) {
  const [d, g] = await Promise.all([get(`d/${dep}.json`), get(`geo/d/${dep}.json`).catch(() => null)]);
  d.byCode ||= Object.fromEntries(d.communes.map(c => [c[0], c]));
  return [d, g];
}
function carteDep(box, d, g, sel) {
  if (!g) { box.innerHTML = `<p class="vide">Pas de carte pour ce territoire.</p>`; return; }
  const couleur = RP[d.region] || "#c9ccd1";
  box.innerHTML = carte({viewBox: [0, 0, g.w, g.h],
    formes: g.c.map(([code, path]) => ({d: path, c: couleur, titre: (d.byCode[code] || [, code])[1],
      href: `#/c/${code}`, cls: sel ? (code === sel ? "sel" : "") : ""}))});
  cliquable(box);
}
function listeCommunes(input, box, d) {
  const dessine = () => {
    const q = norm(input.value);
    const l = d.communes.filter(c => !q || norm(c[1]).startsWith(q) || c[3].includes(input.value.trim()));
    box.innerHTML = l.slice(0, 300).map(c => `<a href="#/c/${c[0]}"><span>${esc(c[1])}</span><small>${nf(c[2])} hab.</small></a>`).join("")
      + (l.length > 300 ? `<p class="note">${nf(l.length - 300)} autres : affinez la recherche.</p>` : "");
  };
  input.addEventListener("input", dessine);
  dessine();
}
const arianeDep = (d, extra = "") => `<div class="ariane"><a href="#/">France</a> › ${d.region && d.region !== "COM" && !DROM.has(d.region)
  ? `<a href="#/r/${d.region}">${esc(regNom(d.region))}</a> › ` : ""}${extra ? `<a href="#/d/${d.code}">${esc(d.nom)}</a> › ${extra}` : esc(d.nom)}</div>`;

async function departement(dep, j) {
  setTab("carte");
  const [d, g] = await chargeDep(dep);
  if (!encore(j)) return;
  const elus = d.elus.map(deLeger);
  const parl = DATA.filter(p => (p.chambre === "depute" || p.chambre === "senateur") && p.dep === dep).map(deNat);
  const cd = unique(elus.filter(e => e.t === "cd")).map(e => ({...e, lieu: d.cantons[e.lc] ? `canton ${d.cantons[e.lc]}` : ""}));
  const maires = elus.filter(e => e.t === "maire").map(e => ({...e, lieu: (d.byCode[e.lc] || [, ""])[1]}));
  const pop = d.communes.reduce((s, c) => s + c[2], 0);
  // Outre-mer : région d'un seul département, pas de page région -> résultats régionaux ici.
  const rr = DROM.has(d.region) ? await get(`r/${d.region}.json`).catch(() => null) : null;
  if (!encore(j)) return;
  const presCd = cd.filter(e => /^Présidente? du conseil/.test(e.f)), petites = d.communes.filter(c => c[2] < 1000).length;
  const cs = Object.entries(d.departementales || {}).sort((a, b) => (d.cantons[a[0]] || "").localeCompare(d.cantons[b[0]] || "", "fr"));
  const somme = k => cs.reduce((t, [, r]) => t + r[k], 0), t1 = cs.filter(([, r]) => r.tour === 1).length;
  const depSec = !cs.length ? "" : `<section class="sec"><h2>Élections départementales de juin 2021</h2>
    <div class="jauges">${jauge(Math.round(part(somme("votants"), somme("inscrits"))), "de participation", `au tour décisif de chaque canton · ${nf(somme("votants"))} votants sur ${nf(somme("inscrits"))} inscrits`)}
      ${barresCarte("Cantons selon le tour décisif", [["Binôme élu au 1er tour", t1, RP[d.region]], ["Binôme élu au 2nd tour", cs.length - t1, RP[d.region]]])}</div>
    ${pli("Le résultat dans chaque canton", nf(cs.length), cs.map(([k, r]) => { const ici = cd.filter(e => e.lc === k);
      return `<div class="kv"><b>${esc(d.cantons[k] || k)}</b><span>${ici.length ? noms(tri([...ici])) : "—"}
      <small class="muted" style="display:block">binôme élu en 2021 avec ${fpc(part(r.voix, r.exprimes))} des suffrages exprimés · ${TOUR(r.tour)} · participation ${fpc(part(r.votants, r.inscrits))}${
        r.en_place.length < ici.length ? ` · ${ici.length - r.en_place.length > 1 ? "deux conseillers arrivés" : "un conseiller arrivé"} depuis (remplacement)` : ""}</small></span></div>`; }).join(""), large())}
    ${src("Source : Ministère de l'Intérieur, résultats officiels des départementales des 20 et 27 juin 2021 (data.gouv.fr). Seuls les conseillers en fonction aujourd'hui sont nommés (Répertoire national des élus).")}</section>`;
  app.innerHTML = `${arianeDep(d)}
    <div class="lieu-h"><div class="kicker">Département ${esc(d.code)}${d.region ? " · " + esc(regNom(d.region)) : ""}</div><h1>${esc(d.nom)}</h1></div>
    <div class="chiffres"><div><span class="big num">${nf(d.communes.length)}</span><span>communes</span></div>
      ${pop ? `<div><span class="big num">${nf(pop)}</span><span>habitants</span></div>` : ""}
      <div><span class="big num">${nf(unique(elus).length)}</span><span>élus</span></div>
      <div><span class="big num">${parl.filter(p => p.t === "depute").length}</span><span>députés</span></div>
      <div><span class="big num">${parl.filter(p => p.t === "senateur").length}</span><span>sénateurs</span></div></div>
    <section class="carte"><div><span class="hint">Touchez une commune</span><div id="map"></div></div>
      <aside class="panneau"><input class="recherche" id="q" placeholder="Chercher une commune ou un code postal" autocomplete="off">
        <div class="liste-lieux" id="coms"></div></aside></section>
    ${enBref([presCd.length ? `Présidence du conseil départemental : ${noms(presCd)}` : "",
      `<b>${nf(d.communes.length)}</b> communes${pop ? `, <b>${nf(pop)}</b> habitants` : ""}`,
      parl.length ? `Au Parlement : <b>${parl.filter(p => p.t === "depute").length}</b> députés, <b>${parl.filter(p => p.t === "senateur").length}</b> sénateurs` : "",
      maires.length ? `<b>${Math.round(100 * maires.filter(e => e.sexe === "F").length / maires.length)} %</b> des maires sont des femmes` : "",
      `<b>${Math.round(100 * petites / Math.max(d.communes.length, 1))} %</b> des communes comptent moins de 1 000 habitants`])}
    <div class="jauges">${parite(maires, "parmi les maires")}
      ${barresCarte("Communes selon leur population", TRANCHES.map(([l, a, b]) => [l, d.communes.filter(c => c[2] >= a && c[2] < b).length, RP[d.region]]),
        nf, "Population municipale INSEE.")}</div>
    <section class="sec"><h2>Au Parlement</h2>${visages(tri(parl))}</section>
    <section class="sec"><h2>Conseil départemental</h2><p class="intro">${cd.length ? "Présidence en premier, puis de A à Z." : "Ce territoire n'a pas de conseil départemental (collectivité à statut particulier)."}</p>
      ${visages([...cd.filter(e => /^Présidente? du conseil/.test(e.f)), ...tri(cd.filter(e => !/^Présidente? du conseil/.test(e.f)))])}</section>
    ${depSec}
    ${rr?.regionales ? scrutinListes(`${["02", "03"].includes(d.region) ? "Élections territoriales" : "Élections régionales"} de juin 2021`, rr.regionales,
      ["02", "03"].includes(d.region) ? "de l'assemblée" : "du conseil régional") : ""}
    <section class="sec"><h2>Maires</h2>${pli("Tous les maires, de A à Z", nf(maires.length), `<div id="maires"></div>`, large())}</section>
    <p><a class="btn" href="#/annuaire?d=${dep}">Tous les élus du département dans l'annuaire →</a></p>
    ${src(`Source : Répertoire national des élus · mis à jour le ${META.maj} · population : INSEE via geo.api.gouv.fr`)}`;
  carteDep(document.getElementById("map"), d, g);
  listeCommunes(document.getElementById("q"), document.getElementById("coms"), d);
  az(document.getElementById("maires"), maires);
}

async function commune(code, j) {
  setTab("carte");
  const dep = depOf(code);
  const [d, g] = await chargeDep(dep);
  if (!encore(j)) return;
  const c = d.byCode[code];
  if (!c) { app.innerHTML = `<p class="vide">Commune introuvable.</p>`; return; }
  const ici = d.elus.map(deLeger).filter(e => e.lc === code && ["maire", "adjoint", "cm", "ca"].includes(e.t));
  const conseil = unique(ici.filter(e => e.t !== "ca"));
  const maires = conseil.filter(e => e.t === "maire");
  const adjoints = conseil.filter(e => e.t === "adjoint").sort((a, b) => (parseInt(a.f) || 99) - (parseInt(b.f) || 99));
  const cms = conseil.filter(e => e.t === "cm");
  const ca = unique(ici.filter(e => e.t === "ca"));
  const deputes = DATA.filter(p => p.chambre === "depute" && (c[5].length ? c[5].includes(p.circo_code) : p.dep === dep)).map(deNat);
  const mu = d.municipales?.[code];
  const munSec = mu ? scrutinListes("Élections municipales de mars 2026", mu, "du conseil municipal") : "";
  app.innerHTML = `${arianeDep(d, esc(c[1]))}
    <div class="lieu-h"><div class="kicker">Commune · ${esc(d.nom)}</div><h1>${esc(c[1])}</h1></div>
    <div class="chiffres">${c[2] ? `<div><span class="big num">${nf(c[2])}</span><span>habitants</span></div>` : ""}
      <div><span class="big num">${conseil.length}</span><span>au conseil municipal</span></div>
      <div><span class="big num">${adjoints.length}</span><span>adjoints au maire</span></div>
      ${c[3] ? `<div><span class="big num" style="font-size:24px">${esc(c[3].split(" ").slice(0, 3).join(" · "))}${c[3].split(" ").length > 3 ? " …" : ""}</span><span>code postal</span></div>` : ""}</div>
    ${enBref([maires.length ? `Maire : ${noms(maires)}` : "",
      `Conseil municipal : <b>${conseil.length}</b> membres, dont <b>${adjoints.length}</b> adjoints`,
      conseil.length ? `<b>${Math.round(100 * conseil.filter(e => e.sexe === "F").length / conseil.length)} %</b> de femmes au conseil municipal` : "",
      c[6] && d.epcis[c[6]] ? `Intercommunalité : ${esc(d.epcis[c[6]])}` : "",
      d.cantons[c[4]] ? `Canton : ${esc(d.cantons[c[4]])}` : "",
      deputes.length ? `${deputes.length > 1 ? "Députés" : "Député"} : ${noms(deputes)}` : "",
      mu ? `Conseil élu au ${TOUR(mu.tour)} des municipales de mars 2026, participation <b>${fpc(part(mu.votants, mu.inscrits))}</b>` : "",
      c[7]?.[0] ? `Indemnité du maire : au plus <b>${eur(c[7][0])}</b> brut par mois (plafond légal)` : ""])}
    <div class="actions-lieu"><a class="btn" href="#/moi/${code}">Qui me représente à ${esc(c[1])} →</a></div>
    <div class="jauges">${barresCarte("Composition du conseil municipal", [["Maire", maires.length, "var(--commune)"], ["Adjoints", adjoints.length, "var(--commune)"],
        ["Conseillers municipaux", cms.length, "var(--commune)"]])}
      ${parite(conseil, "au conseil municipal")}
      ${c[7]?.[0] ? barresCarte("Plafonds légaux d'indemnité / mois", [["Maire", c[7][0], "var(--commune)"], ["Adjoint", c[7][1], "var(--commune)"],
        ["Conseiller", 246.63, "var(--commune)"]], eur, "Selon le CGCT et la population INSEE ; le montant réellement voté n'est pas publié en open data.") : ""}</div>
    <section class="carte"><div><div id="map"></div></div>
      <aside class="panneau"><input class="recherche" id="q" placeholder="Autre commune du département" autocomplete="off">
        <div class="liste-lieux" id="coms"></div></aside></section>
    <section class="sec"><h2>Qui gouverne et légifère à ${esc(c[1])}</h2><p class="intro">Le maire, les adjoints dans l'ordre du tableau, puis le conseil municipal de A à Z.</p>
      <div class="bloc"><h3>Maire</h3>${visages(maires)}</div>
      ${adjoints.length ? `<div class="bloc"><h3>Adjoints au maire</h3>${visages(adjoints)}</div>` : ""}
      ${pli("Conseil municipal, de A à Z", nf(cms.length), `<div id="cm"></div>`, large())}
      ${ca.length ? pli("Conseils d'arrondissement ou de secteur", nf(ca.length), `<div id="ca"></div>`) : ""}
      ${src(`Source : Répertoire national des élus · mis à jour le ${META.maj}`)}</section>
    ${munSec}
    <section class="sec"><h2>Ce que ${esc(c[1])} publie</h2>
      ${badge([["ok", "✓", "Élus et fonctions", "publiés — Répertoire national des élus"],
        c[7]?.[0] ? ["ok", "✓", "Plafonds légaux d'indemnité", `maire : ${eur(c[7][0])}, adjoint : ${eur(c[7][1])}, conseiller : jusqu'à ${eur(246.63)} brut / mois (CGCT, population INSEE). Les montants réellement votés ne sont pas publiés en open data.`]
          : ["soon", "·", "Indemnités des élus", "non publiées en open data"],
        ["soon", "·", "Délibérations, budget", "à brancher — données des collectivités (data.gouv.fr)"]])}</section>`;
  carteDep(document.getElementById("map"), d, g, code);
  listeCommunes(document.getElementById("q"), document.getElementById("coms"), d);
  az(document.getElementById("cm"), cms);
  if (ca.length) az(document.getElementById("ca"), ca.map(e => ({...e, lieu: ""})));
}

/* ---------- qui me représente ---------- */

async function moi(code, j) {
  setTab("moi");
  if (!code) {
    app.innerHTML = `<div class="lieu-h" style="margin-top:30px"><h1>Qui sont vos représentants ?</h1></div>
      <p class="muted">Tapez votre commune ou votre code postal : tous les élus qui vous représentent aujourd'hui, de la mairie au Parlement européen.</p>
      <input class="recherche" id="lieu" placeholder="Commune ou code postal" autocomplete="off" style="max-width:520px;font-size:17px;padding:12px 18px"><div id="sug" style="max-width:520px"></div>
      <div class="niveaux">
        <div class="niveau lvl-commune" style="--lvl:var(--commune)"><h3>Dans votre commune</h3><p>Maire, adjoints, conseil municipal, intercommunalité</p></div>
        <div class="niveau" style="--lvl:var(--departement)"><h3>Dans votre département et votre région</h3><p>Conseillers départementaux de votre canton, conseil régional</p></div>
        <div class="niveau" style="--lvl:var(--national)"><h3>À Paris et à Bruxelles</h3><p>Député de votre circonscription, sénateurs, députés européens, gouvernement</p></div>
      </div>`;
    chercheLieu(document.getElementById("lieu"), document.getElementById("sug"), c => `#/moi/${c}`);
    document.getElementById("lieu").focus();
    return;
  }
  const dep = depOf(code);
  const [d] = await chargeDep(dep);
  const c = d.byCode[code];
  const r = d.region && d.region !== "COM" ? await get(`r/${d.region}.json`).catch(() => ({elus: []})) : {elus: []};
  if (!encore(j)) return;
  if (!c) { app.innerHTML = `<p class="vide">Commune introuvable.</p>`; return; }
  const elus = d.elus.map(deLeger);
  const conseil = unique(elus.filter(e => e.lc === code && ["maire", "adjoint", "cm"].includes(e.t)));
  const tete = conseil.filter(e => e.t !== "cm").sort((a, b) => RANG[a.t] - RANG[b.t] || (parseInt(a.f) || 99) - (parseInt(b.f) || 99));
  const memesEpci = new Set(d.communes.filter(x => x[6] && x[6] === c[6]).map(x => x[0]));
  const cc = unique(elus.filter(e => e.t === "cc" && memesEpci.has(e.lc)));
  const ccTete = cc.filter(e => /^Présidente? du conseil/.test(e.f));
  // Canton : code direct, ou commune partagée entre plusieurs cantons (pseudo-canton 8x/9x) -> par nom.
  const pseudo = c[4] && +c[4].slice(-2) >= 80;
  const cantons = pseudo ? Object.keys(d.cantons).filter(k => norm(d.cantons[k]).startsWith(norm(c[1]))) : [c[4]];
  const cd = unique(elus.filter(e => e.t === "cd" && cantons.includes(e.lc))).map(e => ({...e, lieu: `canton ${d.cantons[e.lc] || ""}`}));
  const presDep = unique(elus.filter(e => e.t === "cd" && /^Présidente? du conseil/.test(e.f)));
  const reg = unique(r.elus.map(deLeger));
  const presReg = reg.filter(e => /^Présidente? (du conseil|de l'assemblée)/.test(e.f));
  const ma = unique(elus.filter(e => e.t === "ma"));
  const deputes = DATA.filter(p => p.chambre === "depute" && (c[5].length ? c[5].includes(p.circo_code) : p.dep === dep)).map(deNat);
  const senateurs = DATA.filter(p => p.chambre === "senateur" && p.dep === dep).map(deNat);
  const exec = DATA.filter(p => p.chambre === "president" || (p.chambre === "gouvernement" && /^Premi/.test(p.titre))).map(deNat);
  const bloc = (h, p, l, plus = "") => `<div class="bloc"><h3>${h}</h3><p>${p}</p>${visages(l)}${plus}</div>`;
  app.innerHTML = `<div class="ariane"><a href="#/moi">Me représente</a> › <a href="#/c/${code}">${esc(c[1])}</a></div>
    <div class="lieu-h"><div class="kicker">Commune · ${esc(d.nom)}</div><h1>Qui représente ${esc(c[1])}</h1></div>
    ${enBref([tete.find(e => e.t === "maire") ? `Maire : ${lienNom(tete.find(e => e.t === "maire"))}` : "",
      ccTete.length ? `Présidence de l'intercommunalité : ${noms(ccTete)}` : "",
      cd.length ? `Conseillers départementaux : ${noms(tri([...cd]))}` : "",
      presReg.length ? `Présidence de région : ${noms(presReg)}` : "",
      deputes.length ? `${deputes.length > 1 ? "Députés" : "Député"} : ${noms(deputes)}` : "",
      senateurs.length ? `Sénateurs : ${noms(tri([...senateurs]))}` : ""])}
    <p class="muted">Le détail par niveau, ordre alphabétique dans chaque groupe.</p>
    <h2 class="sec" style="margin-bottom:0">Dans votre commune</h2>
    ${bloc("Maire et adjoints", `${conseil.length} membres au conseil municipal.`, tete, `<a class="plus" href="#/c/${code}">Voir tout le conseil municipal →</a>`)}
    ${cc.length ? bloc(`Intercommunalité : ${esc(d.epcis[c[6]] || "")}`, `${cc.length} conseillers communautaires, présidence ci-dessous.`, ccTete) : ""}
    <h2 class="sec" style="margin-bottom:0">Dans votre département et votre région</h2>
    ${cd.length ? bloc(`Conseillers départementaux${pseudo ? " (votre commune compte plusieurs cantons)" : ` du canton ${esc(d.cantons[c[4]] || "")}`}`, "Élus en binôme pour le canton.", cd) : ""}
    ${presDep.length ? bloc("Présidence du conseil départemental", esc(d.nom), presDep) : ""}
    ${ma.length ? bloc("Assemblée de la collectivité", `${ma.length} membres.`, ma.filter(e => /^Présidente?/.test(e.f))) : ""}
    ${reg.length ? bloc(`Conseil régional : ${esc(regNom(d.region))}`, `${reg.length} conseillers régionaux, présidence ci-dessous.`, presReg, `<a class="plus" href="#/r/${d.region}">Voir tout le conseil régional →</a>`) : ""}
    <h2 class="sec" style="margin-bottom:0">À Paris et à Bruxelles</h2>
    ${bloc(deputes.length === 1 ? "Votre député" : "Députés", c[5].length ? "Élus dans votre circonscription." : "Circonscription non déterminée : tous les députés du département.", deputes)}
    ${bloc("Sénateurs", `Élus pour le département ${esc(d.nom)}.`, tri(senateurs))}
    ${bloc("Exécutif", "Président de la République et Premier ministre.", exec, `<a class="plus" href="#/annuaire?t=gouvernement">Tout le gouvernement →</a>`)}
    <div class="bloc"><h3>Députés européens</h3><p>81 élus sur une circonscription unique pour toute la France.</p><a class="btn" href="#/annuaire?t=eurodepute">Voir les 81 députés européens →</a></div>
    ${src(`Sources : Répertoire national des élus (${META.maj}) · circonscriptions : Ministère de l'Intérieur (table 2017, communes nouvelles via le COG 2026) · cantons : INSEE, COG 2026`)}`;
}

/* ---------- annuaire ---------- */

async function annuaire(qs, j) {
  setTab("annuaire");
  const p = new URLSearchParams(qs || "");
  const st = {q: p.get("q") || "", t: p.get("t") || "", d: p.get("d") || "", g: p.get("g") || "", l: p.get("l") || ""};
  const opt = (v, t, cur) => `<option value="${esc(v)}" ${v === cur ? "selected" : ""}>${esc(t)}</option>`;
  app.innerHTML = `<div class="lieu-h" style="margin-top:26px"><h1>Qui est qui</h1></div>
    <p class="muted">Tout le monde, de A à Z. Filtrez par fonction, département ou nom ; touchez pour ouvrir la fiche.</p>
    <div class="filtres">
      <input id="q" placeholder="Nom ou prénom et nom" value="${esc(st.q)}" autocomplete="off">
      <select id="t">${opt("", "Toutes les fonctions", st.t)}${Object.entries(T).map(([k, v]) => opt(k, v[0], st.t)).join("")}</select>
      <select id="d">${opt("", "Tous les départements", st.d)}${Object.entries(META.deps || {}).sort((a, b) => a[0].localeCompare(b[0]))
        .map(([k, v]) => opt(k, `${k} · ${v.nom}`, st.d)).join("")}</select>
      <select id="g">${opt("", "Tous les groupes", st.g)}${(META.groupes || []).map(g => opt(g, g, st.g)).join("")}</select>
    </div><div id="res"></div>`;
  const res = document.getElementById("res");
  let attente;
  const go = async () => {
    const k = ++jeton; j = k;
    res.innerHTML = `<p class="charge">Chargement…</p>`;
    const q = norm(st.q), match = e => !q || norm(e.prenom + e.nom).includes(q) || norm(e.nom + e.prenom).includes(q);
    let l;
    if (st.d) {
      const [d] = await chargeDep(st.d);
      l = unique(d.elus.map(deLeger).filter(e => !st.t || e.t === st.t))
        .map(e => ({...e, lieu: COMMUNAL.has(e.t) ? (d.byCode[e.lc] || [, ""])[1] : e.t === "cd" ? `canton ${d.cantons[e.lc] || ""}` : depNom(st.d)}));
      if (st.g) l = l.filter(e => BY[e.slug]?.groupe === st.g);
    } else if (NATIONAL.has(st.t) || st.g) {
      l = DATA.filter(p => (!st.t || p.chambre === st.t) && (!st.g || p.groupe === st.g)).map(deNat);
    } else if (st.t) {
      res.innerHTML = `<p class="vide">Choisissez un département pour lister les ${esc(T[st.t][0].toLowerCase())} (il y en a ${nf(META.counts[st.t])} en France).</p>`;
      return;
    } else if (q.length >= 2 || st.l) {
      const lettres = st.l ? [st.l] : [...new Set(st.q.trim().split(/\s+/).map(w => (norm(w)[0] || "").toUpperCase()).filter(Boolean))].slice(0, 3);
      const fichiers = await Promise.all(lettres.map(L => get(`n/${L}.json`).catch(() => [])));
      l = fichiers.flat().map(deIndex);
    } else {
      const idx = await get("n/index.json");
      if (k !== jeton) return;
      res.innerHTML = `<div class="az-nav">${Object.keys(idx).map(L => `<a href="#/annuaire?l=${L}">${L}</a>`).join("")}</div>` +
        Object.entries(idx).map(([L, [n, top]]) => `<div class="az-l">${L}</div>${visages(top.map(deIndex))}
          <a class="plus" href="#/annuaire?l=${L}">Voir les ${nf(n)} noms en ${L} →</a>`).join("");
      return;
    }
    if (k !== jeton) return;
    l = l.filter(match);
    az(res, l);
  };
  const maj = (cle, v) => { st[cle] = v; if (cle !== "l") st.l = "";
    history.replaceState(null, "", "#/annuaire?" + new URLSearchParams(Object.entries(st).filter(([, x]) => x)));
    clearTimeout(attente); attente = setTimeout(go, cle === "q" ? 250 : 0); };
  ["q", "t", "d", "g"].forEach(id => document.getElementById(id).addEventListener(id === "q" ? "input" : "change", e => maj(id, e.target.value)));
  go();
}

/* ---------- fiche ---------- */

async function personne(shard, slug) {
  if (shard === "fr") return BY[slug];
  const url = shard === "etr" ? "d/etr.json" : shard.startsWith("d") ? `d/${shard.slice(1)}.json` : `c/${shard}.json`;
  const data = await get(url);
  return (Array.isArray(data) ? data : data.fiches).find(p => p.slug === slug);
}
// Infographies : jauge 0–100 % (repère facultatif, ex. la médiane) ; section repliable avec un compteur.
const jauge = (pct, titre, detail, repere) => `<div class="jauge"><div class="jauge-t"><b class="num">${pct} %</b><span>${titre}</span></div>
  <div class="jauge-b" role="img" aria-label="${pct} %${repere != null ? `, repère à ${repere} %` : ""}"><i style="width:${pct}%"></i>${repere != null
    ? `<em style="left:${repere}%"></em>` : ""}</div><small>${detail}</small></div>`;
const pli = (titre, n, corps, ouvert = false) => `<details class="pli"${ouvert ? " open" : ""}><summary><span>${titre}</span><span class="n">${n}</span></summary>${corps}</details>`;
// Pages de lieu : résumé en puces, parité (repère à 50 %), barres comparées, listes longues repliées sur mobile.
const lienNom = e => `<a href="#/p/${e.shard}/${e.slug}">${esc(e.prenom)} ${esc(e.nom)}</a>`;
const noms = l => l.map(lienNom).join(", ");
const large = () => matchMedia("(min-width:861px)").matches;
const enBref = l => `<div class="enbref"><h2>En bref</h2><ul>${l.filter(Boolean).map(x => `<li>${x}</li>`).join("")}</ul></div>`;
const parite = (l, quoi) => { const n = l.length, f = l.filter(e => e.sexe === "F").length;
  return n ? jauge(Math.round(100 * f / n), `de femmes ${quoi}`, `${nf(f)} femmes, ${nf(n - f)} hommes · trait : parité`, 50) : ""; };
const barresCarte = (titre, rows, aff = nf, note = "") => { const m = Math.max(...rows.map(r => r[1]), 1);
  return `<div class="jauge"><div class="jauge-t"><span>${titre}</span></div>${rows.map(([l, x, c]) => `<div class="barre-p"><span>${l}</span>
    <div><i style="width:${100 * x / m}%;background:${c || "var(--accent)"}"></i></div><b class="num">${aff(x)}</b></div>`).join("")}${note ? `<small>${note}</small>` : ""}</div>`; };
// Élections : pourcentage à une décimale, barre « sur 100 inscrits » (segments + légende).
const part = (a, b) => b ? Math.round(1000 * a / b) / 10 : 0;
const fpc = x => `${x.toLocaleString("fr-FR")} %`;
const TOUR = t => t === 1 ? "1er tour" : "2nd tour";
const surCent = segs => `<div class="cumul-b">${segs.map(([l, x, c]) => `<i style="width:${x}%;background:${c}" title="${l}"></i>`).join("")}</div>
  <ul class="legende">${segs.map(([l, x, c]) => `<li><i style="background:${c}"></i>${l} <b class="num">${fpc(x)}</b></li>`).join("")}</ul>`;
// Scrutin de liste (municipales, régionales) : participation, sièges par liste. Listes sans élu jamais affichées.
const coulListe = i => `var(--p${Math.min(i + 1, 5)})`;  // ordre du nombre de sièges, jamais le parti
function scrutinListes(titre, r, de) {
  const sieges = r.listes.reduce((t, l) => t + l[2], 0);
  return `<section class="sec"><h2>${titre}</h2>
    <div class="jauges">${jauge(Math.round(part(r.votants, r.inscrits)), "de participation", `${TOUR(r.tour)} · ${nf(r.votants)} votants sur ${nf(r.inscrits)} inscrits`)}</div>
    <h3 class="mesure">Les ${nf(sieges)} sièges ${de}</h3>
    <div class="cumul-b">${r.listes.map((l, i) => `<i style="width:${100 * l[2] / sieges}%;background:${coulListe(i)}" title="${esc(l[0])}"></i>`).join("")}</div>
    ${r.listes.map((l, i) => `<div class="kv"><b><i class="puce-c" style="background:${coulListe(i)}"></i>${esc(l[0])}</b>
      <span><b class="num">${l[2]}</b> siège${l[2] > 1 ? "s" : ""} · ${fpc(part(l[1], r.exprimes))} des suffrages exprimés${l[3] ? ` · ${l[3]} au conseil communautaire` : ""}</span></div>`).join("")}
    ${src("Source : Ministère de l'Intérieur, résultats officiels (data.gouv.fr). Seules les listes ayant obtenu au moins un siège sont affichées. Couleurs dans l'ordre du nombre de sièges, sans lien avec un parti.")}</section>`;
}
const badge = items => items.map(([c, ic, t, d]) => `<div class="badge-item"><span class="ic ${c}">${ic}</span>
  <span><b>${t}</b><br><span class="muted">${d}</span></span></div>`).join("");
function lieuHref(m) {
  const [t, , lc, , dep] = m;
  if (COMMUNAL.has(t)) return `#/c/${lc}`;
  if (t === "cr") return `#/r/${lc}`;
  if (["cd", "ma", "depute", "senateur"].includes(t) && dep && dep !== "fr") return `#/d/${dep}`;
  return "";
}

async function fiche(shard, slug, j) {
  setTab("");
  const p = await personne(shard, slug).catch(() => null);
  if (!encore(j)) return;
  if (!p) { app.innerHTML = `<p class="vide">Fiche introuvable. <a href="#/annuaire" style="color:var(--accent)">Retour à l'annuaire</a></p>`; return; }
  const m0 = p.m[0], lvl = lvlOf(m0[0]), nat = shard === "fr";
  const age = ageOf(p.naissance), anc = (Date.now() - new Date(m0[6] || m0[5])) / 3.15576e10;
  const v = p.votes, hi = p.interets, ex = p.chambre === "president" || p.chambre === "gouvernement";
  const ind = p.ind || [];
  const mandats = p.m.map((m, i) => { const h = lieuHref(m);
    return `<div class="mandat lvl-${lvlOf(m[0])}"><small>En exercice · ${esc(INSTIT[m[0]])}</small>
      <b>${esc(m[1])}</b><small>${h ? `<a href="${h}">${esc(m[3])}</a>` : esc(m[3])}${m[6] || m[5] ? ` · depuis le ${fdate(m[6] || m[5])}` : ""}</small>
      ${ind[i] ? `<small>Plafond légal d'indemnité : ${eur(ind[i])} brut / mois</small>` : ""}</div>`; }).join("");
  const plafond = ind.find(Boolean);
  const pc = p.presence_com, pcn = pc ? pc[0] + pc[1] + pc[2] : 0;
  const mois = p.debut ? Math.floor((Date.now() - new Date(p.debut)) / 2.6298e9) : 0;
  const percu = p.indemnite != null && mois > 0 && p.chambre !== "eurodepute" ? mois * p.indemnite : 0;
  // Plafond de cumul : 1,5 × l'indemnité parlementaire de base (CGCT L2123-20, L3123-18, L4135-18) ;
  // un parlementaire n'y ajoute que la moitié de cette base (ordonnance n° 58-1210, art. 4).
  const montants = ind.filter(Boolean), parl = p.chambre === "depute" || p.chambre === "senateur";
  const nCumul = montants.length + (parl ? 1 : 0);
  const cumul = META.base_parl && !ex && p.chambre !== "eurodepute" && nCumul >= 2 ? (() => {
    const somme = montants.reduce((a, b) => a + b, 0) + (parl ? p.indemnite : 0);
    const cap = parl ? p.indemnite + META.base_parl / 2 : META.base_parl * 1.5;
    return {somme, cap, max: Math.min(somme, cap), partiel: p.m.length > nCumul}; })() : null;
  const tuiles = [
    p.indemnite != null ? [`${nf(p.indemnite)} €`, `${ex ? "rémunération" : "indemnité"} brute / mois`, `${nf(p.indemnite * 12)} € / an`]
      : plafond ? [eur(plafond), "plafond légal d'indemnité / mois", "montant réellement voté non publié en open data"] : null,
    !isNaN(anc) ? [ans(Math.round(anc * 10) / 10), "dans le mandat principal", `depuis le ${fdate(m0[6] || m0[5])}`] : null,
    age != null ? [`${age} ans`, "âge", `né${p.sexe === "F" ? "e" : ""} le ${fdate(p.naissance)}`] : null,
    p.commissions?.length ? [p.commissions.length, "commissions et organes", "en cours"] : null,
    percu ? [`≈ ${eur(percu)}`, `${ex ? "rémunération brute perçue" : "indemnités brutes perçues"} dans ce mandat`, `estimation : ${nf(mois)} mois au montant actuel`] : null,
  ].filter(Boolean).map(([a, b, c]) => `<div class="tuile"><span class="big num">${a}</span><span>${b}</span><small>${c}</small></div>`).join("");
  const F = p.sexe === "F" ? "e" : "", pcPct = pcn ? Math.round(100 * pc[0] / pcn) : 0, med = META.presence_com_mediane;
  const jauges = [
    v ? jauge(v.participation, "participation aux scrutins publics", `${nf(v.exprimes)} votes exprimés sur ${nf(v.scrutins)} scrutins`) : "",
    v?.conforme != null ? jauge(v.conforme, "votes comme la majorité de son groupe", `sur ${nf(v.conforme_n)} votes exprimés`) : "",
    pcn ? jauge(pcPct, "présence en réunion de commission", `${nf(pc[0])} réunions sur ${nf(pcn)} · trait : médiane de l'Assemblée (${med} %)`, med) : "",
  ].join("");
  // Plafonds cumulés : un segment par mandat (couleur du niveau), trait au plafond légal de cumul.
  const parts = cumul ? [...(parl ? [[m0[1], p.indemnite, lvl]] : []), ...p.m.map((m, i) => [m[1], ind[i], lvlOf(m[0])]).filter(x => x[1])] : [];
  const echelle = cumul ? Math.max(cumul.somme, cumul.cap) : 1;
  const cumulBar = cumul ? `<div class="cumul"><div class="jauge-t"><b class="num">${eur(cumul.max)}</b><span>maximum légal par mois, toutes fonctions</span></div>
    <div class="cumul-b">${parts.map(([l, x, lv]) => `<i style="width:${100 * x / echelle}%;background:var(--${lv})" title="${esc(l)} : ${eur(x)}"></i>`).join("")}
      <em style="left:${100 * cumul.cap / echelle}%"></em></div>
    <ul class="legende">${parts.map(([l, x, lv]) => `<li><i style="background:var(--${lv})"></i>${esc(l)} <b class="num">${eur(x)}</b></li>`).join("")}
      <li><i class="trait"></i>plafond de cumul <b class="num">${eur(cumul.cap)}</b></li></ul>
    <small>${cumul.somme > cumul.cap ? `Somme des plafonds ${eur(cumul.somme)} : écrêtée au plafond de cumul.` : "Somme des plafonds sous le plafond de cumul."}${cumul.partiel ? " Hors mandats sans barème vérifié." : ""}</small></div>` : "";
  const el = p.election, cdM = p.m.find(m => m[0] === "cd");
  const electionSec = el ? `<section class="sec"><h2>Son élection</h2>${sonElection(p, el, F)}</section>` : "";
  const E = META.europeennes, eurL = el?.europe ? E?.listes.find(l => l[3] === el.panneau) : null;
  const a0 = p.activite, debut0 = m0[6] || m0[5];
  const bref = [
    `${esc(m0[1])} · ${esc(m0[3])}${debut0 ? `, depuis le ${fdate(debut0)}` : ""}`,
    p.m.length > 1 ? `Aussi : ${p.m.slice(1).map(m => esc(m[1]) + (m[3] ? ` (${esc(m[3])})` : "")).join(", ")}` : "",
    p.indemnite != null ? `${ex ? "Rémunération" : "Indemnité"} : <b>${eur(p.indemnite)}</b> brut par mois` : plafond ? `Indemnité : au plus <b>${eur(plafond)}</b> brut par mois (plafond légal)` : "",
    el?.elu ? `Élu${F} en 2024 au ${TOUR(el.tour)} avec <b>${fpc(part(el.elu[2], el.exprimes))}</b> des suffrages exprimés` : el?.autre ? "Siège obtenu après les législatives de 2024 (élection partielle ou remplacement)" : "",
    el?.annee ? `Élu${F} en septembre ${el.annee} par les grands électeurs${el.mode === "liste" ? ` sur la liste « ${esc(el.liste)} »` : ` avec <b>${fpc(part(el.voix, el.exprimes))}</b> des suffrages exprimés`}` : "",
    eurL ? (el.ordre > eurL[2] ? `Entré${F} au Parlement européen par remplacement (liste « ${esc(eurL[0])} », position ${el.ordre})`
      : `Élu${F} le 9 juin 2024 sur la liste « ${esc(eurL[0])} » (position ${el.ordre})`) : "",
    v?.participation != null ? `Vote dans <b>${v.participation} %</b> des scrutins publics${v.conforme != null ? ` ; comme la majorité de son groupe <b>${v.conforme} %</b> du temps` : ""}` : "",
    pcn ? `Présent${F} à <b>${pcPct} %</b> des réunions de commission (médiane : ${med} %)` : "",
    a0 && (a0.propositions || a0.amendements) ? `${nf(a0.propositions || 0)} proposition${a0.propositions > 1 ? "s" : ""} déposée${a0.propositions > 1 ? "s" : ""}${a0.lois ? `, dont <b>${a0.lois} devenue${a0.lois > 1 ? "s" : ""} loi${a0.lois > 1 ? "s" : ""}</b>` : ""} · ${nf(a0.amendements || 0)} amendements` : "",
    p.hatvp ? `Déclaration d'intérêts : résumé et PDF officiel plus bas` : hi?.derniere ? `Déclaration d'intérêts publiée le ${fdate(hi.derniere)}` : "",
  ].filter(Boolean);
  const votesSec = v ? `<section class="sec"><h2>Votes à l'Assemblée — 17e législature</h2>
    <div class="votebar"><span class="vp" style="flex:${v.pour}"></span><span class="vc" style="flex:${v.contre}"></span><span class="va" style="flex:${v.abstention}"></span></div>
    <div class="votelegend"><span><i class="vp"></i><b class="num">${nf(v.pour)}</b> pour</span><span><i class="vc"></i><b class="num">${nf(v.contre)}</b> contre</span>
      <span><i class="va"></i><b class="num">${nf(v.abstention)}</b> abstention</span><span><b class="num">${nf(v.nonvotant)}</b> scrutins sans vote exprimé</span></div>
    ${p.votes_detail ? `<h3 style="margin:22px 0 4px">Comment ${p.sexe === "F" ? "elle" : "il"} a voté, scrutin par scrutin</h3>
      <div id="votes-detail"><button class="btn" id="voir-votes">Afficher chaque vote (${nf(v.scrutins)})</button></div>` : ""}
    ${src("Participation aux scrutins publics — ne mesure pas la présence physique. « Comme la majorité de son groupe » : l'Assemblée publie la position majoritaire de chaque groupe, pas sa consigne. Source : scrutins de l'Assemblée nationale, open data.")}</section>` : "";
  const a = p.activite;
  const pl = (n, s, pluriel = s + "s") => `${nf(n)} ${n > 1 ? pluriel : s}`;
  const activiteSec = a ? `<section class="sec"><h2>Activité à l'Assemblée — 17e législature</h2>
    <div class="tuiles">${[
      [a.propositions || 0, "propositions déposées", a.lois ? `dont ${pl(a.lois, "devenue loi", "devenues lois")}` : "en tant qu'auteur"],
      [a.cosignees || 0, "propositions cosignées", "en soutien d'un autre auteur"],
      [a.amendements || 0, "amendements déposés", `dont ${pl(a.amendements_adoptes || 0, "adopté")}`],
      [a.amendements_cosignes || 0, "amendements cosignés", "en soutien d'un autre auteur"],
      [a.qe || 0, "questions écrites", a.qe ? `dont ${pl(a.qe_repondues || 0, "avec réponse", "avec réponse")}` : "au gouvernement"],
      [(a.qag || 0) + (a.qo || 0), "questions orales", `dont ${nf(a.qag || 0)} au gouvernement`],
    ].map(([x, b, c]) => `<div class="tuile"><span class="big num">${nf(x)}</span><span>${b}</span><small>${c}</small></div>`).join("")}</div>
    <div id="activite-detail"></div>
    ${src("Source : Assemblée nationale, open data (dossiers législatifs, amendements, questions). Un amendement « adopté » l'est en commission ou en séance.")}</section>` : "";
  const commissionsSec = p.commissions?.length ? `<section class="sec"><h2>Commissions et organes</h2>
    ${p.commissions.map(([n, f, d]) => `<div class="kv"><b>${esc(n)}</b><span>${esc(f)}${d ? ` · depuis le ${fdate(d)}` : ""}</span></div>`).join("")}
    ${src(`Source : ${p.chambre === "senateur" ? "Sénat, data.senat.fr" : "Assemblée nationale, open data"} · organes en cours`)}</section>` : "";
  const contactSec = `<section class="sec"><h2>Données et contact</h2>
    <div class="kv"><b>Naissance</b><span>${p.naissance ? fdate(p.naissance) : "—"}${p.lieu_naissance ? ` · ${esc(p.lieu_naissance)}` : ""}</span></div>
    <div class="kv"><b>Profession déclarée</b><span>${esc(p.profession || "—")}</span></div>
    ${p.parti_national ? `<div class="kv"><b>Parti national</b><span>${esc(p.parti_national)}</span></div>` : ""}
    ${p.email ? `<div class="kv"><b>E-mail professionnel</b><span><a href="mailto:${esc(p.email)}" style="color:var(--accent)">${esc(p.email)}</a></span></div>` : ""}
    ${p.page ? `<div class="kv"><b>Page officielle</b><span><a href="${esc(p.page)}" target="_blank" rel="noopener" style="color:var(--accent)">${esc(new URL(p.page).hostname)} ↗</a></span></div>` : ""}
    ${src("Coordonnées professionnelles publiées par l'institution. Aucune donnée privée.")}</section>`;
  const interetsSec = p.hatvp || hi?.url ? `<section class="sec"><h2>Déclaration d'intérêts</h2>
    <div id="hatvp">${p.hatvp ? `<p class="charge">Chargement de la déclaration…</p>` : `<p class="muted">Aucune déclaration en données structurées dans l'open data de la HATVP.</p>
      ${hi.pdfs?.length ? listePdf(hi.pdfs) : ""}`}</div>
    ${hi?.url ? `<p><a class="btn ghost" href="${esc(hi.url)}" target="_blank" rel="noopener">Sa page sur hatvp.fr ↗</a></p>` : ""}
    ${src("Reprise de l'open data de la HATVP : seules les informations sur la personne elle-même sont affichées. L'activité du conjoint et des collaborateurs figure dans le PDF officiel. Les déclarations de patrimoine ne sont jamais reprises (loi n° 2013-907).")}</section>` : "";
  const items = [
    nat && ex ? ["ok", "✓", "État civil et fonction", "publiés — Assemblée nationale (référentiel des acteurs) et HATVP"]
      : p.chambre === "depute" || p.chambre === "senateur"
        ? ["ok", "✓", "État civil et mandat", `publiés — ${p.chambre === "depute" ? "Assemblée nationale" : "Sénat"}${p.m.length > 1 ? " ; mandats locaux : Répertoire national des élus" : ""}`]
      : ["ok", "✓", "État civil et mandats", "publiés — Répertoire national des élus, Ministère de l'Intérieur"],
    ...(nat && !ex ? [p.groupe ? ["ok", "✓", "Groupe politique", `publié — ${{depute: "Assemblée nationale", senateur: "Sénat", eurodepute: "Parlement européen"}[p.chambre]}`]
      : ["soon", "·", "Groupe politique", "non rapproché automatiquement"]] : []),
    ...(p.photo ? [["ok", "✓", "Photo", `${esc(p.photo_credit)}`]] : []),
    p.indemnite != null ? [p.chambre === "eurodepute" ? "soon" : "ok", p.chambre === "eurodepute" ? "·" : "✓", ex ? "Rémunération" : "Indemnité", esc(p.indemnite_source)]
      : plafond ? ["ok", "✓", "Plafond légal d'indemnité", "calculé selon le CGCT et la population (INSEE) ; le montant réellement voté par l'assemblée locale n'est pas publié en open data"]
      : ["soon", "·", "Indemnité", "pas de barème vérifié pour ce mandat (intercommunalité, conseil régional…)"],
    ...(percu || cumul ? [["ok", "✓", percu ? "Montant perçu depuis le début du mandat" : "Plafond de cumul",
      `${percu ? "estimation : nombre de mois × montant actuel (les barèmes antérieurs étaient un peu plus bas), hors frais de mandat" : ""}${percu && cumul ? " ; " : ""}${cumul
        ? `plafond de cumul : 1,5 × l'indemnité parlementaire de base (${eur(META.base_parl)}), CGCT art. L2123-20${parl ? " et ordonnance n° 58-1210, art. 4" : ""}` : ""}`]] : []),
    ...(p.chambre === "depute" ? [pcn ? ["ok", "✓", "Présence en commission", "relevés de présence publiés — Assemblée nationale, open data (agenda)"]
      : ["soon", "·", "Présence en commission", "aucun relevé publié pour ce député"]] : []),
    ex ? ["soon", "—", "Votes et groupe parlementaire", "non applicables : fonction exécutive"]
      : p.chambre === "depute" ? (v ? ["ok", "✓", "Votes (scrutins publics)", "publiés — Assemblée nationale, open data"] : ["soon", "·", "Votes", "non rapprochés automatiquement"])
      : p.chambre === "senateur" ? ["soon", "·", "Votes nominatifs", "publiés sur senat.fr (pages web, pas d'open data) — à brancher"]
      : ["soon", "·", "Votes et présence", "les conseils locaux publient rarement leurs votes en open data"],
    p.hatvp ? ["ok", "✓", "Déclaration d'intérêts", "contenu repris de l'open data HATVP ; lien vers le PDF officiel sur hatvp.fr"]
      : hi?.derniere ? ["ok", "✓", "Déclaration d'intérêts", `publiée — HATVP, le ${fdate(hi.derniere)}`]
      : nat ? ["soon", "·", "Déclaration d'intérêts", hi ? `HATVP — ${esc(hi.statut.toLowerCase())}` : "absente de l'open data HATVP pour ce mandat"]
      : ["soon", "·", "Déclaration d'intérêts", "seuls certains élus locaux y sont soumis (HATVP) — à brancher"],
    ...(el ? [["ok", "✓", "Résultat de son élection", el.autre ? "arrivé après les législatives de 2024 : résultat non repris"
      : `${el.elu ? "législatives 2024" : el.annee ? `sénatoriales ${el.annee}` : "européennes 2024"} — Ministère de l'Intérieur, résultats officiels`]] : []),
    patrimoine(p),
  ];
  app.innerHTML = `<div class="ariane">${m0[4] && m0[4] !== "fr" && m0[4] !== "etr" ? `<a href="#/d/${m0[4]}">‹ ${esc(depNom(m0[4]))}</a>` : `<a href="#/annuaire">‹ Qui est qui</a>`}</div>
    <article class="fiche lvl-${lvl}" style="--lvl:var(--${lvl})">
      <div class="fiche-tete">${p.photo ? `<figure class="photo"><img src="${esc(p.photo)}" alt="Photo de ${esc(p.prenom)} ${esc(p.nom)}">
          <figcaption>Photo : ${p.photo_source ? `<a href="${esc(p.photo_source)}" target="_blank" rel="noopener">${esc(p.photo_credit)}</a>`
            : esc((p.photo_credit || "").replace(/ \(.*\)$/, ""))}</figcaption></figure>`
        : `<div class="photo" aria-hidden="true">${esc(initiales(p.prenom, p.nom))}</div>`}
        <div><div class="kicker"><span class="dot"></span>${esc(m0[1])} · ${esc(m0[3])} · en exercice</div>
          <h1>${esc(p.prenom)} ${esc(p.nom)}</h1>
          <p class="ligne">${[p.groupe_label || p.groupe, age != null ? `${age} ans` : "", p.profession].filter(Boolean).map(esc).join(" · ")}</p>
          <div class="pastilles"><span class="pastille">${p.m.length} mandat${p.m.length > 1 ? "s" : ""} en cours</span>
            <button class="btn ghost suivre" data-suivi="${esc(shard)}/${esc(slug)}" aria-pressed="false">☆ <span>Suivre</span></button></div></div></div>
      <div class="enbref"><h2>En bref</h2><ul>${bref.map(b => `<li>${b}</li>`).join("")}</ul></div>
      <div class="mandats">${mandats}</div>
      <div class="tuiles">${tuiles}</div>
      ${jauges ? `<div class="jauges">${jauges}</div>` : ""}${cumulBar}
      ${src(`Source : ${{depute: "Assemblée nationale (référentiel des acteurs, scrutins)", senateur: "Sénat (data.senat.fr)",
        eurodepute: "Répertoire national des élus, Parlement européen", president: "Assemblée nationale et HATVP",
        gouvernement: "Assemblée nationale et HATVP"}[p.chambre] || `Répertoire national des élus (${META.maj})`}${p.m.length > 1 && nat ? ` · mandats locaux : Répertoire national des élus (${META.maj})` : ""}`)}
    </article>
    <div class="actions-lieu"><a class="btn" href="#/comparer?p=${shard}/${slug}">Comparer avec une autre personne</a>
      <a class="btn ghost" href="#/signaler?p=${shard}/${slug}">Signaler une erreur</a>
      <a class="btn ghost" href="#/reponse?p=${shard}/${slug}">Droit de réponse</a></div>
    ${electionSec}${cdM ? `<div id="election-cd"></div>` : ""}${votesSec}${activiteSec}${commissionsSec}${interetsSec}${contactSec}
    <section class="sec"><h2>Ce qui est publié, ce qui ne l'est pas</h2>${badge(items)}</section>`;
  document.getElementById("voir-votes")?.addEventListener("click", () => detailVotes(slug));
  if (p.activite_detail) detailActivite(slug, p).catch(() => {});
  if (cdM) electionCd(p, cdM).catch(() => {});
  boutonSuivi(`${shard}/${slug}`, p);
  if (p.hatvp) detailHatvp(p).catch(() => { const b = document.getElementById("hatvp"); if (b) b.innerHTML = `<p class="vide">Déclaration indisponible.</p>`; });
  window.scrollTo(0, 0);
}

const TYPE_DI = {di: "Déclaration d'intérêts", dia: "Déclaration d'intérêts et d'activités", dim: "Déclaration d'intérêts modificative",
  diam: "Déclaration d'intérêts et d'activités modificative"};
const HATVP_PDF = "https://www.hatvp.fr/livraison/dossiers/";  // les PDF restent chez la HATVP
const listePdf = l => pli("Toutes ses déclarations", l.length, l.map(([d, t, f]) =>
  `<div class="kv"><b class="num">${d ? fdate(d) : "—"}</b><span>${TYPE_DI[t] || "Déclaration d'intérêts"}
    <a class="loi" href="${HATVP_PDF}${esc(f)}" target="_blank" rel="noopener">PDF officiel sur hatvp.fr ↗</a></span></div>`).join(""));

// Déclaration d'intérêts la plus récente, reprise de l'open data HATVP (site/h/<id>.json).
async function detailHatvp(p) {
  const l = await get(`h/${p.hatvp}.json`), box = document.getElementById("hatvp");
  if (!box) return;
  const e = l[0], c = e.c, type = t => t.toLowerCase();
  const per = (a, b) => a || b ? `${a || "?"} – ${b || "en cours"}` : "";
  const montant = x => /^\d+$/.test(x) ? eur(+x) : x;
  const remu = (x, mot = "rémunération") => x && !/^0\s*€?$/.test(x) ? `${mot} ${x}` : "";
  const ligne = (titre, ...det) => `<div class="kv"><b>${esc(titre || "—")}</b><span>${det.filter(Boolean).map(esc).join(" · ") || "—"}</span></div>`;
  const S = [
    ["pro", "Activités professionnelles des cinq dernières années", x => ligne(x[0], x[1], per(x[2], x[3]), remu(x[4]), x[5])],
    ["consultant", "Activités de consultant", x => ligne(x[0], x[1], per(x[2], x[3]), remu(x[4]), x[5])],
    ["dirigeant", "Organes dirigeants d'un organisme public ou privé", x => ligne(x[0], x[1], per(x[2], x[3]), remu(x[4]), x[5])],
    ["participations", "Participations financières dans des sociétés", x => ligne(x[0], x[1] && `valeur déclarée ${montant(x[1])}`,
      x[2] && `${/^\d+$/.test(x[2]) ? nf(+x[2]) : x[2]} parts`, x[3] && `capital détenu : ${x[3]}`, remu(x[4]), x[5])],
    ["benevole", "Fonctions bénévoles", x => ligne(x[0], x[1], remu(x[2]), x[3])],
    ["mandats", "Mandats électifs", x => ligne(x[0], per(x[1], x[2]), remu(x[3], "indemnités"), x[4])],
  ];
  const tous = [...l.filter(x => x.pdf).map(x => [x.d, type(x.t) + (x.mod ? "m" : ""), x.pdf]),
    ...(p.interets?.pdfs || [])].filter((x, i, a) => a.findIndex(y => y[2] === x[2]) === i).sort((a, b) => b[0].localeCompare(a[0]));
  box.innerHTML = `<div class="encart"><b>${TYPE_DI[type(e.t) + (e.mod ? "m" : "")]}</b> déposée le ${fdate(e.d)}${e.q ? `, au titre de : ${esc(e.q)}` : ""}
      ${e.pdf ? `<p style="margin:10px 0 0"><a class="btn" href="${HATVP_PDF}${esc(e.pdf)}" target="_blank" rel="noopener">Télécharger le PDF officiel sur hatvp.fr ↗</a></p>` : ""}</div>
    ${S.map(([k, t, f]) => pli(t, c[k]?.length || "néant", c[k]?.length ? c[k].map(f).join("") : `<p class="muted">Rien de déclaré.</p>`)).join("")}
    ${c.observations?.length ? pli("Observations", c.observations.length, c.observations.map(o => `<p>${esc(o)}</p>`).join("")) : ""}
    ${tous.length > 1 ? listePdf(tous) : ""}`;
}

// Déclaration de patrimoine : jamais reprise ici (loi n° 2013-907, art. 26 III) ; on dit où la consulter selon la fonction.
function patrimoine(p) {
  const d = p.interets?.patrimoine, dispo = d ? ` Disponible depuis le ${fdate(d)}.` : " Pas encore signalée comme disponible par la HATVP.";
  const lieu = {"099": "à la préfecture de Paris (Français établis hors de France)", "988": "au haut-commissariat en Nouvelle-Calédonie",
    "987": "au haut-commissariat en Polynésie française"}[p.dep] || (/^97[5-8]|^986/.test(p.dep || "") ? "à la préfecture de la collectivité"
    : `à la préfecture ${p.departement ? `du département d'élection (${esc(p.departement)})` : "du département d'élection"}`);
  const interdit = "Sa publication est interdite (loi n° 2013-907, art. 26 : peines de l'article 226-1 du code pénal).";
  if (p.chambre === "president" || p.chambre === "gouvernement")
    return ["soon", "↗", "Déclaration de patrimoine", `publiée par la HATVP sur ${p.interets?.url ? `<a href="${esc(p.interets.url)}" target="_blank" rel="noopener">hatvp.fr ↗</a>` : "hatvp.fr"}
      (loi n° 2013-907, art. 5). Non reprise ici : la loi n'autorise la réutilisation que des déclarations d'intérêts.`];
  if (p.chambre === "depute" || p.chambre === "senateur")
    return ["soon", "⌂", "Déclaration de patrimoine", `consultable ${lieu}, par tout électeur inscrit sur les listes électorales, aux seules fins de consultation
      (code électoral, art. LO 135-2${p.chambre === "senateur" ? " et LO 296" : ""}).${dispo} ${interdit}`];
  if (p.chambre === "eurodepute")
    return ["soon", "⌂", "Déclaration de patrimoine", `consultable dans toutes les préfectures, par tout électeur inscrit sur les listes électorales
      (circonscription unique ; loi n° 2013-907, art. 12).${dispo} ${interdit}`];
  return ["no", "✕", "Déclaration de patrimoine", "ni publiée ni consultable pour un élu local : seule la HATVP la contrôle, pour les élus qui y sont soumis (loi n° 2013-907, art. 11 et 12)."];
}

// Section « Son élection » : législatives 2024 (député), sénatoriales 2023/2026, européennes 2024. Jamais d'autre candidat nommé.
function sonElection(p, el, F) {
  const pron = p.sexe === "F" ? "elle" : "lui", Il = p.sexe === "F" ? "Elle" : "Il";
  if (el.autre) return `<p>${Il} n'a pas été élu${F} aux législatives de 2024 dans cette circonscription : siège obtenu depuis
    (élection partielle ou remplacement), le ${fdate(p.debut)}.</p>`;
  if (el.elu) return `<div class="jauges">${jauge(Math.round(part(el.elu[2], el.exprimes)), "des suffrages exprimés", `${nf(el.elu[2])} voix sur ${nf(el.exprimes)} · ${TOUR(el.tour)} des législatives de 2024`)}
      ${jauge(Math.round(part(el.votants, el.inscrits)), "de participation", `${nf(el.votants)} votants sur ${nf(el.inscrits)} inscrits`)}</div>
    <h3 class="mesure">Sur 100 inscrits de la circonscription</h3>
    ${surCent([[`ont voté pour ${pron}`, part(el.elu[2], el.inscrits), "var(--national)"], ["pour un autre candidat", part(el.exprimes - el.elu[2], el.inscrits), "var(--muted)"],
      ["blanc ou nul", part(el.blancs + el.nuls, el.inscrits), "#b9b3a6"], ["abstention", part(el.inscrits - el.votants, el.inscrits), "var(--line)"]])}
    ${src("Source : Ministère de l'Intérieur, résultats définitifs des législatives des 30 juin et 7 juillet 2024 (data.gouv.fr). Les autres candidats ne sont pas nommés.")}`;
  if (el.annee) return `<div class="jauges">${el.mode === "liste"
      ? jauge(Math.round(part(el.voix, el.exprimes)), "des suffrages exprimés pour sa liste", `liste « ${esc(el.liste)} » : ${el.sieges} siège${el.sieges > 1 ? "s" : ""} sur ${el.sieges_dep} · ${TOUR(el.tour)}`)
      : jauge(Math.round(part(el.voix, el.exprimes)), "des suffrages exprimés", `${nf(el.voix)} voix sur ${nf(el.exprimes)} · ${TOUR(el.tour)}`)}</div>
    <p>Élu${F} en septembre ${el.annee} ${el.mode === "liste" ? "au scrutin proportionnel" : "au scrutin majoritaire"} par les ${nf(el.inscrits)} grands électeurs
      du département, dont ${nf(el.votants)} ont voté.</p>
    ${src(`Source : Ministère de l'Intérieur, résultats des sénatoriales de ${el.annee} (data.gouv.fr). Les autres candidats et listes ne sont pas nommés.`)}`;
  const E = META.europeennes, l = E?.listes.find(x => x[3] === el.panneau);
  if (!l) return "";
  const sieges = E.listes.reduce((t, x) => t + x[2], 0);
  return `<div class="jauges">${jauge(Math.round(part(l[1], E.exprimes)), "des suffrages exprimés pour sa liste", `liste « ${esc(l[0])} » · ${l[2]} sièges sur ${sieges}`)}
      ${jauge(Math.round(part(E.votants, E.inscrits)), "de participation en France", `${nf(E.votants)} votants sur ${nf(E.inscrits)} inscrits`)}</div>
    <p>${el.ordre > l[2] ? `Candidat${F} le 9 juin 2024 en position ${el.ordre} sur la liste « ${esc(l[0])} », qui a obtenu ${l[2]} sièges :
      entré${F} au Parlement européen par remplacement.` : `Élu${F} le 9 juin 2024 sur la liste « ${esc(l[0])} », où ${p.sexe === "F" ? "elle" : "il"} figurait en position ${el.ordre}.`}</p>
    <h3 class="mesure">Les ${sieges} sièges français au Parlement européen</h3>
    <div class="cumul-b">${E.listes.map((x, i) => `<i style="width:${100 * x[2] / sieges}%;background:${coulListe(i)}" title="${esc(x[0])}"></i>`).join("")}</div>
    ${E.listes.map((x, i) => `<div class="kv"><b><i class="puce-c" style="background:${coulListe(i)}"></i>${esc(x[0])}${x[3] === el.panneau ? " · sa liste" : ""}</b>
      <span><b class="num">${x[2]}</b> sièges · ${fpc(part(x[1], E.exprimes))} des suffrages exprimés</span></div>`).join("")}
    ${src("Source : Ministère de l'Intérieur, résultats définitifs des européennes du 9 juin 2024 et liste des candidatures (data.gouv.fr). Seules les listes ayant obtenu des sièges sont affichées ; couleurs dans l'ordre du nombre de sièges, sans lien avec un parti.")}`;
}

// Conseiller départemental : résultat de son binôme en juin 2021, s'il en faisait partie.
async function electionCd(p, m) {
  const [d] = await chargeDep(m[4]), r = d.departementales?.[m[2]], box = document.getElementById("election-cd");
  if (!r || !box) return;
  box.innerHTML = `<section class="sec"><h2>Son élection</h2>${r.en_place.includes(`${p.shard}/${p.slug}`)
    ? `<div class="jauges">${jauge(Math.round(part(r.voix, r.exprimes)), "des suffrages exprimés", `pour son binôme · ${TOUR(r.tour)} des départementales de juin 2021`)}
        ${jauge(Math.round(part(r.votants, r.inscrits)), "de participation", `canton ${esc(m[3])} · ${nf(r.votants)} votants sur ${nf(r.inscrits)} inscrits`)}</div>
      <h3 class="mesure">Sur 100 inscrits du canton</h3>
      ${surCent([["ont voté pour le binôme", part(r.voix, r.inscrits), "var(--departement)"], ["pour un autre binôme", part(r.exprimes - r.voix, r.inscrits), "var(--muted)"],
        ["blanc ou nul", part(r.blancs + r.nuls, r.inscrits), "#b9b3a6"], ["abstention", part(r.inscrits - r.votants, r.inscrits), "var(--line)"]])}`
    : `<p>${p.sexe === "F" ? "Elle" : "Il"} ne faisait pas partie du binôme élu dans ce canton en juin 2021 : siège obtenu depuis (remplacement).</p>`}
    ${src("Source : Ministère de l'Intérieur, résultats officiels des départementales des 20 et 27 juin 2021 (data.gouv.fr). Les autres binômes ne sont pas nommés.")}</section>`;
}

async function detailActivite(slug, p) {
  const d = await get(`a/${slug}.json`), box = document.getElementById("activite-detail");
  if (!box) return;
  const props = d.propositions || [], qs = d.questions || [];
  box.innerHTML = `${props.length ? pli("Ses propositions", props.length, props.map(([date, type, titre, loi, url]) =>
      `<div class="kv"><b class="num">${fdate(date)}</b><span>${esc(titre)}<br><small class="muted">${esc(type)}</small>
        ${loi ? ` <a class="loi" href="${esc(url || "https://www.legifrance.gouv.fr")}" target="_blank" rel="noopener">Devenue la loi n° ${esc(loi)} ↗</a>` : ""}</span></div>`).join("")) : ""}
    ${qs.length ? pli("Ses dernières questions écrites", Math.min(qs.length, 12), qs.slice(0, 12).map(([date, rub, an, min, rep]) =>
      `<div class="kv"><b class="num">${date ? fdate(date) : "—"}</b><span>${esc(an || rub)}<br><small class="muted">${esc(rub)} · ${esc(min)} · ${rep ? "réponse publiée" : "sans réponse à ce jour"}</small></span></div>`).join("")) : ""}`;
}

// Chaque vote d'un député : table des scrutins (commune à tous) + positions de la personne.
async function detailVotes(slug) {
  const box = document.getElementById("votes-detail");
  box.innerHTML = `<p class="charge">Chargement des scrutins…</p>`;
  const [sc, pos] = await Promise.all([get("scrutins.json"), get(`v/${slug}.json`)]);
  const POS = ["Pour", "Contre", "Abstention", "Non-votant"], CLS = ["vp", "vc", "va", ""];
  const lignes = pos.map(([i, x, cf]) => ({s: sc[i], x, cf}));  // déjà du plus récent au plus ancien
  let n = 50, q = "";
  box.innerHTML = `<div class="filtres"><input id="vq" placeholder="Chercher dans les intitulés (ex. retraites, budget)"></div><div id="vl"></div>`;
  const dessine = () => {
    const l = q ? lignes.filter(e => norm(e.s[2]).includes(q)) : lignes;
    document.getElementById("vl").innerHTML = `<p class="compte">${nf(l.length)} scrutins</p>` + l.slice(0, n).map(({s, x, cf}) =>
      `<div class="vote"><span class="vd">${fdate(s[1])}</span><span class="vt">${esc(s[2][0].toUpperCase() + s[2].slice(1))}
        <small><a href="#/scrutin/${s[0]}">Scrutin n° ${s[0]}</a> · ${esc(s[3] || "")} · ${nf(s[4])} pour, ${nf(s[5])} contre</small></span>
        <span class="vpos"><b class="${CLS[x]}">${POS[x]}</b><small>${cf === 1 ? "comme la majorité de son groupe" : cf === 0 ? "autrement que la majorité de son groupe" : ""}</small></span></div>`).join("")
      + (l.length > n ? `<button class="plus" id="vplus">Afficher 50 de plus</button>` : "");
    document.getElementById("vplus")?.addEventListener("click", () => { n += 50; dessine(); });
  };
  document.getElementById("vq").addEventListener("input", e => { q = norm(e.target.value); n = 50; dessine(); });
  dessine();
}

/* ---------- comparer ---------- */

async function chercheNom(q) {  // annuaire par initiale : nom ou prénom + nom
  const lettres = [...new Set(q.trim().split(/\s+/).map(w => (norm(w)[0] || "").toUpperCase()).filter(Boolean))].slice(0, 3);
  const n = norm(q);
  return (await Promise.all(lettres.map(L => get(`n/${L}.json`).catch(() => [])))).flat().map(deIndex)
    .filter(e => norm(e.prenom + e.nom).includes(n) || norm(e.nom + e.prenom).includes(n));
}

async function comparer(qs, j) {
  setTab("comparer");
  const ids = (new URLSearchParams(qs || "").get("p") || "").split(",").filter(Boolean).slice(0, 5);
  const gens = (await Promise.all(ids.map(id => { const [s, ...r] = id.split("/");
    return personne(s, r.join("/")).then(p => p && {...p, _id: id}).catch(() => null); }))).filter(Boolean);
  if (!encore(j)) return;
  const url = l => `#/comparer?p=${l.join(",")}`;
  const v = p => p.votes || {};
  const lignes = [
    ["Fonction principale", p => `${esc(p.m[0][1])}<br><small class="muted">${esc(p.m[0][3])}</small>`],
    ["Mandats en cours", p => p.m.length],
    ["Groupe politique", p => esc(p.groupe_label || p.groupe || "") || "—"],
    ["Âge", p => ageOf(p.naissance) ?? "—"],
    ["Dans le mandat principal depuis", p => (p.m[0][6] || p.m[0][5]) ? fdate(p.m[0][6] || p.m[0][5]) : "—"],
    ["Indemnité brute / mois", p => p.indemnite != null ? eur(p.indemnite) : (p.ind || []).find(Boolean) ? `plafond ${eur(p.ind.find(Boolean))}` : "—"],
    ["Participation aux scrutins publics", p => v(p).participation != null ? `${v(p).participation} %` : "—"],
    ["Votes comme la majorité de son groupe", p => v(p).conforme != null ? `${v(p).conforme} %` : "—"],
    ["Commissions et organes", p => p.commissions?.length ?? "—"],
    ["Présence en réunion de commission", p => { const c = p.presence_com, n = c ? c[0] + c[1] + c[2] : 0;
      return n ? `${Math.round(100 * c[0] / n)} %<br><small class="muted">${nf(c[0])} sur ${nf(n)}</small>` : "—"; }],
    ["Déclaration d'intérêts (HATVP)", p => p.interets?.derniere ? `publiée le ${fdate(p.interets.derniere)}` : "—"],
    ["Profession déclarée", p => esc(p.profession || "") || "—"],
  ];
  // Une couleur par personne, selon l'ordre d'ajout (jamais selon le parti).
  const coul = i => `var(--p${i + 1})`;
  const pct = (c, n) => n ? Math.round(100 * c / n) : null;
  const mesures = [  // [titre, valeur, affichage, maximum (null : le plus grand des valeurs)]
    ["Participation aux scrutins publics", p => v(p).participation, x => `${x} %`, 100],
    ["Votes comme la majorité de son groupe", p => v(p).conforme, x => `${x} %`, 100],
    ["Présence en réunion de commission", p => p.presence_com ? pct(p.presence_com[0], p.presence_com[0] + p.presence_com[1] + p.presence_com[2]) : null, x => `${x} %`, 100],
    ["Indemnité brute / mois (ou plafond légal)", p => p.indemnite ?? (p.ind || []).find(Boolean) ?? null, eur, null],
    ["Mandats en cours", p => p.m.length, nf, null],
    ["Amendements déposés", p => p.activite?.amendements ?? null, nf, null],
  ].filter(([, f]) => gens.some(p => f(p) != null));
  const barres = gens.length ? `<section class="sec"><h2>En un coup d'œil</h2>
    <ul class="legende">${gens.map((p, i) => `<li><i style="background:${coul(i)}"></i>${esc(p.prenom)} ${esc(p.nom)}</li>`).join("")}</ul>
    ${mesures.map(([t, f, aff, max]) => { const m = max || Math.max(...gens.map(p => f(p) || 0)) || 1;
      return `<h3 class="mesure">${t}</h3>${gens.map((p, i) => { const x = f(p);
        return `<div class="barre-p"><span>${esc(p.prenom)} ${esc(p.nom)}</span><div><i style="width:${x == null ? 0 : 100 * x / m}%;background:${coul(i)}"></i></div>
          <b class="num">${x == null ? "—" : aff(x)}</b></div>`; }).join("")}`; }).join("")}
    ${src("« — » : donnée non publiée par la source pour cette personne, jamais zéro. Couleurs attribuées dans l'ordre d'ajout, sans lien avec un parti.")}</section>` : "";
  app.innerHTML = `<div class="lieu-h" style="margin-top:26px"><h1>Comparer</h1></div>
    <p class="muted">De 2 à 5 personnes côte à côte, avec ce que publient les sources officielles. Aucune note, aucun classement ;
      « — » signifie que la source ne publie pas la donnée, jamais zéro.</p>
    ${gens.length < 5 ? `<div class="filtres" style="max-width:520px"><input id="cq" placeholder="Ajouter une personne : nom ou prénom et nom" autocomplete="off"></div><div id="csug" style="max-width:520px"></div>` : ""}
    ${barres}
    ${gens.length ? `<h2 class="sec">Le détail</h2><div class="comparo"><table><thead><tr><th></th>${gens.map((p, i) => `<th style="box-shadow:inset 0 4px 0 ${coul(i)}">
        ${p.photo ? `<img src="${esc(p.photo)}" alt="">` : `<span class="ini">${esc(initiales(p.prenom, p.nom))}</span>`}
        <a href="#/p/${p._id}"><b>${esc(p.prenom)} ${esc(p.nom)}</b></a>
        <a class="retirer" href="${url(ids.filter(x => x !== p._id))}">Retirer</a></th>`).join("")}</tr></thead>
      <tbody>${lignes.map(([l, f]) => `<tr><th>${l}</th>${gens.map(p => `<td>${f(p)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
      : `<p class="vide">Ajoutez une première personne avec le champ ci-dessus.</p>`}
    ${src("Sources : celles de chaque fiche (Répertoire national des élus, Assemblée nationale, Sénat, Parlement européen, HATVP).")}`;
  const input = document.getElementById("cq");
  if (!input) return;
  let att;
  input.addEventListener("input", () => { clearTimeout(att); att = setTimeout(async () => {
    const box = document.getElementById("csug");
    if (norm(input.value).length < 3) { box.innerHTML = ""; return; }
    const r = (await chercheNom(input.value)).filter(e => !ids.includes(`${e.shard}/${e.slug}`)).slice(0, 8);
    box.innerHTML = r.length ? `<div class="suggestions">${r.map(e => `<a href="${url([...ids, `${e.shard}/${e.slug}`])}">${esc(e.prenom)} ${esc(e.nom)}
      <small>${esc(e.f)}${e.lieu ? " · " + esc(e.lieu) : ""}</small></a>`).join("")}</div>` : `<p class="vide">Personne trouvée.</p>`;
  }, 250); });
  input.focus();
}

/* ---------- signaler, droit de réponse, à propos ---------- */

async function formulaire(type, qs, j) {
  setTab("");
  const id = new URLSearchParams(qs || "").get("p") || "";
  const [s, ...r] = id.split("/");
  const p = id ? await personne(s, r.join("/")).catch(() => null) : null;
  if (!encore(j)) return;
  const qui = p ? `${p.prenom} ${p.nom}` : "";
  const reponse = type === "reponse";
  app.innerHTML = `<div class="lieu-h" style="margin-top:26px"><h1>${reponse ? "Droit de réponse" : "Signaler une erreur"}</h1></div>
    ${p ? `<p class="muted">À propos de la fiche de <a href="#/p/${esc(id)}" style="color:var(--accent)">${esc(qui)}</a>.</p>` : ""}
    ${reponse ? `<div class="encart"><p>Toute personne nommée ou désignée sur ce site peut demander l'insertion d'une réponse
      (loi n° 2004-575 du 21 juin 2004 pour la confiance dans l'économie numérique, article 6, IV). La demande doit être
      adressée au directeur de la publication dans les trois mois suivant la mise en ligne du contenu concerné ; la réponse
      est alors insérée dans les trois jours suivant sa réception, sauf motif légitime de refus.</p>
      <p class="muted">Le directeur de la publication sera désigné avant la mise en ligne publique. En attendant, les demandes
      parviennent à l'adresse provisoire ${CONTACT}.</p></div>`
      : `<p class="muted">Une information fausse, manquante ou dépassée ? Indiquez-la ici. Tout ce qui est affiché vient d'une source
      officielle : si l'erreur vient de la source, nous le signalerons à l'organisme qui la publie.</p>`}
    <form class="formulaire" id="f">
      ${reponse ? `<label>Vos nom et qualité<input name="nom" required></label>
        <label>Passage ou donnée contestée<textarea name="passage" rows="3" required></textarea></label>
        <label>Votre réponse<textarea name="message" rows="8" required></textarea></label>`
      : `<label>Type de signalement<select name="type"><option>Information fausse</option><option>Information manquante</option>
          <option>Information dépassée</option><option>Autre</option></select></label>
        <label>Ce qui ne va pas<textarea name="message" rows="6" required placeholder="Ex. : cette personne n'est plus adjointe depuis…"></textarea></label>
        <label>Votre nom (facultatif)<input name="nom"></label>`}
      <label>Votre e-mail${reponse ? "" : " (facultatif, pour vous répondre)"}<input name="email" type="email" ${reponse ? "required" : ""}></label>
      <button class="btn" type="submit">Préparer l'e-mail</button>
      <p class="src">L'envoi passe par votre messagerie, vers ${CONTACT} (adresse provisoire). Vos coordonnées servent uniquement
        à traiter la demande ; elles ne sont jamais publiées ni transmises.</p>
    </form>`;
  document.getElementById("f").addEventListener("submit", e => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(e.target));
    const sujet = `[${reponse ? "Droit de réponse" : "Signalement"}] ${qui || "Politiscope"}${id ? ` (${id})` : ""}`;
    const corps = [p ? `Fiche : ${location.origin}${location.pathname}#/p/${id}` : "", d.type ? `Type : ${d.type}` : "",
      d.passage ? `Passage contesté :\n${d.passage}` : "", `${reponse ? "Réponse" : "Message"} :\n${d.message}`,
      d.nom ? `Nom : ${d.nom}` : "", d.email ? `E-mail : ${d.email}` : ""].filter(Boolean).join("\n\n");
    location.href = `mailto:${CONTACT}?subject=${encodeURIComponent(sujet)}&body=${encodeURIComponent(corps)}`;
  });
}

function aPropos() {
  setTab("");
  app.innerHTML = `<div class="lieu-h" style="margin-top:26px"><h1>À propos et méthode</h1></div>
    <section class="sec"><h2>Ce que fait ce site</h2><ul class="puces">
      <li>Montre <b>qui exerce un mandat</b> en France aujourd'hui, de la mairie à l'Élysée.</li>
      <li>Réunit ce que les institutions publient sur chacun : <b>mandats, rémunération, votes, présence, déclarations d'intérêts</b>.</li>
      <li>Uniquement des <b>sources officielles et ouvertes</b>, citées sous chaque bloc avec leur date.</li></ul></section>
    <section class="sec"><h2>Neutralité</h2><ul class="puces">
      <li><b>Aucune note, aucun classement</b>, ni « meilleur » ni « pire ».</li>
      <li>Listes en <b>ordre alphabétique</b>.</li>
      <li>Couleurs : le niveau d'institution, le lieu ou l'ordre d'une comparaison, <b>jamais un parti</b>.</li>
      <li>Aucune consigne de vote.</li></ul></section>
    <section class="sec"><h2>Méthode</h2>
      <div class="kv"><b>Qui siège</b><span>Chaque institution fait foi pour ses membres : l'Assemblée nationale pour les députés, le Sénat pour
        les sénateurs, l'Assemblée nationale et la HATVP pour le gouvernement, le Répertoire national des élus pour les élus locaux et les députés européens.</span></div>
      <div class="kv"><b>Une personne, une fiche</b><span>Les mandats d'une même personne sont réunis par nom, prénom et date de naissance.</span></div>
      <div class="kv"><b>Rémunérations</b><span>Parlementaires et gouvernement : calcul sur la base légale (grille de la fonction publique). Élus locaux :
        plafond légal selon le code général des collectivités territoriales et la population ; le montant réellement voté n'est pas publié en open data.</span></div>
      <div class="kv"><b>Votes</b><span>Scrutins publics de l'Assemblée nationale. La participation aux scrutins ne mesure pas la présence physique.
        Le Sénat ne publie pas ses votes nominatifs en open data.</span></div>
      <div class="kv"><b>Ce que nous ne publions pas</b><span>Les candidats non élus, toute donnée privée, et les déclarations de patrimoine :
        leur republication est interdite (loi n° 2013-907, art. 26). Chaque fiche indique où les consulter :</span></div>
      <ul class="puces"><li><b>Président et gouvernement</b> : publiées par la HATVP sur hatvp.fr (loi n° 2013-907, art. 5).</li>
        <li><b>Députés et sénateurs</b> : consultables à la préfecture du département d'élection par tout électeur inscrit sur les listes électorales
          (code électoral, art. LO 135-2 et LO 296) ; préfecture de Paris pour les élus des Français de l'étranger, haut-commissariat en Nouvelle-Calédonie et en Polynésie française.</li>
        <li><b>Députés européens</b> : consultables dans toutes les préfectures, par tout électeur inscrit (loi n° 2013-907, art. 12).</li>
        <li><b>Élus locaux</b> : ni publiées ni consultables ; seule la HATVP les contrôle, pour les élus qui y sont soumis.</li></ul></section>
    <section class="sec"><h2>Sources</h2>
      <div class="kv"><b>Répertoire national des élus</b><span><a href="https://www.data.gouv.fr/datasets/5c34c4d1634f4173183a64f1/" target="_blank" rel="noopener" style="color:var(--accent)">data.gouv.fr ↗</a> · Ministère de l'Intérieur · mis à jour le ${esc(META.maj)}</span></div>
      <div class="kv"><b>Assemblée nationale</b><span><a href="https://data.assemblee-nationale.fr" target="_blank" rel="noopener" style="color:var(--accent)">data.assemblee-nationale.fr ↗</a> · députés, organes, scrutins</span></div>
      <div class="kv"><b>Sénat</b><span><a href="https://data.senat.fr" target="_blank" rel="noopener" style="color:var(--accent)">data.senat.fr ↗</a> · sénateurs, groupes, commissions</span></div>
      <div class="kv"><b>Parlement européen</b><span>liste des membres</span></div>
      <div class="kv"><b>HATVP</b><span><a href="https://www.hatvp.fr" target="_blank" rel="noopener" style="color:var(--accent)">hatvp.fr ↗</a> · déclarations d'intérêts</span></div>
      <div class="kv"><b>INSEE et geo.api.gouv.fr</b><span>communes, populations, cantons ; contours IGN (Licence Ouverte)</span></div>
      <div class="kv"><b>Photos</b><span>sites de l'Assemblée nationale, du Sénat et du Parlement européen ; à défaut Wikimedia Commons (licences libres). Crédit sous chaque photo.</span></div></section>
    <section class="sec"><h2>Confidentialité</h2><ul class="puces"><li>Aucun cookie publicitaire, aucune mesure d'audience pour l'instant.</li>
      <li>Les formulaires ouvrent votre messagerie : rien n'est stocké par le site.</li>
      <li><b>Compte « Mes élus » (facultatif)</b> : adresse e-mail et liste des élus suivis, enregistrées avec votre accord explicite,
        car elles peuvent révéler une opinion politique. Vous pouvez tout retirer depuis « Mes élus » et demander la suppression du compte à ${CONTACT}.</li>
      <li>Les images à partager sont fabriquées dans votre navigateur : rien n'est envoyé.</li></ul></section>
    <section class="sec"><h2>Mentions légales</h2><ul class="puces">
      <li><b>Éditeur</b> : particulier publiant à titre non professionnel ; son identité est connue de l'hébergeur
        (loi n° 2004-575 du 21 juin 2004, art. 6, III, 2).</li>
      <li><b>Hébergeur</b> : GitHub, Inc. (GitHub Pages), 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis.</li>
      <li><b>Contact, signalement, droit de réponse</b> : ${CONTACT} ·
        <a href="#/reponse" style="color:var(--accent)">Exercer un droit de réponse</a> · <a href="#/signaler" style="color:var(--accent)">Signaler une erreur</a></li>
      <li><b>Données</b> : sources publiques officielles réutilisées sous Licence Ouverte (Etalab) ou licences équivalentes, citées sur chaque page.</li></ul></section>`;
}

/* ---------- fonctions expliquées ---------- */

const FONCTIONS = [  // [type, titre, niveau, combien, élection, durée, rôle, textes]
  ["president", "Président de la République", "national", "1", "Élu au suffrage universel direct, à deux tours.",
    "5 ans ; deux mandats consécutifs au plus.",
    "Nomme le Premier ministre, promulgue les lois, peut dissoudre l'Assemblée nationale, est chef des armées, négocie et ratifie les traités.",
    "Constitution, articles 5 à 19"],
  ["gouvernement", "Premier ministre et gouvernement", "national", "", "Le Premier ministre est nommé par le Président de la République ; les ministres, sur sa proposition.",
    "Pas de durée fixe : le gouvernement reste tant qu'il conserve la confiance de l'Assemblée nationale.",
    "Détermine et conduit la politique de la nation, dirige l'administration, propose des projets de loi. Responsable devant l'Assemblée nationale, qui peut le renverser par une motion de censure.",
    "Constitution, articles 8, 20, 21 et 49"],
  ["depute", "Député", "national", "577", "Élu au suffrage universel direct dans une circonscription, au scrutin majoritaire à deux tours.",
    "5 ans, sauf dissolution.", "Vote la loi, contrôle l'action du gouvernement, évalue les politiques publiques. A le dernier mot sur la loi en cas de désaccord avec le Sénat.",
    "Constitution, articles 24, 45 et 49"],
  ["senateur", "Sénateur", "national", "348", "Élu au suffrage universel indirect par les « grands électeurs » (surtout des élus locaux) de son département.",
    "6 ans ; le Sénat est renouvelé par moitié tous les 3 ans.", "Vote la loi et contrôle le gouvernement ; représente les collectivités territoriales.",
    "Constitution, article 24"],
  ["eurodepute", "Député européen", "europe", "81", "Élu au suffrage universel direct, au scrutin de liste proportionnel, sur une circonscription unique pour toute la France.",
    "5 ans.", "Adopte les lois européennes avec le Conseil de l'Union, vote le budget de l'Union, contrôle la Commission européenne.", "Traités de l'Union européenne"],
  ["cr", "Conseiller régional", "region", "", "Élu au suffrage universel direct, au scrutin de liste à deux tours, par sections départementales.",
    "6 ans.", "Développement économique, lycées, transports régionaux, formation professionnelle, aménagement du territoire.", "Code général des collectivités territoriales"],
  ["cd", "Conseiller départemental", "departement", "", "Élu en binôme (une femme, un homme) dans un canton, au scrutin majoritaire à deux tours.",
    "6 ans.", "Action sociale (RSA, protection de l'enfance, personnes âgées et handicapées), collèges, routes départementales.", "Code général des collectivités territoriales"],
  ["cc", "Conseiller communautaire", "interco", "", "Désigné lors des élections municipales, parmi les conseillers municipaux de sa commune.",
    "6 ans, comme le conseil municipal.", "Siège à l'intercommunalité (communauté de communes, d'agglomération, urbaine, métropole), selon les compétences que les communes lui ont confiées : eau, déchets, transports, développement économique…",
    "Code général des collectivités territoriales"],
  ["maire", "Maire", "commune", "", "Élu par le conseil municipal, parmi ses membres.", "6 ans, comme le conseil municipal.",
    "Prépare et exécute les décisions du conseil et le budget, exerce la police municipale. Agent de l'État : état civil, organisation des élections.",
    "Code général des collectivités territoriales"],
  ["adjoint", "Adjoint au maire", "commune", "", "Élu par le conseil municipal.", "6 ans, comme le conseil municipal.",
    "Exerce les délégations que lui confie le maire (urbanisme, écoles, finances…). Leur nombre ne peut dépasser 30 % de l'effectif du conseil.",
    "Code général des collectivités territoriales"],
  ["cm", "Conseiller municipal", "commune", "", "Élu au suffrage universel direct, au scrutin de liste.", "6 ans.",
    "Règle par ses délibérations les affaires de la commune : budget, services publics locaux, urbanisme.", "Code général des collectivités territoriales"],
];

function fonctions() {
  setTab("fonctions");
  const c = META.counts;
  const total = t => t === "cm" ? (c.cm || 0) + (c.maire || 0) + (c.adjoint || 0) : t === "cr" ? (c.cr || 0) + (c.ma || 0) : c[t];
  app.innerHTML = `<div class="lieu-h" style="margin-top:26px"><div class="kicker">Comprendre</div><h1>Qui fait quoi</h1></div>
    <p class="muted" style="max-width:720px">Chaque fonction élective en quelques lignes : comment on y accède, pour combien de temps, et ce qu'elle permet de faire.
      Ces fiches résument les textes ; elles ne les remplacent pas.</p>
    <div class="fonctions">${FONCTIONS.map(([t, titre, niv, , elec, duree, role, textes]) => `<article class="fonction" style="--lvl:var(--${niv})">
      <header><span class="big num">${nf(total(t))}</span><h2>${titre}</h2></header>
      <dl><dt>Comment</dt><dd>${elec}</dd><dt>Durée</dt><dd>${duree}</dd><dt>Rôle</dt><dd>${role}</dd></dl>
      <p class="src">${textes}</p>
      <a class="plus" href="#/annuaire?t=${t}">${{president: "Voir la fiche", gouvernement: "Voir le gouvernement"}[t] || `Voir les ${T[t][0].toLowerCase()}`} →</a></article>`).join("")}</div>`;
}

/* ---------- mises à jour ---------- */

async function misesAJour(j) {
  setTab("");
  const l = await get("sources.json").catch(() => []);
  if (!encore(j)) return;
  const jours = d => Math.floor((Date.now() - new Date(d)) / 864e5);
  app.innerHTML = `<div class="lieu-h" style="margin-top:26px"><div class="kicker">Transparence</div><h1>Mises à jour</h1></div>
    <p class="muted" style="max-width:720px">Une routine récupère chaque source officielle, vérifie qu'elle est complète et lisible, puis reconstruit le site.
      Si une source change de format ou paraît incomplète, la mise à jour s'arrête au lieu de publier des données fausses.</p>
    ${l.length ? `<div class="comparo"><table><thead><tr><th>Source</th><th>Ce qu'elle apporte</th><th>Rythme prévu</th><th>Dernière publication</th><th>Dernière vérification</th><th>État</th></tr></thead>
      <tbody>${l.map(s => { const retard = jours(s.verifie) > Math.max(2, s.frequence * 1.5);
        return `<tr><th>${esc(s.nom)}</th><td>${esc(s.apport)}</td><td>${s.frequence <= 1 ? "quotidien" : s.frequence <= 7 ? "hebdomadaire" : s.frequence <= 31 ? "mensuel" : s.frequence <= 92 ? "trimestriel" : "annuel"}</td>
          <td>${s.maj ? fdate(s.maj) : "non communiquée par la source"}</td><td>${fdate(s.verifie)}</td><td><b class="${retard ? "no" : "ok"}">${retard ? "en retard" : "à jour"}</b></td></tr>`; }).join("")}</tbody></table></div>`
      : `<p class="vide">Aucune mise à jour enregistrée pour l'instant.</p>`}
    ${src("« Dernière publication » : date de modification du fichier chez la source. « Dernière vérification » : dernier passage de la routine.")}`;
}

/* ---------- Parlement en direct ---------- */

const jourLong = d => new Date(d + "T12:00").toLocaleDateString("fr-FR", {weekday: "long", day: "numeric", month: "long"});
const resultat = s => `<b class="${/^adopt/.test(s) ? "vp" : /^rejet/.test(s) ? "vc" : ""}">${esc(s ? s[0].toUpperCase() + s.slice(1) : "—")}</b>`;
const ligneScrutin = s => `<a class="vote" href="#/scrutin/${s[0]}"><span class="vd">${fdate(s[1])}</span>
  <span class="vt">${esc(s[2][0].toUpperCase() + s[2].slice(1))}<small>Scrutin n° ${s[0]} · ${nf(s[4])} pour, ${nf(s[5])} contre, ${nf(s[6])} abstentions</small></span>
  <span class="vpos">${resultat(s[3])}</span></a>`;

async function parlement(j) {
  setTab("parlement");
  const [ag, sc] = await Promise.all([get("agenda.json").catch(() => []), get("scrutins.json")]);
  if (!encore(j)) return;
  const auj = new Date().toLocaleDateString("sv");
  const TYPE = {seance: "Séance publique", commission: "Commission", autre: "Autre réunion"};
  let filtre = "seance", jours = 5, n = 20, q = "";
  app.innerHTML = `<div class="lieu-h" style="margin-top:26px"><div class="kicker">Assemblée nationale et Sénat</div><h1>Parlement en direct</h1></div>
    <p class="muted" style="max-width:720px">L'ordre du jour des prochains jours et chaque vote de l'Assemblée, groupe par groupe.
      Agenda publié par l'Assemblée nationale, relevé le ${fdate(META.agenda_maj)}.</p>
    <section class="sec"><h2>À l'agenda</h2>
      <div class="segments" role="group" aria-label="Type de réunion">${[["seance", "Séances publiques"], ["commission", "Commissions"], ["", "Tout"]]
        .map(([v, l]) => `<button class="btn ghost" data-f="${v}" aria-pressed="${v === filtre}">${l}</button>`).join("")}</div>
      <div id="agenda"></div>
      ${src("Source : Assemblée nationale, open data (agenda), qui reprend aussi les séances publiques du Sénat. Réunions annulées non affichées ; « à confirmer » : réunion éventuelle.")}</section>
    <section class="sec"><h2>Derniers votes à l'Assemblée</h2>
      <div class="filtres"><input id="sq" placeholder="Chercher un scrutin (ex. retraites, budget, n° 9100)" autocomplete="off"></div>
      <div id="scrutins"></div>
      ${src(`Source : scrutins publics de l'Assemblée nationale, open data (17e législature, ${nf(sc.length)} scrutins). Le Sénat ne publie pas ses votes nominatifs en open data.`)}</section>`;
  const dessineAgenda = () => {
    const l = ag.filter(a => a.d.slice(0, 10) >= auj && (!filtre || a.t === filtre));
    const parJour = Object.entries(l.reduce((o, a) => ((o[a.d.slice(0, 10)] ||= []).push(a), o), {}));
    document.getElementById("agenda").innerHTML = (parJour.length ? parJour.slice(0, jours).map(([d, items]) => `<h3 class="jour">${d === auj ? "Aujourd'hui · " : ""}${jourLong(d)}</h3>
      ${items.map(a => `<div class="vote"><span class="vd">${a.d.slice(11, 13)} h ${a.d.slice(14, 16)}<small>${a.ch === "Sénat" ? "Sénat" : "Assemblée"}</small></span>
        <span class="vt"><b>${a.t === "seance" ? TYPE.seance : esc(a.o || TYPE[a.t])}</b>${a.p.length ? `<ul class="odj">${a.p.slice(0, 6).map(x => `<li>${esc(x[0].toUpperCase() + x.slice(1))}</li>`).join("")}</ul>` : ""}</span>
        <span class="vpos">${a.e === "Eventuel" ? "<b>à confirmer</b>" : ""}</span></div>`).join("")}`).join("")
      : `<p class="vide">Rien à l'agenda publié pour les prochains jours.</p>`)
      + (parJour.length > jours ? `<button class="plus" id="aplus">Afficher les jours suivants</button>` : "");
    document.getElementById("aplus")?.addEventListener("click", () => { jours += 5; dessineAgenda(); });
  };
  const dessineScrutins = () => {
    const l = q ? sc.filter(s => String(s[0]) === q || norm(s[2]).includes(q)) : sc;
    document.getElementById("scrutins").innerHTML = `<p class="compte">${nf(l.length)} scrutins</p>` + l.slice(0, n).map(ligneScrutin).join("")
      + (l.length > n ? `<button class="plus" id="splus">Afficher 20 de plus</button>` : "");
    document.getElementById("splus")?.addEventListener("click", () => { n += 20; dessineScrutins(); });
  };
  app.querySelectorAll(".segments button").forEach(b => b.addEventListener("click", () => {
    filtre = b.dataset.f; jours = 5;
    app.querySelectorAll(".segments button").forEach(x => x.setAttribute("aria-pressed", x === b));
    dessineAgenda(); }));
  document.getElementById("sq").addEventListener("input", e => { q = norm(e.target.value); n = 20; dessineScrutins(); });
  dessineAgenda(); dessineScrutins();
}

async function scrutin(num, j) {
  setTab("parlement");
  const sc = await get("scrutins.json");
  const i = sc.findIndex(s => String(s[0]) === num);
  if (i < 0) { if (encore(j)) app.innerHTML = `<p class="vide">Scrutin introuvable. <a href="#/parlement" style="color:var(--accent)">Retour au Parlement en direct</a></p>`; return; }
  const gr = ((await get(`s/${Math.floor(i / 500)}.json`))[i % 500] || []).map(g => [...g, ...(META.groupes_an?.[g[0]] || ["", g[0]])])
    .sort((a, b) => a[6].localeCompare(b[6], "fr"));  // [ref, pour, contre, abst, nv, libellé, sigle]
  if (!encore(j)) return;
  const [n, d, titre, sort, pour, contre, abst] = sc[i];
  const POS = ["pour", "contre", "abstention"];
  const majo = g => { const m = Math.max(g[1], g[2], g[3]); return !m ? "aucun vote exprimé" : [g[1], g[2], g[3]].filter(x => x === m).length > 1 ? "partagée" : POS[[g[1], g[2], g[3]].indexOf(m)]; };
  const barre = (a, b, c) => `<div class="votebar" style="margin:6px 0 0"><span class="vp" style="flex:${a}"></span><span class="vc" style="flex:${b}"></span><span class="va" style="flex:${c}"></span></div>`;
  app.innerHTML = `<div class="ariane"><a href="#/parlement">‹ Parlement en direct</a></div>
    <div class="lieu-h"><div class="kicker">Assemblée nationale · scrutin n° ${n} · ${fdate(d)}</div><h1 class="titre-long">${esc(titre[0].toUpperCase() + titre.slice(1))}</h1></div>
    <div class="tuiles">${[[resultat(sort), "résultat", ""], [nf(pour), "pour", ""], [nf(contre), "contre", ""], [nf(abst), "abstentions", ""]]
      .map(([a, b]) => `<div class="tuile"><span class="big num">${a}</span><span>${b}</span></div>`).join("")}</div>
    ${barre(pour, contre, abst)}
    <section class="sec"><h2>Par groupe</h2>
      <div class="votelegend" style="margin-bottom:6px"><span><i class="vp"></i>pour</span><span><i class="vc"></i>contre</span><span><i class="va"></i>abstention</span></div>
      <div class="groupes">${gr.map(g => `<div class="groupe"><div class="groupe-t"><b>${esc(g[6])}</b><span class="muted">${esc(g[5])}</span><span class="pastille">${majo(g)}</span></div>
        ${g[1] + g[2] + g[3] ? barre(g[1], g[2], g[3]) : `<div class="votebar"></div>`}
        <small class="num">${nf(g[1])} pour · ${nf(g[2])} contre · ${nf(g[3])} abst.${g[4] ? ` · ${nf(g[4])} non-votant${g[4] > 1 ? "s" : ""}` : ""}</small></div>`).join("")}</div>
      <p><a class="btn" href="https://www.assemblee-nationale.fr/dyn/17/scrutins/${n}" target="_blank" rel="noopener">Le scrutin et la liste nominative sur assemblee-nationale.fr ↗</a></p>
      ${src("Groupes en ordre alphabétique. « Majorité du groupe » : position la plus fréquente parmi les votes exprimés de ses membres. Source : Assemblée nationale, open data.")}</section>`;
}

/* ---------- routeur ---------- */

function route() {
  const j = ++jeton;
  const [chemin, qs] = (location.hash.slice(1) || "/").split("?");
  const s = chemin.split("/").filter(Boolean);
  const run = f => f.catch(e => { if (encore(j)) app.innerHTML = `<p class="vide">Impossible de charger cette page (${esc(e.message)}).</p>`; });
  if (s[0] === "p") return run(s.length === 2 ? fiche("fr", s[1], j) : fiche(s[1], s[2], j));
  if (s[0] === "r") return run(region(s[1], j));
  if (s[0] === "d") return run(departement(s[1], j));
  if (s[0] === "c") return run(commune(s[1], j));
  if (s[0] === "moi") return run(moi(s[1], j));
  if (s[0] === "annuaire") return run(annuaire(qs, j));
  if (s[0] === "comparer") return run(comparer(qs, j));
  if (s[0] === "signaler" || s[0] === "reponse") return run(formulaire(s[0], qs, j));
  if (s[0] === "a-propos") return aPropos();
  if (s[0] === "fonctions") return fonctions();
  if (s[0] === "mises-a-jour") return run(misesAJour(j));
  if (s[0] === "parlement") return run(parlement(j));
  if (s[0] === "suivis") return run(pageSuivis(qs, j));
  if (s[0] === "scrutin") return run(scrutin(s[1], j));
  return run(accueil(j));
}
document.getElementById("maj").innerHTML = `Données officielles — élus locaux au <b>${esc(META.maj)}</b>, Parlement et gouvernement mis à jour chaque jour · <a href="#/mises-a-jour" style="color:var(--accent)">Mises à jour</a>`;
// Mode sombre : suit le système, bouton pour forcer ; préférence gardée dans ce navigateur si possible.
const theme = document.getElementById("theme");
const appliqueTheme = t => { if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; };
try { appliqueTheme(localStorage.getItem("theme")); } catch {}
theme.addEventListener("click", () => {
  const sombre = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;
  const t = sombre ? "light" : "dark";
  appliqueTheme(t);
  try { localStorage.setItem("theme", t); } catch {}
});
// Partager : feuille de partage du téléphone si elle existe, sinon copie du lien.
document.getElementById("copier").addEventListener("click", async e => {
  const b = e.currentTarget;
  try {
    if (navigator.share && matchMedia("(pointer: coarse)").matches) await navigator.share({title: document.title, url: location.href});
    else { await navigator.clipboard.writeText(location.href); b.querySelector(".txt").textContent = "Lien copié"; }
  } catch {}
});
// Écouter la page : synthèse vocale du navigateur, en français.
document.getElementById("ecouter").addEventListener("click", e => {
  const s = window.speechSynthesis, b = e.currentTarget;
  if (!s) return;
  if (s.speaking) { s.cancel(); b.setAttribute("aria-pressed", "false"); return; }
  const u = new SpeechSynthesisUtterance(app.innerText.replace(/\s+/g, " ").slice(0, 30000));
  u.lang = "fr-FR";
  u.onend = () => b.setAttribute("aria-pressed", "false");
  b.setAttribute("aria-pressed", "true");
  s.speak(u);
});
window.addEventListener("hashchange", () => window.speechSynthesis?.cancel());
window.addEventListener("hashchange", () => { route(); if (!location.hash.includes("annuaire")) window.scrollTo(0, 0); });
Suivi.init().finally(route);  // état du compte connu avant d'afficher la première page
