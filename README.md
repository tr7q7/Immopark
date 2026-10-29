# Immopark (LMNP Cashflow) — v2

Stack 100 % gratuite : Streamlit Community Cloud (hébergement) + Supabase (base + comptes).

## Mise en place (dans cet ordre)

1. **Supabase > SQL Editor** : coller et exécuter `schema.sql`.
   Vérifie ensuite dans *Table Editor* que `properties` et `profiles` affichent « RLS enabled ».
2. **Supabase > Authentication > URL Configuration** : *Site URL* = l'adresse de ton app Streamlit.
3. **Emails (obligatoire pour que d'autres s'inscrivent)** :
   Supabase > Authentication > SMTP Settings : brancher un SMTP externe gratuit (Resend, Brevo…).
   Sans cela, l'envoi par défaut est limité à 2 emails/heure et aux seuls membres de ton organisation.
4. **Supabase > Authentication > Emails > Templates > « Reset password »** :
   remplacer le lien par le code : `Ton code : {{ .Token }}` (l'app attend ce code).
5. **Streamlit Cloud > Settings > Secrets** :
   ```
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_ANON_KEY = "ta clé anon"
   ```
6. **GitHub > Settings > Secrets > Actions** : ajouter les mêmes `SUPABASE_URL` et `SUPABASE_ANON_KEY`
   pour que `.github/workflows/keepalive.yml` empêche la mise en pause de la base.

## Sauvegardes
Le plan gratuit Supabase n'inclut pas de sauvegardes quotidiennes. Deux filets :
- bouton « Exporter mes données » (CSV) dans l'app, pour chaque utilisateur ;
- toi, en admin : Supabase > Table Editor > Export CSV, à faire régulièrement.
