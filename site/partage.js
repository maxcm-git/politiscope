/* Image à partager (story Instagram 1080×1920 ou carré 1080×1080), dessinée dans le navigateur à partir de la page affichée :
   titre, photo, puces « En bref », tuiles, jauges. L'utilisateur coche ce qu'il veut ; rien n'est envoyé à un serveur.
   Partage : feuille de partage du téléphone (fichier image) si elle l'accepte, sinon téléchargement. */
const FORMATS = {story: [1080, 1920], carre: [1080, 1080]};

// Ce que la page affiche, sous forme d'éléments cochables.
function elementsDeLaPage() {
  const t = s => (s || "").replace(/\s+/g, " ").trim();
  const el = [];
  document.querySelectorAll("#app .enbref li").forEach(li => { const x = t(li.innerText);
    if (!/plus bas/.test(x)) el.push({type: "puce", texte: x}); });  // renvois internes à la page : sans objet dans une image
  document.querySelectorAll("#app .tuiles .tuile").forEach(x => {
    const [a, b] = [x.querySelector(".big"), x.querySelector("span:not(.big)")];
    if (a && b) el.push({type: "chiffre", valeur: t(a.innerText), libelle: t(b.innerText)});
  });
  document.querySelectorAll("#app .jauge").forEach(x => {
    const v = x.querySelector(".jauge-t b"), l = x.querySelector(".jauge-t span"), m = x.querySelector(".jauge-b em");
    if (v && l && /%/.test(v.innerText)) el.push({type: "jauge", valeur: parseFloat(v.innerText.replace(",", ".")), libelle: t(l.innerText),
      repere: m ? parseFloat(m.style.left) : null});
  });
  return el.slice(0, 40);
}

function enteteDeLaPage() {
  const h1 = document.querySelector("#app h1"), k = document.querySelector("#app .kicker"), img = document.querySelector("#app .fiche-tete img");
  return {titre: h1?.innerText.trim() || "Politiscope", sous: k?.innerText.replace(/\s+/g, " ").trim() || "", photo: img?.src || "",
    credit: document.querySelector("#app figcaption")?.innerText.replace(/^Photo : /, "") || ""};
}

function couleurs() {
  const s = getComputedStyle(document.querySelector("#app .fiche") || document.documentElement);
  const v = n => s.getPropertyValue(n).trim();
  return {fond: "#f6f4ee", carte: "#fffdf8", encre: "#1b1d22", gris: "#5d6470", trait: "#e2ddd2", accent: v("--lvl") || "#1f3f8f"};
}

function lignes(ctx, texte, largeur) {  // coupe un texte en lignes qui tiennent dans « largeur »
  const mots = texte.split(" "), out = [];
  let l = "";
  for (const m of mots) { const essai = l ? `${l} ${m}` : m;
    if (ctx.measureText(essai).width > largeur && l) { out.push(l); l = m; } else l = essai; }
  if (l) out.push(l);
  return out;
}

