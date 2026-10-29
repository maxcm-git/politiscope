/* Suivre des élus : compte gratuit + liste des personnes suivies (icône ☆ sur les fiches, page « Mes élus »).
   Deux modes :
   - en ligne : Supabase (comptes et base de données), si config.js définit window.POLITISCOPE_CONFIG = {supabaseUrl, supabaseKey} ;
   - « mode local de test » sinon : compte et suivis gardés dans ce navigateur seulement, rien n'est envoyé.
   La liste des élus suivis peut révéler une opinion politique (donnée sensible, RGPD art. 9) : consentement explicite
   demandé à la création du compte. Table attendue côté Supabase : voir supabase.sql. */
const SUPA_JS = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/+esm";
const CLE_LOCALE = "politiscope.suivi";

const Suivi = {
  mode: "local", sb: null, utilisateur: null, liste: {},  // liste : "shard/slug" -> {prenom, nom, f, lieu, photo}

  async init() {
    const cfg = window.POLITISCOPE_CONFIG || {};
    if (cfg.supabaseUrl && cfg.supabaseKey) {
      try {
        const {createClient} = await import(SUPA_JS);
        this.sb = createClient(cfg.supabaseUrl, cfg.supabaseKey);
        this.mode = "en ligne";
        const {data} = await this.sb.auth.getSession();
        this.utilisateur = data.session?.user ? {email: data.session.user.email, id: data.session.user.id} : null;
        await this.charger();
      } catch { this.mode = "indisponible"; }
    } else {
      const l = this.lireLocal();
      this.utilisateur = l.email ? {email: l.email} : null;
      this.liste = l.items || {};
    }
    this.signaler();
  },
  lireLocal() { try { return JSON.parse(localStorage.getItem(CLE_LOCALE)) || {}; } catch { return {}; } },
  ecrireLocal() { try { localStorage.setItem(CLE_LOCALE, JSON.stringify({email: this.utilisateur?.email, items: this.liste})); } catch {} },
  async charger() {
    if (!this.sb || !this.utilisateur) { this.liste = {}; return; }
    const {data, error} = await this.sb.from("suivis").select("personne, libelle");
    if (!error) this.liste = Object.fromEntries(data.map(r => [r.personne, r.libelle]));
  },
  est(id) { return id in this.liste; },
  nombre() { return Object.keys(this.liste).length; },

  async creerCompte(email, mdp) {
    if (this.mode !== "en ligne") { this.utilisateur = {email}; this.ecrireLocal(); this.signaler(); return {ok: true}; }
    // Retour sur ce site après le lien de confirmation (adresse à autoriser dans Supabase : Redirect URLs).
    const {data, error} = await this.sb.auth.signUp({email, password: mdp,
      options: {emailRedirectTo: location.origin + location.pathname}});
    if (error) return {erreur: error.message};
    if (!data.session) return {ok: true, verifier: true};  // e-mail de confirmation envoyé par Supabase
    this.utilisateur = {email, id: data.user.id};
    this.signaler();
    return {ok: true};
  },
  async connexion(email, mdp) {
    if (this.mode !== "en ligne") { this.utilisateur = {email}; this.liste = this.lireLocal().items || {}; this.ecrireLocal(); this.signaler(); return {ok: true}; }
    const {data, error} = await this.sb.auth.signInWithPassword({email, password: mdp});
    if (error) return {erreur: error.message};
    this.utilisateur = {email, id: data.user.id};
    await this.charger();
    this.signaler();
    return {ok: true};
  },
  async deconnexion() {
    if (this.sb) await this.sb.auth.signOut();
    this.utilisateur = null;
    if (this.mode !== "en ligne") { this.liste = {}; try { localStorage.removeItem(CLE_LOCALE); } catch {} } else this.liste = {};
    this.signaler();
  },
  async basculer(id, info) {
    const suivre = !this.est(id);
    if (suivre) this.liste[id] = info; else delete this.liste[id];
    if (this.mode === "en ligne") {
      const r = suivre ? await this.sb.from("suivis").insert({user_id: this.utilisateur.id, personne: id, libelle: info})
        : await this.sb.from("suivis").delete().eq("personne", id);
      if (r.error) { if (suivre) delete this.liste[id]; else this.liste[id] = info; return false; }
    } else this.ecrireLocal();
    this.signaler();
    return true;
  },
  // Met à jour l'onglet « Mes élus » et le bandeau.
  signaler() {
    const n = this.nombre(), onglet = document.querySelector('nav.tabs a[data-r="suivis"]');
    if (onglet) onglet.textContent = this.utilisateur ? `Mes élus${n ? ` (${n})` : ""}` : "Mes élus";
    const b = document.getElementById("bandeau-suivi");
    let ferme = false;
    try { ferme = localStorage.getItem("politiscope.bandeau") === "ferme"; } catch {}
    if (b) b.hidden = ferme || (this.utilisateur && n > 0);
  },
};

// Bouton ☆ sur une fiche : suivre / ne plus suivre ; sans compte, renvoie vers la page de connexion puis revient.
function boutonSuivi(id, p) {
  const b = document.querySelector(`[data-suivi="${CSS.escape(id)}"]`);
  if (!b) return;
  const info = {prenom: p.prenom, nom: p.nom, f: p.m[0][1], lieu: p.m[0][3], photo: p.photo || ""};
  const peindre = () => { const on = Suivi.est(id);
    b.setAttribute("aria-pressed", on); b.innerHTML = `${on ? "★" : "☆"} <span>${on ? "Suivi" : "Suivre"}</span>`;
    b.title = on ? "Ne plus suivre" : "Suivre cet élu (compte gratuit)"; };
  peindre();
  if (Suivi.aSuivre === id && Suivi.utilisateur) {
    Suivi.aSuivre = null;
    if (!Suivi.est(id)) Suivi.basculer(id, info).then(peindre);
  }
  b.addEventListener("click", async () => {
    if (!Suivi.utilisateur) { location.hash = `#/suivis?p=${encodeURIComponent(id)}`; return; }
    b.disabled = true;
    await Suivi.basculer(id, info);
    b.disabled = false;
    peindre();
  });
}

