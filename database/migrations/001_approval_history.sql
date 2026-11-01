-- ============================================================================
-- MIGRATION 001 — approval_history (append-only decision ledger)
--
-- WHY: ai_proposals holds each AI suggestion plus its *latest* status.
-- This table is the permanent, immutable audit log of EVERY decision
-- (approve / reject / edit), including re-decisions. An audit trail you
-- can edit isn't an audit trail, so UPDATE and DELETE are blocked in the
-- database itself — not just politely avoided in code.
--
-- Safe to run more than once (uses IF NOT EXISTS / OR REPLACE).
--
-- HOW TO RUN: Supabase dashboard → SQL Editor → paste → Run.
-- ============================================================================

create table if not exists public.approval_history (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references public.profiles (id) on delete cascade,
    proposal_id  uuid not null references public.ai_proposals (id) on delete cascade,
    action       text not null check (action in ('approve', 'reject', 'edit')),
    notes        text,
    decided_by   text not null default 'user',
    decided_at   timestamptz not null default now()
);

-- Frequently filtered: "show me decisions for this proposal", newest first
create index if not exists idx_approval_history_proposal
    on public.approval_history (proposal_id, decided_at desc);
create index if not exists idx_approval_history_user
    on public.approval_history (user_id, decided_at desc);

-- Append-only guard: any UPDATE or DELETE raises an error, even from the
-- dashboard or service role. History stays history.
create or replace function public.block_approval_historyMutation()
returns trigger language plpgsql as $$
begin
    raise exception 'approval_history is append-only (no % allowed)', TG_OP;
end;
$$;

drop trigger if exists trg_approval_history_guard on public.approval_history;
create trigger trg_approval_history_guard
    before update or delete on public.approval_history
    for each row execute function public.block_approval_historyMutation();

-- Row Level Security: same policy as every other user-owned table.
alter table public.approval_history enable row level security;

drop policy if exists "approval_history_select_own" on public.approval_history;
create policy "approval_history_select_own" on public.approval_history
    for select using (auth.uid() = user_id);

drop policy if exists "approval_history_insert_own" on public.approval_history;
create policy "approval_history_insert_own" on public.approval_history
    for insert with check (auth.uid() = user_id);
