-- Immopark : schéma Supabase + sécurité (RLS)
-- À exécuter dans Supabase > SQL Editor. Idempotent : peut être relancé sans casse.
-- ATTENTION : compare avec tes tables actuelles avant d'exécuter (le dépôt ne contenait pas de SQL).

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  created_at timestamptz not null default now()
);

create table if not exists public.properties (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  nom text not null default 'Bien',
  prix_achat_total numeric not null default 0,
  loyer numeric not null default 0,
  credit numeric not null default 0,
  assurance numeric not null default 0,
  taxe numeric not null default 0,
  copro numeric not null default 0,
  electricite numeric not null default 0,
  gaz numeric not null default 0,
  imprevu numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists properties_user_id_idx on public.properties(user_id);

-- Si la table existait déjà sans updated_at :
alter table public.properties add column if not exists updated_at timestamptz not null default now();

create or replace function public.set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists properties_set_updated_at on public.properties;
create trigger properties_set_updated_at before update on public.properties
for each row execute function public.set_updated_at();

-- Création automatique du profil à l'inscription (plus besoin de le faire depuis l'app)
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, email) values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_user();

-- Rattrapage des comptes déjà existants
insert into public.profiles (id, email)
select id, email from auth.users
on conflict (id) do nothing;

-- Sécurité : chaque utilisateur ne voit et ne modifie que SES lignes
alter table public.profiles enable row level security;
alter table public.properties enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;
drop policy if exists "profiles_insert_own" on public.profiles;
drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_select_own" on public.profiles for select using ((select auth.uid()) = id);
create policy "profiles_insert_own" on public.profiles for insert with check ((select auth.uid()) = id);
create policy "profiles_update_own" on public.profiles for update using ((select auth.uid()) = id);

drop policy if exists "properties_select_own" on public.properties;
drop policy if exists "properties_insert_own" on public.properties;
drop policy if exists "properties_update_own" on public.properties;
drop policy if exists "properties_delete_own" on public.properties;
create policy "properties_select_own" on public.properties for select using ((select auth.uid()) = user_id);
create policy "properties_insert_own" on public.properties for insert with check ((select auth.uid()) = user_id);
create policy "properties_update_own" on public.properties for update
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "properties_delete_own" on public.properties for delete using ((select auth.uid()) = user_id);
