-- ============================================================================
-- show_rls_policies.sql — DIAGNOSTIC (no changes) — paste into Supabase SQL
-- Editor. Purpose: after scripts/verify_db.py reported LEAK rows visible to
-- the anon key, identify every non-owner policy on the affected tables.
--
-- Expected: ONLY *_owner_all policies (auth.uid() = id / user_id).
-- Anything else (e.g. "public read", using (true)) = the reason anon sees
-- rows. Drop those, then re-run scripts/verify_db.py (must print PASS 15x).
-- ============================================================================

select tablename, policyname, cmd,
       qual, with_check, roles
from pg_policies
where schemaname = 'public'
order by tablename, policyname;

-- Also confirm RLS is actually ENABLED everywhere (rls_enabled should be t):
select relname as table_name, relrowsecurity as rls_enabled,
       relforcerowsecurity as forced
from pg_class
join pg_namespace n on n.oid = relnamespace
where nspname = 'public' and relkind = 'r';
