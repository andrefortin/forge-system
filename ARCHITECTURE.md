# Forge System — Architecture Plan

## The 12-Factory Architecture

Each forge is a standalone project with its own specialized agents following the boss→worker→checker pattern (Nate B Jones, T2/7.5). One agent per item. No agent does two things.

```
                         ┌──────────────────┐
                         │   SPARK FORGE    │ ◀── ENTRY POINT A
                         │  Ideas, concepts │
                         │  what-ifs, hooks │
                         └────────┬─────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           │                      │                      │
    ┌──────┴──────┐       ┌──────┴──────┐       ┌──────┴──────┐
    │   GENRE     │◀──B   │   WORLD     │◀──C   │ CHARACTER   │◀──D
    │   FORGE     │       │   FORGE     │       │   FORGE     │
    │ Container   │       │ Setting     │       │   People    │
    └──────┬──────┘       └──────┬──────┘       └──────┬──────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  │
                         ┌────────┴─────────┐
                         │  OUTLINE FORGE   │
                         │  Plot structure  │
                         └────────┬─────────┘
                                  │
                         ┌────────┴─────────┐
                         │   STORY FORGE    │
                         │  Chapter gen     │
                         │  27 gates        │
                         │  105 techniques  │
                         └────────┬─────────┘
                                  │
    ┌─────────────────────────────┼─────────────────────────────┐
    │                             │                             │
┌───┴───┐                   ┌────┴────┐                   ┌────┴────┐
│ VOICE │                   │ QUALITY │                   │  COVER  │
│ FORGE │                   │  FORGE  │                   │  FORGE  │
│Finger-│                   │27 gates │                   │ Designs │
│prints │                   │standalone│                  │         │
└───────┘                   └─────────┘                   └─────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           │                      │                      │
    ┌──────┴──────┐       ┌──────┴──────┐       ┌──────┴──────┐
    │   AUDIO     │       │   MERCH     │       │ MARKETING   │
    │   FORGE     │       │   FORGE     │       │   FORGE     │
    │ Audiobooks  │       │ Products    │       │ Promotion   │
    └─────────────┘       └─────────────┘       └─────────────┘
```

## Entry Points

The creative spark can enter from any of four entry points. The system does not assume a linear path:

| Entry | Starts With | Example |
|-------|------------|---------|
| **A — Spark** | An idea, hook, what-if | "What if death was a bureaucracy?" |
| **B — Genre** | A genre container | "I want to write cozy fantasy" |
| **C — World** | A setting, place | "A city built on a sleeping god" |
| **D — Character** | A person, voice | "A tea shop owner who can see death coming" |

Any entry point can feed into any other. The system handles this with a shared data format.

## Forge Catalog

| # | Forge | Status | Purpose | Entry Point |
|---|-------|--------|---------|-------------|
| 1 | **Spark** | 🔨 Building | Ideas, hooks, concepts, what-ifs | A |
| 2 | **Genre** | 📋 Planned | Genre contracts, research, tropes | B |
| 3 | **World** | 📋 Planned | Settings, magic systems, geography | C |
| 4 | **Character** | 📋 Planned | People, arcs, relationships, voice | D |
| 5 | **Outline** | 📋 Planned | Plot structure, pacing, beat sheets | — |
| 6 | **Story** | ✅ Exists | Chapter generation, 27 gates, 105 techniques | — |
| 7 | **Voice** | 📋 Planned | Voice fingerprinting, style extraction | — |
| 8 | **Quality** | 📋 Planned | Standalone 27-gate QA pipeline | — |
| 9 | **Cover** | 📋 Planned | Cover design, image generation | — |
| 10 | **Audio** | 📋 Planned | Audiobook production, TTS | — |
| 11 | **Merch** | ✅ Exists | Product creation, storefront sync | — |
| 12 | **Marketing** | 🔨 Building | Promotion, ARCs, signal optimization | — |

## Shared Data Format

Every forge reads and writes a common format. This is how they compose:

```json
{
  "forge_id": "spark-001",
  "type": "concept",
  "title": "The Bureaucratic Wizard's Floating Component Shop",
  "hook": "What if a wizard ran a floating component shop and the bureaucracy was the real villain?",
  "genre_hint": "cozy-fantasy",
  "world_hint": "A floating marketplace above a forgotten city",
  "character_hint": "A wizard who'd rather file paperwork than cast spells",
  "tone": "warm, humorous, slightly absurd",
  "status": "spark",
  "feeds_into": ["genre-forge", "world-forge", "character-forge"]
}
```

## Agent Pattern (One Agent Per Item)

Every forge follows the same pattern:

```
Boss Agent (DeepSeek V4 Pro)
    │  Writes specs, designs, reviews, rules on disputes. Never creates.
    │  Gets V4 Pro for deeper reasoning on complex design tasks.
    │
    ├──→ Worker Agent (DeepSeek V4 Flash)
    │       Creates ONE item (one concept, one world, one character)
    │       V4 Flash is the workhorse — cheap, fast, focused.
    │
    ├──→ Worker Agent (DeepSeek V4 Flash)
    │       Creates another item
    │
    ├──→ Worker Agent (DeepSeek V4 Flash)
    │       Creates another item
    │
    └──→ Checker Agent (DeepSeek V4 Flash)
            Verifies independently. Rejects unless proven correct.
            Escalates disputes to Boss.
```

**Rules:**
- One agent = one item. Never two items per agent.
- Workers execute, never design.
- Boss designs, never executes.
- Checkers verify independently of worker's self-report.
- Every item gets its own verification before being accepted.
- **Model strategy:** DeepSeek V4 Flash via OpenRouter = default workhorse. V4 Pro via OpenRouter = boss tasks. Fallback: DeepSeek Direct API when rate-limited (auto-switch via model-fallback extension).

## Cost Structure

| Forge | Items per Run | Workers | Total Tokens | Est. Cost |
|-------|--------------|---------|-------------|-----------| 
| Spark | 10 concepts | 10 workers + 1 checker | ~50K | ~$0.15 |
| Genre | 1 contract | 1 worker + 1 checker | ~15K | ~$0.05 |
| World | 5 elements | 5 workers + 1 checker | ~30K | ~$0.10 |
| Character | 5 characters | 5 workers + 1 checker | ~30K | ~$0.10 |
| Story | 18 chapters | 18 workers + 18 checkers | ~500K | ~$1.50 |
| Quality | 1 manuscript | 10 gates (LLM) | ~100K | ~$0.30 |

**Full book from spark to publish: ~$2-3** (all DeepSeek, no external models)