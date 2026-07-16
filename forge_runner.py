#!/usr/bin/env python3
"""
Forge Runner — Pipeline Orchestrator
Conducts the 12-factory system. Runs the full chain from spark to publish.

Architecture:
    Runner calls each forge in sequence. Each forge is a standalone subprocess
    with its own agents. The runner's job is routing, not creating.

    spark → genre → world → character → outline → story → quality → cover → audio → publish

Usage:
    python3 forge_runner.py run --spark "cozy fantasy tea shop between worlds"
    python3 forge_runner.py run --spark-file /path/to/spark.json
    python3 forge_runner.py status --run-id run-001
    python3 forge_runner.py resume --run-id run-001
"""

import sys, os, json, time, uuid, subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

# ── Paths ───────────────────────────────────────────────────────

BATCAVE = os.path.expanduser("~/batcave")
FORGES = {
    "spark":    os.path.join(BATCAVE, "spark-forge"),
    "genre":    os.path.join(BATCAVE, "genre-forge"),
    "world":    os.path.join(BATCAVE, "world-forge"),
    "character": os.path.join(BATCAVE, "character-forge"),
    "outline":  os.path.join(BATCAVE, "outline-forge"),
    "voice":    os.path.join(BATCAVE, "voice-forge"),
    "cover":    os.path.join(BATCAVE, "cover-forge"),
    "audio":    os.path.join(BATCAVE, "audio-forge"),
    "story":    os.path.join(BATCAVE, "story-forge"),
    "merch":    os.path.join(BATCAVE, "merch-forge"),
    "marketing": os.path.join(BATCAVE, "marketing-forge"),
}

RUNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")
os.makedirs(RUNS_DIR, exist_ok=True)

# ── Pipeline Definition ─────────────────────────────────────────

CREATIVE_CHAIN = ["spark", "genre", "world", "character", "outline"]
PRODUCTION_CHAIN = ["voice", "story", "cover"]
DISTRIBUTION_CHAIN = ["audio", "merch", "marketing"]

FULL_CHAIN = CREATIVE_CHAIN + PRODUCTION_CHAIN + DISTRIBUTION_CHAIN

FORGE_LABELS = {
    "spark": "⚡ Spark Forge — Idea Engine",
    "genre": "📚 Genre Forge — Category Researcher",
    "world": "🌍 World Forge — Setting Builder",
    "character": "👤 Character Forge — People Builder",
    "outline": "📐 Outline Forge — Plot Structure",
    "voice": "🎤 Voice Forge — Voice Fingerprint",
    "story": "📖 Story Forge — Chapter Generation",
    "cover": "🎨 Cover Forge — Cover Design",
    "audio": "🎧 Audio Forge — Audiobook Production",
    "merch": "🏪 Merch Forge — Product Creation",
    "marketing": "📢 Marketing Forge — Promotion Engine",
}

# ── State Management ────────────────────────────────────────────

def create_run(params: dict) -> dict:
    """Initialize a new pipeline run."""
    run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run = {
        "run_id": run_id,
        "status": "created",
        "params": params,
        "chain": params.get("chain", FULL_CHAIN),
        "current_forge": None,
        "completed": [],
        "failed": None,
        "results": {},
        "cost": {"total": 0, "per_forge": {}},
        "started": datetime.now().isoformat(),
        "finished": None,
    }
    save_run(run)
    return run


def save_run(run: dict):
    path = os.path.join(RUNS_DIR, f"{run['run_id']}.json")
    with open(path, 'w') as f:
        json.dump(run, f, indent=2, default=str)


