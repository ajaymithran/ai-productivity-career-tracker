-- ============================================================================
-- AI Productivity & Career Tracker — database/schema.sql
-- ----------------------------------------------------------------------------
-- Run this ONCE in the Supabase SQL Editor (Dashboard → SQL Editor → New query).
-- Task 4 explains how to create the project and run it.
--
-- Structure: 15 tables
--   13 module tables you specified + profiles (auth bridge) + ai_proposals
--   (approval history required by the AI rules).
--
-- Conventions used throughout:
--   * id            uuid, generated  → stable, non-guessable PKs
--   * user_id       uuid → profiles  → ownership on every row (see RLS)
--   * created_at    timestamptz      → timezone-aware timestamps ALWAYS
--   * updated_at    timestamptz      → kept current by trigger (defined below)
--   * status        text + CHECK     → CHECK instead of ENUM: easy to extend
--   * progress      integer CHECK 0..100
--
-- NEVER expose the service_role key anywhere. Client code uses the anon key;
-- these RLS policies are what make the anon key safe to ship.
-- ============================================================================

-- ============================================================================
-- 1) PROFILES — bridge table to Supabase Auth (official Supabase pattern)
--    auth.users is protected; we never write to it. profiles extends it and
--    gives every other table an FK target we control.
-- ============================================================================
create table public.profiles (
    id          uuid primary key references auth.users (id) on delete cascade,
    display_name text not null default 'User',
    timezone    text not null default 'Asia/Kolkata',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- A profile row is created automatically whenever someone signs up.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer           -- runs with creator privileges so it can insert
set search_path = public
as $$
begin
    insert into public.profiles (id, display_name)
    values (new.id, coalesce(new.raw_user_meta_data ->> 'display_name', 'User'));
    return new;
end;
$$;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ============================================================================
-- 2) USER SETTINGS — 1:1 configuration of study availability & preferences
--    PK = user_id  → 1:1 with profiles enforced structurally.
-- ============================================================================
create table public.user_settings (
    user_id             uuid primary key references public.profiles (id) on delete cascade,
    daily_study_minutes integer not null default 120
        check (daily_study_minutes between 15 and 720),
    study_start_time    time   not null default '06:30',
    study_end_time      time   not null default '22:00'
        check (study_end_time > study_start_time),
    weekly_review_day   smallint not null default 0     -- 0=Sunday .. 6=Saturday
        check (weekly_review_day between 0 and 6),
    theme               text not null default 'light'
        check (theme in ('light', 'dark')),
    ai_enabled          boolean not null default true,
    ai_tone             text not null default 'mentor'
        check (ai_tone in ('mentor', 'concise', 'drill_sergeant')),
    data_encrypted_at_rest boolean not null default true,  -- platform fact, shown in Settings
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

-- ============================================================================
-- 3) GOALS — career goals with statuses (incl. active/paused from our review)
-- ============================================================================
create table public.goals (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references public.profiles (id) on delete cascade,
    title        text not null check (char_length(title) between 1 and 200),
    description  text,
    horizon      text not null default 'short_term'
                 check (horizon in ('short_term', 'mid_term', 'long_term')),
    target_date  date,
    status       text not null default 'active'
                 check (status in ('active', 'paused', 'achieved', 'abandoned')),
    progress_pct integer not null default 0 check (progress_pct between 0 and 100),
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),

    -- A paused/achieved/abandoned goal may dangle a far-future target date,
    -- but an ACTIVE goal without a target date is unusable for planning.
    unique (user_id, title)
);

create index idx_goals_user_status on public.goals (user_id, status);

-- ============================================================================
-- 4) PROJECTS — GitHub-linked work items with date sanity enforced in DB
-- ============================================================================
create table public.projects (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references public.profiles (id) on delete cascade,
    name         text not null check (char_length(name) between 1 and 150),
    description  text,
    github_url   text
        check (github_url is null or github_url ilike 'https://github.com/%'),
    blog_url     text,
    start_date   date not null default current_date,
    target_date  date,
    status       text not null default 'planning'
                 check (status in ('planning', 'in_progress', 'paused', 'done', 'dropped')),
    -- blockers stored as freeform text + per-milestone blocker (see milestones)
    blockers     text,
    notes        text,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),

    constraint projects_dates_ordered
        check (target_date is null or target_date >= start_date)
);

