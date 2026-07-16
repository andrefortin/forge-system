# Forge System — Deployment Architecture

## What Gets Deployed Where

```
YOUR MACHINE (Andre's Pop!_OS)          THE CLOUD
─────────────────────────────          ─────────────────────────
                                                                    
Pi Agent (dev tool)                    DigitalOcean Droplet ($12/mo)
  │  builds, tests, deploys              │
  │  ┌─────────────┐                     ├── API Server (FastAPI)
  │  │ forge_runner │──deploys──→        │     Accepts user requests
  │  │ (CLI test)   │                    │     Creates LavinMQ jobs
  │  └─────────────┘                     │
  │                                      ├── Worker Processes (systemd)
  │  ┌─────────────┐                     │     cloud_worker.py --forge all
  │  │ 12 forges    │──rsync──→          │     Listens on LavinMQ
  │  │ (scripts)    │                    │     Executes forge jobs
  │  └─────────────┘                     │     Calls DeepSeek via OpenRouter
  │                                      │
  │  ┌─────────────┐                     ├── NGINX (reverse proxy)
  │  │ llm_client   │──rsync──→          │     SSL termination
  │  │ (shared)     │                    │     Rate limiting
  │  └─────────────┘                     │
                                         │
                                    LavinMQ (CloudAMQP) — already running
                                      │
                                      ├── forge-spark queue
                                      ├── forge-genre queue
                                      ├── forge-world queue
                                      ├── ... (one per forge)
                                      
                                    Supabase — already running
                                      │
                                      ├── forge_runs table
                                      ├── forge_outputs table
                                      ├── projects table
                                      ├── users table (Auth)
                                      
                                    Vercel — for frontend (future)
                                      │
                                      ├── Next.js dashboard
                                      ├── HeroUI components
```

## Pi's Role: Development Plane (Stays Local)

Pi does NOT get deployed. Pi is the tool that:
1. Writes and tests forge scripts locally
2. Runs `forge_runner.py --dry-run` to validate the chain
3. Runs `forge_runner.py run --chain creative` for live testing
4. Deploys code to the droplet via rsync/git
5. SSHs into the droplet to restart workers
6. Monitors logs and Supabase for results

Pi's model-fallback extension, settings.json, and agent configuration are irrelevant to the cloud deployment. The cloud uses its own environment variables.

## Droplet Setup

```bash
# On the DO droplet (Ubuntu 24.04, $12/mo basic)
apt update && apt install python3-pip python3-venv nginx certbot

# Clone forges
cd ~ && mkdir -p batcave && cd batcave
git clone https://github.com/andrefortin/forge-system.git
git clone https://github.com/andrefortin/spark-forge.git
git clone https://github.com/andrefortin/genre-forge.git
# ... clone all 12 forges

# Install dependencies
pip install pika supabase python-dotenv youtube-transcript-api

# Set environment (NOT in .bashrc — use systemd EnvironmentFile)
cat > /etc/forge/env << 'EOF'
LAVINMQ_URL=amqps://user:pass@rabbit.lmq.cloudamqp.com/hkmovykq
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
OPENROUTER_API_KEY=sk-or-v1-...
DEEPSEEK_API_KEY=sk-...
EOF
chmod 600 /etc/forge/env
```

## Worker Setup (systemd)

```ini
# /etc/systemd/system/forge-worker@.service
[Unit]
Description=Forge Worker: %i
After=network.target

[Service]
Type=simple
User=forge
WorkingDirectory=/home/forge/batcave/forge-system
EnvironmentFile=/etc/forge/env
ExecStart=/usr/bin/python3 cloud_worker.py start --forge %i
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Start one worker per forge (or one worker for all):
systemctl enable forge-worker@all
systemctl start forge-worker@all

# Or scale specific forges independently:
systemctl enable forge-worker@spark
systemctl enable forge-worker@story  # needs more CPU
```

## API Server (FastAPI)

```python
# api_server.py — runs on the droplet, port 8000

from fastapi import FastAPI, HTTPException
from cloud_worker import publish_job
import uuid, json
from datetime import datetime

app = FastAPI(title="Forge API")

@app.post("/api/forge/{forge_name}")
async def run_forge(forge_name: str, body: dict):
    """Submit a job to a forge."""
    valid = ["spark","genre","world","character","outline","voice","cover","audio"]
    if forge_name not in valid:
        raise HTTPException(400, f"Unknown forge. Use: {', '.join(valid)}")
    
    run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    job = {
        "run_id": run_id,
        "project_id": body.get("project_id", "default"),
        "user_id": body.get("user_id", "anonymous"),
        "forge": forge_name,
        "params": body.get("params", {}),
        "created_at": datetime.now().isoformat(),
    }
    
    result = publish_job(forge_name, job)
    return {"run_id": run_id, "status": "queued", **result}


@app.post("/api/pipeline/creative")
async def run_creative_pipeline(body: dict):
    """Run the full creative chain: spark → genre → world → character → outline."""
    run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    jobs = []
    
    chain = ["spark", "genre", "world", "character", "outline"]
    for forge_name in chain:
        job = {
            "run_id": run_id,
            "project_id": body.get("project_id", "default"),
            "user_id": body.get("user_id", "anonymous"),
            "forge": forge_name,
            "params": body.get("params", {}),
            "chain_position": chain.index(forge_name),
            "created_at": datetime.now().isoformat(),
        }
        publish_job(forge_name, job)
        jobs.append(forge_name)
    
    return {"run_id": run_id, "status": "queued", "chain": chain, "jobs": len(jobs)}


@app.get("/api/run/{run_id}")
async def get_run_status(run_id: str):
    """Check status of a pipeline run."""
    # Query Supabase for forge_runs with this run_id
    # ...
    return {"run_id": run_id, "status": "in_progress"}
```

## NGINX Config

```nginx
server {
    listen 80;
    server_name api.fortin.press;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Cost Estimate

| Resource | Monthly Cost |
|----------|------------|
| DO Droplet ($12/mo basic) | $12 |
| LavinMQ (CloudAMQP, free tier) | $0 |
| Supabase (free tier) | $0 |
| Vercel (frontend, free tier) | $0 |
| DeepSeek API (~10 books/mo) | ~$20-30 |
| **Total monthly** | **~$32-42** |