async function dessiner(canvas, format, choix, tete) {
  const [W, H] = FORMATS[format], ctx = canvas.getContext("2d"), C = couleurs(), M = 72;
  canvas.width = W; canvas.height = H;
  await document.fonts.ready;
  ctx.fillStyle = C.fond; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = C.accent; ctx.fillRect(0, 0, W, 18);
  let y = 110;
  ctx.fillStyle = C.encre; ctx.font = '700 40px "Fraunces", Georgia, serif'; ctx.fillText("Politiscope", M, y);
  ctx.fillStyle = C.gris; ctx.font = '500 26px "Instrument Sans", sans-serif';
  ctx.textAlign = "right"; ctx.fillText("Les élus, en données officielles", W - M, y); ctx.textAlign = "left";
  y += 60;
  if (tete.photo && choix.photo) {
    const img = new Image(); img.src = tete.photo;
    try { await img.decode();
      const T = format === "story" ? 360 : 240, r = 28;
      ctx.save(); ctx.beginPath(); ctx.roundRect(M, y, T, T, r); ctx.clip();
      const s = Math.max(T / img.width, T / img.height);
      ctx.drawImage(img, M + (T - img.width * s) / 2, y + (T - img.height * s) / 2, img.width * s, img.height * s); ctx.restore();
      if (format === "carre") { ctx.font = '800 64px "Fraunces", Georgia, serif'; ctx.fillStyle = C.encre;
        let yy = y + 70; for (const l of lignes(ctx, tete.titre, W - 2 * M - T - 40).slice(0, 3)) { ctx.fillText(l, M + T + 40, yy); yy += 72; }
        ctx.font = '600 26px "Instrument Sans", sans-serif'; ctx.fillStyle = C.gris;
        for (const l of lignes(ctx, tete.sous, W - 2 * M - T - 40).slice(0, 3)) { ctx.fillText(l, M + T + 40, yy); yy += 34; }
        y += T + 50; tete = {...tete, fait: true};
      } else y += T + 60;
    } catch { /* photo illisible : on continue sans */ }
  }
  if (!tete.fait) {
    ctx.fillStyle = C.gris; ctx.font = '600 28px "Instrument Sans", sans-serif';
    for (const l of lignes(ctx, tete.sous.toUpperCase(), W - 2 * M).slice(0, 2)) { ctx.fillText(l, M, y); y += 38; }
    y += 100; ctx.fillStyle = C.encre; ctx.font = '800 92px "Fraunces", Georgia, serif';  // 100 : place des capitales
    for (const l of lignes(ctx, tete.titre, W - 2 * M).slice(0, 3)) { ctx.fillText(l, M, y); y += 100; }
    y += 10;
  }
  const bas = H - 150;
  let deborde = false;
  const els = choix.elements;
  // puces
  ctx.font = '500 36px "Instrument Sans", sans-serif';
  for (const e of els.filter(e => e.type === "puce")) {
    const ls = lignes(ctx, e.texte, W - 2 * M - 40);
    if (y + ls.length * 48 + 16 > bas) { deborde = true; break; }
    ctx.fillStyle = C.accent; ctx.beginPath(); ctx.arc(M + 10, y - 12, 8, 0, 7); ctx.fill();
    ctx.fillStyle = C.encre; for (const l of ls) { ctx.fillText(l, M + 40, y); y += 48; }
    y += 16;
  }
  // chiffres (deux colonnes)
  const ch = els.filter(e => e.type === "chiffre");
  if (ch.length) y += 10;
  for (let i = 0; i < ch.length; i += 2) {
    if (y + 170 > bas) { deborde = true; break; }
    ch.slice(i, i + 2).forEach((e, k) => {
      const x = M + k * ((W - 2 * M) / 2 + 10), w = (W - 2 * M) / 2 - 10;
      ctx.fillStyle = C.carte; ctx.strokeStyle = C.trait; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.roundRect(x, y, w, 150, 20); ctx.fill(); ctx.stroke();
      ctx.fillStyle = C.encre; ctx.font = '800 54px "Fraunces", Georgia, serif'; ctx.fillText(lignes(ctx, e.valeur, w - 40)[0], x + 24, y + 70);
      ctx.fillStyle = C.gris; ctx.font = '600 26px "Instrument Sans", sans-serif'; ctx.fillText(lignes(ctx, e.libelle, w - 40)[0], x + 24, y + 116);
    });
    y += 170;
  }
  // jauges
  for (const e of els.filter(e => e.type === "jauge")) {
    if (y + 120 > bas) { deborde = true; break; }
    ctx.fillStyle = C.encre; ctx.font = '800 50px "Fraunces", Georgia, serif'; ctx.fillText(`${e.valeur} %`, M, y + 46);
    ctx.font = '600 30px "Instrument Sans", sans-serif'; ctx.fillText(lignes(ctx, e.libelle, W - 2 * M - 220)[0], M + 200, y + 42);
    ctx.fillStyle = C.trait; ctx.beginPath(); ctx.roundRect(M, y + 70, W - 2 * M, 22, 11); ctx.fill();
    ctx.fillStyle = C.accent; ctx.beginPath(); ctx.roundRect(M, y + 70, (W - 2 * M) * Math.min(e.valeur, 100) / 100, 22, 11); ctx.fill();
    if (e.repere != null) { ctx.fillStyle = C.encre; ctx.fillRect(M + (W - 2 * M) * e.repere / 100 - 2, y + 60, 5, 42); }
    y += 130;
  }
  // pied : source et adresse
  ctx.fillStyle = C.trait; ctx.fillRect(M, H - 130, W - 2 * M, 2);
  ctx.fillStyle = C.gris; ctx.font = '500 24px "Instrument Sans", sans-serif';
  const pied = `Sources officielles (Assemblée nationale, Sénat, RNE, HATVP…) · ${new Date().toLocaleDateString("fr-FR")}`;
  ctx.fillText(lignes(ctx, pied, W - 2 * M)[0], M, H - 90);
  if (choix.photo && tete.photo && tete.credit) ctx.fillText(lignes(ctx, `Photo : ${tete.credit}`, W - 2 * M)[0], M, H - 56);
  ctx.textAlign = "right"; ctx.fillStyle = C.encre; ctx.font = '700 26px "Instrument Sans", sans-serif';
  ctx.fillText(location.host.includes("localhost") ? "politiscope" : location.host, W - M, H - 56); ctx.textAlign = "left";
  return deborde;
}

