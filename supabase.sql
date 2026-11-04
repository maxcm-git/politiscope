-- Comptes, élus suivis et alertes (Supabase). À coller en entier dans Supabase > SQL Editor > Run.
-- Peut être relancé sans risque : rien n'est effacé, ce qui existe déjà est mis à jour.
-- Chaque personne ne voit et ne modifie que ses propres données (sécurité au niveau des lignes).
create table if not exists public.suivis (
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  personne text not null,          -- « shard/slug » de la fiche
  libelle jsonb not null,          -- nom, fonction, lieu, photo au moment du suivi
  cree_le timestamptz not null default now(),
  primary key (user_id, personne)
);
alter table public.suivis enable row level security;
drop policy if exists "lire ses suivis" on public.suivis;
drop policy if exists "ajouter ses suivis" on public.suivis;
drop policy if exists "retirer ses suivis" on public.suivis;
create policy "lire ses suivis" on public.suivis for select using (auth.uid() = user_id);
create policy "ajouter ses suivis" on public.suivis for insert with check (auth.uid() = user_id);
create policy "retirer ses suivis" on public.suivis for delete using (auth.uid() = user_id);

-- Alertes par e-mail : désactivées tant que la personne ne coche pas la case sur « Mes élus ».
create table if not exists public.preferences (
  user_id uuid primary key default auth.uid() references auth.users (id) on delete cascade,
  alertes boolean not null default false,
  maj_le timestamptz not null default now()
);
alter table public.preferences enable row level security;
drop policy if exists "lire ses préférences" on public.preferences;
drop policy if exists "créer ses préférences" on public.preferences;
drop policy if exists "modifier ses préférences" on public.preferences;
create policy "lire ses préférences" on public.preferences for select using (auth.uid() = user_id);
create policy "créer ses préférences" on public.preferences for insert with check (auth.uid() = user_id);
create policy "modifier ses préférences" on public.preferences for update using (auth.uid() = user_id);

-- Suppression complète de son propre compte (RGPD, droit à l'effacement) : suivis et préférences partent avec.
create or replace function public.supprimer_mon_compte() returns void
language sql security definer set search_path = '' as $$
  delete from auth.users where id = auth.uid();
$$;
revoke execute on function public.supprimer_mon_compte() from public, anon;
grant execute on function public.supprimer_mon_compte() to authenticated;

-- Liste des destinataires des alertes, lue par la mise à jour automatique (alertes.py) avec un jeton secret.
-- Le jeton n'ouvre que cette liste (e-mail + élu suivi) : pas besoin de la clé « service_role », qui ouvre tout.
create schema if not exists prive;
revoke all on schema prive from public, anon, authenticated;
create table if not exists prive.reglages (cle text primary key, valeur text not null);
insert into prive.reglages values ('jeton_alertes', replace(gen_random_uuid()::text || gen_random_uuid()::text, '-', ''))
  on conflict do nothing;
create or replace function public.alertes_destinataires(jeton text) returns table (email text, personne text)
language sql security definer set search_path = '' as $$
  select u.email::text, s.personne
  from public.suivis s
  join public.preferences p on p.user_id = s.user_id and p.alertes
  join auth.users u on u.id = s.user_id
  where u.email_confirmed_at is not null
    and jeton = (select valeur from prive.reglages where cle = 'jeton_alertes');
$$;
revoke execute on function public.alertes_destinataires(text) from public, authenticated;
grant execute on function public.alertes_destinataires(text) to anon;

-- Dernière ligne : le jeton à copier dans GitHub (Settings > Secrets and variables > Actions > ALERTES_JETON).
select valeur as "jeton à copier dans GitHub (ALERTES_JETON)" from prive.reglages where cle = 'jeton_alertes';