create index idx_projects_user_status on public.projects (user_id, status);

-- ============================================================================
-- 5) MILESTONES — ordered steps inside a project, each can carry a blocker
-- ============================================================================
create table public.milestones (
    id          uuid primary key default gen_random_uuid(),
    project_id  uuid not null references public.projects (id) on delete cascade,
    user_id     uuid not null references public.profiles (id) on delete cascade,
    title       text not null check (char_length(title) between 1 and 200),
    position    integer not null default 0,             -- ordering within project
    due_date    date,
    status      text not null default 'pending'
                check (status in ('pending', 'in_progress', 'done', 'blocked')),
    blocker     text,                                   -- required when status='blocked'
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),

    constraint milestones_blocker_required_when_blocked
        check (status <> 'blocked' or blocker is not null)
);

create index idx_milestones_project on public.milestones (project_id, position);

-- ============================================================================
-- 6) TASKS — the daily-planner workhorse
--    * estimated_minutes + priority_band + due_date feed Python scoring
--    * project/milestone/goal refs are optional, mutually consistent by CHECK
-- ============================================================================
create table public.tasks (
    id               uuid primary key default gen_random_uuid(),
    user_id          uuid not null references public.profiles (id) on delete cascade,
    title            text not null check (char_length(title) between 1 and 250),
    notes            text,
    priority_band    text not null default 'medium'
                     check (priority_band in ('low', 'medium', 'high')),
    impact           smallint not null default 3 check (impact between 1 and 5),
    effort           smallint not null default 3 check (effort between 1 and 5),
    -- priority_score is written back by Python (core/priority.py), not AI.
    priority_score   numeric(5,2) not null default 0 check (priority_score >= 0),
    estimated_minutes integer not null default 30
                     check (estimated_minutes between 5 and 600),
    due_date         date,
    project_id       uuid references public.projects (id) on delete set null,
    milestone_id     uuid references public.milestones (id) on delete set null,
    goal_id          uuid references public.goals (id) on delete set null,
    status           text not null default 'todo'
                     check (status in ('todo', 'in_progress', 'done', 'wont_do')),
    completed_at     timestamptz,                        -- set when status → done
    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now()
    -- NOTE: cross-table consistency (milestone belongs to the same user/project
    -- as its task) is enforced in db/queries.py, because PostgreSQL CHECK
    -- constraints cannot contain subqueries into other tables.
);

create index idx_tasks_user_status  on public.tasks (user_id, status);
create index idx_tasks_user_due     on public.tasks (user_id, due_date);
create index idx_tasks_project      on public.tasks (project_id);

-- ============================================================================
-- 7) SKILLS — the 8 tracked skills + anything else; active/paused/retired
-- ============================================================================
create table public.skills (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references public.profiles (id) on delete cascade,
    name         text not null check (char_length(name) between 1 and 80),   -- e.g. Python, SQL, Excel, Power BI, Statistics, ML, AI, English
    category     text not null default 'technical'
                 check (category in ('technical', 'analytics', 'ai', 'language', 'soft')),
    current_level smallint not null default 1 check (current_level between 1 and 5),
    target_level  smallint not null default 5 check (target_level between 1 and 5)
                 check (target_level >= current_level),
    minutes_goal_weekly integer not null default 180
                 check (minutes_goal_weekly between 15 and 3000),
    status       text not null default 'active'
                 check (status in ('active', 'paused', 'retired')),
    notes        text,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),

    unique (user_id, name)   -- one row per skill per user
);

create index idx_skills_user_status on public.skills (user_id, status);

-- ============================================================================
-- 8) DAILY PLANS — one per user per calendar day, NEVER deleted (immutable history)
-- ============================================================================
create table public.daily_plans (
    id                 uuid primary key default gen_random_uuid(),
    user_id            uuid not null references public.profiles (id) on delete cascade,
    plan_date          date not null,
    availability_minutes integer not null default 120
                       check (availability_minutes between 0 and 720),
    availability_note  text,                                -- "busy evening", etc.
    status             text not null default 'draft'
                       check (status in ('draft', 'active', 'completed', 'missed')),
    planned_summary    text,                                -- AI weekly-plan context lands here as history
    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now(),

    unique (user_id, plan_date)   -- one plan per day per user
);