def load_run(run_id: str) -> Optional[dict]:
    path = os.path.join(RUNS_DIR, f"{run_id}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def list_runs() -> list:
    runs = []
    for f in sorted(os.listdir(RUNS_DIR), reverse=True):
        if f.endswith('.json'):
            with open(os.path.join(RUNS_DIR, f)) as fh:
                runs.append(json.load(fh))
    return runs


# ── Forge Execution ─────────────────────────────────────────────

def find_spark_data(run: dict) -> Optional[dict]:
    """Find the output from Spark Forge for this run."""
    spark_dir = os.path.join(FORGES["spark"], "data")
    vault_path = os.path.join(spark_dir, "concept_vault.json")
    if os.path.exists(vault_path):
        with open(vault_path) as f:
            vault = json.load(f)
        # Return the most recent spark
        if vault:
            newest = max(vault.values(), key=lambda x: x.get('created', ''))
            return newest
    return None


def find_genre_data(run: dict, spark_data: dict = None) -> Optional[dict]:
    """Find genre contract."""
    genre = spark_data.get("genre_hint", "fiction") if spark_data else run.get("params", {}).get("genre", "fiction")
    genre_dir = os.path.join(FORGES["genre"], "data")
    path = os.path.join(genre_dir, f"{genre}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def find_world_data(run: dict) -> Optional[dict]:
    """Find most recent world build."""
    world_dir = os.path.join(FORGES["world"], "data")
    worlds = [f for f in os.listdir(world_dir) if f.startswith("world-") and f.endswith(".json")]
    if worlds:
        newest = sorted(worlds)[-1]
        with open(os.path.join(world_dir, newest)) as f:
            return json.load(f)
    return None


def find_character_data(run: dict) -> Optional[dict]:
    """Find most recent character build."""
    char_dir = os.path.join(FORGES["character"], "data")
    chars = [f for f in os.listdir(char_dir) if f.startswith("char-") and f.endswith(".json")]
    if chars:
        newest = sorted(chars)[-1]
        with open(os.path.join(char_dir, newest)) as f:
            return json.load(f)
    return None


def find_outline_data(run: dict) -> Optional[dict]:
    """Find most recent outline."""
    outline_dir = os.path.join(FORGES["outline"], "data")
    outlines = [f for f in os.listdir(outline_dir) if f.startswith("outline-") and f.endswith(".json")]
    if outlines:
        newest = sorted(outlines)[-1]
        with open(os.path.join(outline_dir, newest)) as f:
            return json.load(f)
    return None


def run_forge(forge_name: str, run: dict) -> dict:
    """Execute a forge. Each forge is called as a subprocess with its own agents."""
    forge_dir = FORGES.get(forge_name)
    if not forge_dir:
        return {"ok": False, "error": f"Unknown forge: {forge_name}"}
    
    start = time.time()
    params = run.get("params", {})
    spark_data = find_spark_data(run)
    title = spark_data.get("title", params.get("title", "Untitled")) if spark_data else params.get("title", "Untitled")
    genre = spark_data.get("genre_hint", params.get("genre", "fiction")) if spark_data else params.get("genre", "fiction")
    
    try:
        if forge_name == "spark":
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "spark.py"), "generate", "--count", "10"]
            if params.get("genre"):
                cmd += ["--genre", params["genre"]]
            if params.get("world_seed"):
                cmd += ["--world", params["world_seed"]]
            if params.get("character_seed"):
                cmd += ["--character", params["character_seed"]]
        
        elif forge_name == "genre":
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "genre.py"), "research", "--genre", genre]
        
        elif forge_name == "world":
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "world.py"), "build"]
            if spark_data:
                cmd += ["--seed", spark_data.get("world_hint", spark_data.get("hook", ""))]
            if genre:
                cmd += ["--genre", genre]
        
        elif forge_name == "character":
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "character.py"), "build"]
            if spark_data:
                cmd += ["--seed", spark_data.get("character_hint", spark_data.get("hook", ""))]
            if genre:
                cmd += ["--genre", genre]
        
        elif forge_name == "outline":
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "outline.py"), "build"]
            cmd += ["--title", title, "--genre", genre, "--chapters", str(params.get("chapters", 18))]
        
        elif forge_name == "voice":
            # Voice Forge needs a prose sample — skip if no sample
            sample = params.get("voice_sample")
            if not sample:
                return {"ok": True, "detail": "No voice sample provided — skipping Voice Forge", "skipped": True}
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "voice.py"), "extract", "--sample", sample]
        
        elif forge_name == "story":
            # Story Forge is called via book_factory.py
            project_id = params.get("project_id", title.lower().replace(" ", "-")[:40])
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "book_factory.py"), project_id, "--phase", "generate"]
        
        elif forge_name == "cover":
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "cover.py"), "design"]
            cmd += ["--title", title, "--genre", genre]
        
        elif forge_name == "audio":
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "audio.py"), "produce"]
            cmd += ["--project", params.get("project_id", "")]
        
        elif forge_name == "merch":
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "generate_product.py"), "--author", params.get("author", "stella-hawthorne")]
        
        elif forge_name == "marketing":
            cmd = [sys.executable, os.path.join(forge_dir, "scripts", "signal_optimizer.py"), "--project", params.get("project_id", "")]
        
        else:
            return {"ok": False, "error": f"No handler for forge: {forge_name}"}
        
        # Run the forge
        print(f"   ⏳ Running: {' '.join(cmd[:5])}...")
        result = subprocess.run(cmd, cwd=forge_dir, capture_output=True, text=True, timeout=300)
        elapsed = round(time.time() - start, 1)
        
        ok = result.returncode == 0
        detail = f"Completed in {elapsed}s"
        
        if not ok and result.stderr:
            detail = result.stderr.strip()[:200]
        
        return {
            "ok": ok,
            "detail": detail,
            "elapsed": elapsed,
            "stdout": result.stdout[:500] if result.stdout else "",
            "stderr": result.stderr[:500] if result.stderr else "",
        }
    
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timeout after 300s", "elapsed": 300}
    except Exception as e:
        return {"ok": False, "error": str(e), "elapsed": round(time.time() - start, 1)}


