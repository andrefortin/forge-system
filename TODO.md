# Forge System — TODO & Status Report
# Updated 2026-07-15

## Phase 1: Build All Forges ✅ COMPLETE

All 12 repos built, scripts written, LLM decoupled, pushed to GitHub.

| # | Forge | Repo | Script | forge_llm | Status |
|---|-------|------|--------|-----------|--------|
| 1 | spark-forge | github.com/andrefortin/spark-forge | spark.py | ✅ | ✅ |
| 2 | genre-forge | github.com/andrefortin/genre-forge | genre.py | ✅ | ✅ |
| 3 | world-forge | github.com/andrefortin/world-forge | world.py | ✅ | ✅ |
| 4 | character-forge | github.com/andrefortin/character-forge | character.py | ✅ | ✅ |
| 5 | outline-forge | github.com/andrefortin/outline-forge | outline.py | ✅ | ✅ |
| 6 | voice-forge | github.com/andrefortin/voice-forge | voice.py | ✅ | ✅ |
| 7 | cover-forge | github.com/andrefortin/cover-forge | cover.py | ✅ | ✅ |
| 8 | audio-forge | github.com/andrefortin/audio-forge | audio.py | ✅ | ✅ |
| 9 | story-forge | github.com/andrefortin/revenue-forge | book_factory.py | N/A | ✅ |
| 10 | merch-forge | github.com/andrefortin/merch-forge | generate_product.py | N/A | ✅ |
| 11 | marketing-forge | github.com/andrefortin/marketing-forge | signal_optimizer.py | N/A | ✅ |
| — | forge-system | github.com/andrefortin/forge-system | forge_runner.py | ✅ | ✅ |

## Phase 1b: Decouple from Pi/Story Forge ✅ COMPLETE

- ✅ All 8 forges decoupled — zero cross-project imports
- ✅ Each forge has standalone forge_llm.py (~150 lines)
- ✅ Pure urllib, no pip dependencies beyond stdlib
- ✅ OpenRouter primary → DeepSeek Direct fallback (auto)

## Phase 2: Pipeline Orchestrator ✅ COMPLETE

- ✅ forge_runner.py — CLI conductor, runs full chain
- ✅ cloud_worker.py — LavinMQ consumer, cloud deployment
- ✅ Dry-run mode, resume from checkpoint, status tracking
- ✅ DEPLOYMENT.md — systemd, NGINX, FastAPI configs

## Phase 3: End-to-End Test 📋 PENDING

Run the chain with a real spark and verify:
- [ ] spark → genre → world → character → outline (creative chain)
- [ ] Each forge reads from previous forge's output
- [ ] Cost tracked per forge + total
- [ ] Quality scores at each stage

## Phase 4: Extract Quality Forge 📋 PENDING

27 gates extracted from story-forge as standalone QA service.
- Own agents (checker agents already built as gate functions)
- Own repo: github.com/andrefortin/quality-forge
- Feeds into: story-forge, merch-forge, marketing-forge

## Phase 5: Internal SaaS (Andre's company) 📋 PLANNED

- [ ] Database migration (local files → Supabase)
- [ ] REST API layer (FastAPI on DO droplet)
- [ ] Web dashboard (Next.js + HeroUI on Vercel)
- [ ] Job queue (LavinMQ — credentials ready)
- [ ] Per-project cost tracking
- [ ] Deploy to DO droplet

## Phase 6: Story Forge Upgrades 📋 PLANNED

- [ ] Outline stress test: implement remaining 7 checks (currently 1 of 8)
- [ ] Gate 2.23: Worldbuilding Consistency
- [ ] Gate 2.24: Character Desire Depth
- [ ] Gate 2.25: Audiobook Readiness

## Phase 7: Multi-Tenant SaaS 📋 PLANNED

- [ ] Supabase Auth (user accounts)
- [ ] Stripe billing (already in pi skills)
- [ ] Per-user API key management
- [ ] Rate limiting per tier
- [ ] Usage-based pricing

## Knowledge Pipeline Status

| Backlog | Total | Integrated | Remaining |
|---------|-------|------------|-----------|
| 2026-07-14 batch | 168 | 52 | 116 |
| 2026-07-15 batch | 17 | 9 | 0 |
| knowledge-audit.json | 52 entries | 42 wired | 6 docs-only |