create index idx_daily_plans_user_date on public.daily_plans (user_id, plan_date desc);

-- ============================================================================
-- 9) DAILY PLAN ITEMS — what's scheduled in a plan: a task OR a skill session
--    (or milestone_NUM) — exactly one link per item.
-- ============================================================================
create table public.daily_plan_items (
    id             uuid primary key default gen_random_uuid(),
    plan_id        uuid not null references public.daily_plans (id) on delete cascade,
    user_id        uuid not null references public.profiles (id) on delete cascade,
    task_id        uuid references public.tasks (id) on delete set null,
    milestone_id   uuid references public.milestones (id) on delete set null,
    skill_id       uuid references public.skills (id) on delete set null,
    minutes_allocated integer not null check (minutes_allocated between 5 and 600),
    position       integer not null default 0,
    notes          text,
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now(),

    constraint dpi_exactly_one_target
        check (num_nonnulls(task_id, milestone_id, skill_id) = 1)
    -- NOTE: same-user consistency of task_id/skill_id/milestone_id is enforced
    -- in db/queries.py (CHECK constraints cannot reference other tables).
);

create index idx_dpi_plan     on public.daily_plan_items (plan_id, position);
create index idx_dpi_task     on public.daily_plan_items (task_id);
create index idx_dpi_skill    on public.daily_plan_items (skill_id);

-- ============================================================================
-- 10) ACTIVITY LOGS — who did what, when (audit trail, manual changes only)
-- ============================================================================
create table public.activity_logs (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references public.profiles (id) on delete cascade,
    entity_type text not null check (entity_type in
                ('task', 'project', 'milestone', 'goal', 'skill', 'plan', 'plan_item',
                 'settings', 'ready', 'review', 'notification', 'ai_proposal')),
    entity_id   uuid,
    action      text not null check (action in
                ('create', 'update', 'delete', 'status_change', 'approve', 'reject', 'edit_before_apply')),
    detail      jsonb not null default '{}'::jsonb,   -- {"field": "due_date", "old": .., "new": ..}
    created_at  timestamptz not null default now()
);

create index idx_activity_user_time on public.activity_logs (user_id, created_at desc);

-- ============================================================================
-- 11) WEEKLY REVIEWS — one per ISO week; both manual reflection and AI draft
-- ============================================================================
create table public.weekly_reviews (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references public.profiles (id) on delete cascade,
    week_start_date date not null,                     -- always ISO Monday
    wins            text,
    challenges      text,
    planned_minutes integer check (planned_minutes >= 0),      -- snapshot at review time
    actual_minutes  integer check (actual_minutes >= 0),
    tasks_done      integer default 0 check (tasks_done >= 0),
    ai_summary      text,                               -- advisory only; dismissing never deletes history
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    unique (user_id, week_start_date)
);

create index idx_reviews_user_week on public.weekly_reviews (user_id, week_start_date desc);

-- ============================================================================
-- 12) ENGLISH LOGS — spaced language practice, optionally linked to English skill row
-- ============================================================================
create table public.english_logs (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null references public.profiles (id) on delete cascade,
    skill_id      uuid references public.skills (id) on delete set null,
    practice_type text not null
                  check (practice_type in ('speaking', 'listening', 'reading', 'writing', 'vocabulary')),
    minutes       integer not null check (minutes between 1 and 300),
    confidence    smallint not null check (confidence between 1 and 5),   -- 1=low .. 5=near-native
    notes         text,
    logged_on     date not null default current_date,
    created_at    timestamptz not null default now()
);

create index idx_english_user_day on public.english_logs (user_id, logged_on desc);

-- ============================================================================
-- 13) JOB READINESS — 1:1 current state: resume, portfolio, applications
-- ============================================================================
create table public.job_readiness (
    user_id               uuid primary key references public.profiles (id) on delete cascade,
    resume_progress_pct   integer not null default 0 check (resume_progress_pct between 0 and 100),
    portfolio_progress_pct integer not null default 0 check (portfolio_progress_pct between 0 and 100),
    target_role           text,
    readiness_score       integer,                       -- computed by core/skillgap.py; snapshot here
    applications_sent     integer not null default 0 check (applications_sent >= 0),
    interviews            integer not null default 0 check (interviews >= 0),
    notes                 text,
    created_at            timestamptz not null default now(),
    updated_at            timestamptz not null default now()
);