# ── Pipeline Orchestration ──────────────────────────────────────

def run_pipeline(params: dict, chain: list = None, dry_run: bool = False):
    """Run the full pipeline. spark → genre → world → ... → publish."""
    chain = chain or params.get("chain", FULL_CHAIN)
    run = create_run({**params, "chain": chain})
    
    print(f"\n{'='*70}")
    print(f"  🎼 FORGE RUNNER — Pipeline Orchestrator")
    print(f"  Run: {run['run_id']}")
    print(f"  Chain: {' → '.join(chain)}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*70}")
    
    total_start = time.time()
    
    for i, forge_name in enumerate(chain):
        label = FORGE_LABELS.get(forge_name, forge_name)
        print(f"\n  [{i+1}/{len(chain)}] {label}")
        
        if dry_run:
            print(f"       ⏭️  Dry run — skipping")
            run["completed"].append(forge_name)
            run["results"][forge_name] = {"ok": True, "detail": "Dry run", "skipped": True}
            continue
        
        run["current_forge"] = forge_name
        save_run(run)
        
        result = run_forge(forge_name, run)
        run["results"][forge_name] = result
        
        if result.get("skipped"):
            run["completed"].append(forge_name)
            print(f"       ⏭️  Skipped — {result.get('detail', '')}")
            continue
        
        if result.get("ok"):
            run["completed"].append(forge_name)
            print(f"       ✅ {result.get('detail', 'Done')}")
        else:
            run["failed"] = forge_name
            print(f"       ❌ FAILED: {result.get('error', result.get('detail', 'Unknown error'))}")
            print(f"\n  🛑 Pipeline stopped at {forge_name}. {len(run['completed'])}/{len(chain)} forges completed.")
            print(f"     Resume with: python3 forge_runner.py resume --run-id {run['run_id']}")
            break
    
    total_elapsed = round(time.time() - total_start, 1)
    run["status"] = "completed" if not run.get("failed") else "failed"
    run["finished"] = datetime.now().isoformat()
    run["total_elapsed"] = total_elapsed
    save_run(run)
    
    print(f"\n{'='*70}")
    if run.get("failed"):
        print(f"  ❌ Pipeline FAILED at {run['failed']}")
    else:
        print(f"  ✅ Pipeline COMPLETE")
    print(f"  Completed: {len(run['completed'])}/{len(chain)} | Time: {total_elapsed}s")
    print(f"  Run ID: {run['run_id']}")
    print(f"{'='*70}")
    
    return run


