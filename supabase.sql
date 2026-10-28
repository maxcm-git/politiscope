-- Comptes et élus suivis (Supabase). À coller une fois dans Supabase > SQL Editor > Run.
-- Chaque personne ne voit et ne modifie que ses propres suivis (sécurité au niveau des lignes).
create table if not exists public.suivis (
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  personne text not null,          -- « shard/slug » de la fiche
  libelle jsonb not null,          -- nom, fonction, lieu, photo au moment du suivi
  cree_le timestamptz not null default now(),
  primary key (user_id, personne)
);
alter table public.suivis enable row level security;
create policy "lire ses suivis" on public.suivis for select using (auth.uid() = user_id);
create policy "ajouter ses suivis" on public.suivis for insert with check (auth.uid() = user_id);
create policy "retirer ses suivis" on public.suivis for delete using (auth.uid() = user_id);