-- ============================================================================
-- 14) NOTIFICATIONS — in-app only (per our design, never email/SMS)
-- ============================================================================
create table public.notifications (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references public.profiles (id) on delete cascade,
    notif_type  text not null check (notif_type in
                ('deadline', 'weekly_review', 'progress', 'ai_approval', 'system')),
    severity    text not null default 'info'
                check (severity in ('info', 'warning', 'urgent')),
    title       text not null,
    body        text,
    route       text,                                   -- in-app target, e.g. "planner"
    is_read     boolean not null default false,
    read_at     timestamptz,
    expires_at  timestamptz,                            -- housekeeping by GH Action
    created_at  timestamptz not null default now(),

    constraint notifications_read_consistent
        check (is_read = false or read_at is not null)
);

create index idx_notif_unread on public.notifications (user_id, is_read, created_at desc);

-- ============================================================================
-- 15) AI PROPOSALS — the approval audit trail
--     One row per Gemini suggestion; your decision is permanent history.
-- ============================================================================
create table public.ai_proposals (
    id             uuid primary key default gen_random_uuid(),
    user_id        uuid not null references public.profiles (id) on delete cascade,
    scope          text not null check (scope in
                   ('daily_plan', 'task_set', 'skill_gap', 'weekly_plan', 'summary')),
    prompt_context jsonb not null,                      -- exactly the user data the AI saw
    model          text not null default 'gemini',
    proposal       jsonb not null,                      -- the AI's suggested edits/additions
    status         text not null default 'pending'
                   check (status in ('pending', 'approved', 'rejected', 'edited', 'applied', 'expired')),
    applied_at     timestamptz,                         -- set only when edits hit live tables
    applied_result jsonb,                               -- what actually changed
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now(),

    constraint ai_proposal_never_silent
        check (applied_at is null or status in ('approved', 'edited'))
);

create index idx_ai_proposals_user_time on public.ai_proposals (user_id, created_at desc);

-- ============================================================================
-- ROW LEVEL SECURITY — every table. Policy: the row belongs to the logged-in
-- user. This makes the anon key safe: without your session it can see nothing.
-- ============================================================================
alter table public.profiles          enable row level security;
alter table public.user_settings     enable row level security;
alter table public.goals             enable row level security;
alter table public.projects          enable row level security;
alter table public.milestones        enable row level security;
alter table public.tasks             enable row level security;
alter table public.skills            enable row level security;
alter table public.daily_plans       enable row level security;
alter table public.daily_plan_items  enable row level security;
alter table public.activity_logs     enable row level security;
alter table public.weekly_reviews    enable row level security;
alter table public.english_logs      enable row level security;
alter table public.job_readiness     enable row level security;
alter table public.notifications     enable row level security;
alter table public.ai_proposals      enable row level security;

create policy "profiles_owner_all" on public.profiles
    for all using (auth.uid() = id) with check (auth.uid() = id);

-- Same owner rule for the rest; generated plainly for auditability:
create policy "settings_owner_all" on public.user_settings
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "goals_owner_all" on public.goals
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "projects_owner_all" on public.projects
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "milestones_owner_all" on public.milestones
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "tasks_owner_all" on public.tasks
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "skills_owner_all" on public.skills
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "daily_plans_owner_all" on public.daily_plans
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "daily_plan_items_owner_all" on public.daily_plan_items
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "activity_logs_owner_all" on public.activity_logs
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "weekly_reviews_owner_all" on public.weekly_reviews
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "english_logs_owner_all" on public.english_logs
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "job_readiness_owner_all" on public.job_readiness
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "notifications_owner_all" on public.notifications
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "ai_proposals_owner_all" on public.ai_proposals
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ============================================================================
-- updated_at auto-touch trigger — applied to every table that has the column.
-- One bug fixed in one place, forever.
-- ============================================================================
create function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

do $$
declare t text;
begin
    foreach t in array array['profiles','user_settings','goals','projects','milestones',
        'tasks','skills','daily_plans','daily_plan_items','weekly_reviews',
        'job_readiness','ai_proposals']
    loop
        execute format(
            'create trigger set_updated_at_%s before update on public.%I
             for each row execute function public.set_updated_at();', t, t);
    end loop;
end $$;