function ouvrirPartageImage() {
  const tete = enteteDeLaPage(), els = elementsDeLaPage();
  const dlg = document.createElement("dialog");
  dlg.className = "dlg-image";
  const groupe = (type, titre, f) => { const l = els.map((e, i) => [e, i]).filter(([e]) => e.type === type);
    return l.length ? `<fieldset><legend>${titre}</legend>${l.map(([e, i]) => `<label class="case"><input type="checkbox" data-i="${i}" ${i < 99 ? "checked" : ""}>${esc(f(e))}</label>`).join("")}</fieldset>` : ""; };
  dlg.innerHTML = `<form method="dialog" class="img-grille">
      <div class="img-choix"><h2>Créer une image à partager</h2>
        <fieldset><legend>Format</legend><label class="case"><input type="radio" name="fmt" value="story" checked> Story (1080 × 1920)</label>
          <label class="case"><input type="radio" name="fmt" value="carre"> Carré (1080 × 1080)</label></fieldset>
        ${tete.photo ? `<fieldset><legend>Photo</legend><label class="case"><input type="checkbox" name="photo" checked> Afficher la photo</label></fieldset>` : ""}
        ${groupe("puce", "En bref", e => e.texte)}${groupe("chiffre", "Chiffres", e => `${e.valeur} · ${e.libelle}`)}${groupe("jauge", "Jauges", e => `${e.valeur} % · ${e.libelle}`)}
        ${els.length ? "" : `<p class="muted">Cette page n'a pas d'éléments à reprendre : l'image montrera le titre.</p>`}
        <p class="muted" id="img-alerte" role="status"></p>
        <div class="actions-lieu"><button class="btn" type="button" id="img-partager">Partager</button>
          <button class="btn ghost" type="button" id="img-telecharger">Télécharger</button><button class="btn ghost" value="fermer">Fermer</button></div></div>
      <div class="img-apercu"><canvas aria-label="Aperçu de l'image"></canvas></div></form>`;
  document.body.append(dlg);
  const canvas = dlg.querySelector("canvas");
  const choix = () => ({photo: dlg.querySelector('[name="photo"]')?.checked,
    elements: [...dlg.querySelectorAll("[data-i]")].filter(c => c.checked).map(c => els[+c.dataset.i])});
  const fmt = () => dlg.querySelector('[name="fmt"]:checked').value;
  const maj = async () => { const trop = await dessiner(canvas, fmt(), choix(), {...tete});
    dlg.querySelector("#img-alerte").textContent = trop ? "Tout ne tient pas : décochez des éléments ou choisissez le format story." : ""; };
  // Par défaut : les puces cochées, le reste décoché (image lisible d'emblée).
  dlg.querySelectorAll("[data-i]").forEach(c => { c.checked = els[+c.dataset.i].type === "puce"; });
  dlg.addEventListener("change", maj);
  const fichier = () => new Promise(r => canvas.toBlob(b => r(new File([b], `politiscope-${Date.now()}.png`, {type: "image/png"})), "image/png"));
  dlg.querySelector("#img-telecharger").addEventListener("click", async () => {
    const f = await fichier(), a = Object.assign(document.createElement("a"), {href: URL.createObjectURL(f), download: f.name});
    a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  });
  dlg.querySelector("#img-partager").addEventListener("click", async () => {
    const f = await fichier();
    if (navigator.canShare?.({files: [f]})) { try { await navigator.share({files: [f], title: tete.titre}); } catch {} }
    else dlg.querySelector("#img-telecharger").click();  // ordinateur : pas de feuille de partage pour les fichiers
  });
  dlg.addEventListener("close", () => dlg.remove());
  dlg.showModal();
  maj();
}

document.getElementById("image")?.addEventListener("click", ouvrirPartageImage);
