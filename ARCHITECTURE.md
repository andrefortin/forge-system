# Forge System — Architecture Plan

## Dual-Path Architecture

The system is designed for two paths from day one:

```
PATH 1: CLI AGENTIC FLOW (Andre's company — NOW)
  Terminal → forge_runner.py → 12 forges → book published
  Single user, local files, API keys in ~/.bashrc

PATH 2: SaaS PLATFORM (external users — NEXT)
  Web UI → REST API → Job Queue → 12 forges → book published
  Multi-tenant, Supabase, Stripe billing, user API keys
```

Both paths use the same forges underneath. The only difference is how they're invoked.

## SaaS Architecture

```
                         ┌──────────────────────┐
                         │      WEB DASHBOARD    │
                         │  Next.js + HeroUI    │
                         │  User projects,      │
                         │  book progress,       │
                         │  cost tracking        │
                         └──────────┬───────────┘
                                    │ REST API
                         ┌──────────┴───────────┐
                         │      API GATEWAY      │
                         │  FastAPI / Hono       │
                         │  Auth (Supabase)      │
                         │  Rate limiting         │
                         │  API key validation   │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┴───────────┐
                         │     JOB ORCHESTRATOR  │
                         │  Queue (BullMQ/Redis) │
                         │  forge_runner.py      │
                         │  Per-user cost track  │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
        ┌─────┴─────┐         ┌─────┴─────┐         ┌─────┴─────┐
        │  SPARK    │         │  GENRE    │         │   WORLD   │
        │  FORGE    │         │  FORGE    │         │   FORGE   │
        └───────────┘         └───────────┘         └───────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                         [remaining forges...]
                                    │
                         ┌──────────┴───────────┐
                         │    SUPABASE (DB)      │
                         │  Postgres + Auth       │
                         │  User data, books,     │
                         │  forges, billing       │
                         └──────────────────────┘
```

## Multi-Tenant Data Model

Each user has their own namespace. All forge outputs are scoped to a user + project.

```sql
-- Core tables
users (id, email, stripe_customer_id, created_at)
projects (id, user_id, title, genre, status, created_at)
forge_runs (id, project_id, forge_name, status, cost, started_at, finished_at)
forge_outputs (id, forge_run_id, output_type, data JSONB, created_at)
api_keys (id, user_id, provider, key_encrypted, created_at)

-- Billing
subscriptions (id, user_id, tier, status, current_period_end)
usage_events (id, user_id, forge_name, tokens_used, cost, created_at)
```

## Phased Roadmap

### Phase 1: CLI Agentic Flow ✅ IN PROGRESS
- ✅ 11 forges built with scripts
- ✅ forge_runner.py orchestrator
- ✅ One-agent-per-item pattern
- ✅ OpenRouter + Direct fallback
- 📋 End-to-end test
- 📋 Extract quality-forge as standalone

### Phase 2: Internal SaaS (Andre's company)
- Database migration (local files → Supabase)
- REST API layer (FastAPI)
- Web dashboard (Next.js + HeroUI)
- Job queue (BullMQ + Redis)
- Cost tracking per project
- Discord notifications for pipeline events

### Phase 3: Multi-Tenant SaaS (external users)
- User authentication (Supabase Auth)
- Stripe billing integration
- Per-user API key management
- Rate limiting per tier
- Usage-based pricing
- Admin dashboard

### Phase 4: Marketplace
- Public forge templates
- Community genre contracts
- Voice fingerprint marketplace
- Cover design marketplace
- Publishing service marketplace

## Cost Structure (SaaS)

| Tier | Books/Month | Forges | Price |
|------|------------|--------|-------|
| **Free** | 1 | Spark only (10 concepts) | $0 |
| **Creator** | 5 | Creative chain | $29/mo |
| **Author** | 20 | Full pipeline | $79/mo |
| **Publisher** | Unlimited | Full pipeline + priority | $199/mo |

Plus usage-based: $0.50 per 100K tokens over included quota.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js, HeroUI (already in pi skills), Tailwind CSS |
| **API** | FastAPI (Python, matches forge language) or Hono (TypeScript) |
| **Database** | Supabase (Postgres + Auth + Realtime) |
| **Queue** | BullMQ (Redis) — job queue for forge execution |
| **Auth** | Supabase Auth (email/password + OAuth) |
| **Billing** | Stripe (already in pi skills) |
| **Hosting** | DigitalOcean droplet + Vercel (frontend) |
| **Monitoring** | Discord webhooks (already in pi skills) |

## CLI → SaaS Migration Path

Every forge already outputs standardized JSON. The only changes needed:
1. Replace local `data/*.json` with Supabase tables
2. Replace `subprocess.run()` with BullMQ job submission
3. Add API key validation middleware
4. Add user context to every forge run

The forges themselves don't change — they're already isolated, one-agent-per-item, and produce structured output.