async function pageSuivis(qs, j) {
  setTab("suivis");
  const apres = new URLSearchParams(qs || "").get("p");  // fiche à suivre après connexion
  if (!Suivi.utilisateur) {
    app.innerHTML = `<div class="lieu-h" style="margin-top:26px"><div class="kicker">Gratuit</div><h1>Suivez vos élus</h1></div>
      <ul class="puces" style="max-width:640px"><li>Touchez <b>☆ Suivre</b> sur la fiche d'un élu pour l'ajouter à <b>Mes élus</b>.</li>
        <li>Retrouvez-les tous sur une seule page, depuis n'importe quel appareil.</li>
        <li>Compte gratuit : une adresse e-mail et un mot de passe, rien d'autre.</li></ul>
      ${Suivi.mode !== "en ligne" ? `<p class="encart" style="max-width:640px"><b>Mode local de test.</b> Aucun service de comptes n'est branché :
        le compte et les élus suivis restent dans ce navigateur, rien n'est envoyé.</p>` : ""}
      <form class="formulaire" id="f-compte" style="max-width:420px">
        <label>Adresse e-mail<input type="email" name="email" required autocomplete="email"></label>
        <label>Mot de passe (8 caractères au moins)<input type="password" name="mdp" minlength="8" required autocomplete="current-password"></label>
        <label class="case"><input type="checkbox" name="accord" required> J'accepte que Politiscope enregistre mon adresse e-mail et la liste des
          élus que je suis, pour me les afficher. Je peux tout supprimer à tout moment.</label>
        <div class="actions-lieu"><button class="btn" name="action" value="creer">Créer mon compte</button>
          <button class="btn ghost" name="action" value="connexion" formnovalidate>J'ai déjà un compte</button></div>
        <p id="f-msg" class="muted" role="status"></p></form>`;
    const f = document.getElementById("f-compte");
    f.addEventListener("submit", async e => {
      e.preventDefault();
      const creer = e.submitter?.value === "creer", d = new FormData(f), msg = document.getElementById("f-msg");
      if (!d.get("email") || String(d.get("mdp")).length < 8) { msg.textContent = "Adresse e-mail et mot de passe de 8 caractères au moins."; return; }
      if (creer && !d.get("accord")) { msg.textContent = "Cochez la case d'accord pour créer le compte."; return; }
      msg.textContent = "Un instant…";
      const r = creer ? await Suivi.creerCompte(d.get("email"), d.get("mdp")) : await Suivi.connexion(d.get("email"), d.get("mdp"));
      if (r.erreur) { msg.textContent = `Échec : ${r.erreur}`; return; }
      if (r.verifier) { msg.textContent = "Compte créé : ouvrez l'e-mail de confirmation, puis revenez vous connecter."; return; }
      Suivi.aSuivre = apres;  // l'élu qui a mené ici est suivi dès le retour sur sa fiche
      location.hash = apres ? `#/p/${apres}` : "#/suivis";
    });
    return;
  }
  const l = Object.entries(Suivi.liste).map(([id, x]) => { const [shard, ...s] = id.split("/");
    return {shard, slug: s.join("/"), nom: x.nom, prenom: x.prenom, f: x.f, lieu: x.lieu, photo: x.photo}; });
  app.innerHTML = `<div class="lieu-h" style="margin-top:26px"><div class="kicker">${esc(Suivi.utilisateur.email)}${Suivi.mode !== "en ligne" ? " · mode local de test" : ""}</div>
      <h1>Mes élus</h1></div>
    ${l.length ? `<p class="muted">${l.length} élu${l.length > 1 ? "s" : ""} suivi${l.length > 1 ? "s" : ""}, de A à Z. Touchez une carte pour ouvrir la fiche.</p>
      <div id="suivis-liste">${visages(tri(l))}</div>`
      : `<p class="vide">Vous ne suivez encore personne. Ouvrez la fiche d'un élu et touchez <b>☆ Suivre</b>.</p>`}
    <div class="actions-lieu"><a class="btn" href="#/annuaire">Trouver un élu</a><button class="btn ghost" id="deco">Se déconnecter</button>
      ${l.length ? `<button class="btn ghost" id="vider">Ne plus suivre personne</button>` : ""}</div>
    ${src("Prochaine étape prévue : être prévenu par e-mail quand un élu suivi vote, change de fonction ou publie une déclaration.")}`;
  document.getElementById("deco").addEventListener("click", async () => { await Suivi.deconnexion(); pageSuivis("", j); });
  document.getElementById("vider")?.addEventListener("click", async () => {
    for (const id of Object.keys(Suivi.liste)) await Suivi.basculer(id, Suivi.liste[id]);
    pageSuivis("", j);
  });
}

document.getElementById("bandeau-fermer")?.addEventListener("click", () => {
  try { localStorage.setItem("politiscope.bandeau", "ferme"); } catch {}
  document.getElementById("bandeau-suivi").hidden = true;
});