def resume_pipeline(run_id: str, dry_run: bool = False):
    """Resume a failed pipeline run from where it stopped."""
    run = load_run(run_id)
    if not run:
        print(f"Run {run_id} not found.")
        return
    
    if run.get("status") == "completed":
        print(f"Run {run_id} is already complete. Use --force to re-run.")
        return
    
    chain = run.get("chain", FULL_CHAIN)
    failed_index = chain.index(run["failed"]) if run.get("failed") in chain else len(run["completed"])
    
    remaining = chain[failed_index:]
    print(f"\n🔄 Resuming {run_id} from {remaining[0] if remaining else 'end'}")
    print(f"   Already completed: {', '.join(run['completed'])}")
    print(f"   Remaining: {' → '.join(remaining)}")
    
    # Only run remaining forges
    run["failed"] = None
    run["current_forge"] = None
    run_pipeline(run.get("params", {}), chain=remaining, dry_run=dry_run)


# ── CLI ─────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description='Forge Runner — Pipeline Orchestrator')
    s = p.add_subparsers(dest='cmd')
    
    # run
    r = s.add_parser('run', help='Run the full pipeline')
    r.add_argument('--spark', help='Spark seed (free-text idea)')
    r.add_argument('--genre', default='fiction', help='Genre')
    r.add_argument('--title', default='Untitled', help='Book title')
    r.add_argument('--chapters', type=int, default=18, help='Chapter count')
    r.add_argument('--chain', choices=['creative', 'production', 'distribution', 'full'], default='creative')
    r.add_argument('--dry-run', action='store_true', help='Preview without executing')
    
    # resume
    res = s.add_parser('resume', help='Resume a failed run')
    res.add_argument('--run-id', required=True, help='Run ID to resume')
    
    # status
    st = s.add_parser('status', help='Show pipeline status')
    st.add_argument('--run-id', help='Specific run ID')
    st.add_argument('--all', action='store_true', help='Show all runs')
    
    a = p.parse_args()
    
    chain_map = {
        "creative": CREATIVE_CHAIN,
        "production": PRODUCTION_CHAIN,
        "distribution": DISTRIBUTION_CHAIN,
        "full": FULL_CHAIN,
    }
    
    if a.cmd == 'run':
        params = {"title": a.title, "genre": a.genre, "chapters": a.chapters}
        if a.spark:
            params["world_seed"] = a.spark
            params["character_seed"] = a.spark
        chain = chain_map.get(a.chain, CREATIVE_CHAIN)
        run_pipeline(params, chain, dry_run=a.dry_run)
    
    elif a.cmd == 'resume':
        resume_pipeline(a.run_id)
    
    elif a.cmd == 'status':
        if a.run_id:
            run = load_run(a.run_id)
            if not run:
                print(f"Run {a.run_id} not found.")
                return
            print(f"\n🎼 Run: {run['run_id']}")
            print(f"   Status: {run.get('status', '?')}")
            print(f"   Chain: {' → '.join(run.get('chain', []))}")
            print(f"   Completed: {', '.join(run.get('completed', []))}")
            if run.get('failed'):
                print(f"   Failed at: {run['failed']}")
            print(f"   Started: {run.get('started', '?')}")
            print(f"   Finished: {run.get('finished', '?')}")
        else:
            runs = list_runs()
            if not runs:
                print("No runs yet. Start one with: python3 forge_runner.py run --spark 'your idea'")
                return
            print(f"\n🎼 Pipeline Runs ({len(runs)} total)")
            print(f"{'─'*70}")
            for run in runs[:10]:
                status = run.get('status', '?')
                icon = '✅' if status == 'completed' else ('❌' if status == 'failed' else '⏳')
                completed = len(run.get('completed', []))
                total = len(run.get('chain', []))
                print(f"  {icon} {run['run_id']} | {completed}/{total} | {status} | {run.get('started', '?')[:16]}")
    
    else:
        p.print_help()


if __name__ == '__main__':
    main()