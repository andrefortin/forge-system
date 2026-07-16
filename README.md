# Forge System

**12 AI agent factories that build, monetize, and distribute books.** Each forge is a standalone Python script with its own specialized agents following the one-agent-per-item pattern.

## Quick Start

```bash
# CLI — run the creative chain locally
cd ~/batcave/forge-system
python3 forge_runner.py run --spark "cozy fantasy tea shop between worlds" --chain creative

# Cloud — start a worker connected to LavinMQ
python3 cloud_worker.py start --forge all
```

## Architecture

```
CREATIVE                    PRODUCTION              DISTRIBUTION
spark → genre               voice → story           audio → merch
world → character           cover → quality         marketing → publish
outline
```

**Every forge:**
- Standalone Python script (~500 lines) + `forge_llm.py` (~150 lines)
- Boss agent (`deepseek-v4-pro`) designs, never executes
- Worker agents (`deepseek-v4-flash`) each create ONE item
- Checker agent (`deepseek-v4-flash`) verifies independently
- Zero dependencies on Pi, Story Forge, or any agent system
- Deployable anywhere: DO droplet, Lambda, Docker, cron

## Repos

| Forge | Repo | Status |
|-------|------|--------|
| spark-forge | [repo](https://github.com/andrefortin/spark-forge) | ✅ |
| genre-forge | [repo](https://github.com/andrefortin/genre-forge) | ✅ |
| world-forge | [repo](https://github.com/andrefortin/world-forge) | ✅ |
| character-forge | [repo](https://github.com/andrefortin/character-forge) | ✅ |
| outline-forge | [repo](https://github.com/andrefortin/outline-forge) | ✅ |
| voice-forge | [repo](https://github.com/andrefortin/voice-forge) | ✅ |
| cover-forge | [repo](https://github.com/andrefortin/cover-forge) | ✅ |
| audio-forge | [repo](https://github.com/andrefortin/audio-forge) | ✅ |
| story-forge | [repo](https://github.com/andrefortin/revenue-forge) | ✅ |
| merch-forge | [repo](https://github.com/andrefortin/merch-forge) | ✅ |
| marketing-forge | [repo](https://github.com/andrefortin/marketing-forge) | ✅ |
| forge-system | [repo](https://github.com/andrefortin/forge-system) | ✅ |

## Model Strategy

| Role | Model | Provider |
|------|-------|----------|
| Boss (design, review) | `deepseek/deepseek-v4-pro` | OpenRouter → Direct fallback |
| Worker (create) | `deepseek/deepseek-v4-flash` | OpenRouter → Direct fallback |
| Checker (verify) | `deepseek/deepseek-v4-flash` | OpenRouter → Direct fallback |

Full book from spark to publish: **~$2-3 total.**

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — Full system design, SaaS phases
- [DEPLOYMENT.md](DEPLOYMENT.md) — Cloud deployment guide
- [TODO.md](TODO.md) — Phase tracking
- [forge_llm.py](forge_llm.py) — Standalone LLM client used by all forges