#!/usr/bin/env python3
"""
Cloud Forge Worker — LavinMQ consumer that executes forge jobs in the cloud.
Deployed on DigitalOcean droplet. Listens on LavinMQ queues, runs forge scripts,
stores results in Supabase.

Architecture:
    LavinMQ (CloudAMQP) → Worker (DO droplet) → Forge scripts → DeepSeek API
                                              → Results → Supabase

Usage:
    python3 cloud_worker.py --forge spark
    python3 cloud_worker.py --forge all
    python3 cloud_worker.py --forge spark --queue forge-spark

Environment (set on droplet):
    LAVINMQ_URL=amqps://user:pass@rabbit.lmq.cloudamqp.com/vhost
    SUPABASE_URL=https://xxx.supabase.co
    SUPABASE_KEY=eyJ...
    OPENROUTER_API_KEY=sk-or-v1-...
    DEEPSEEK_API_KEY=sk-...
"""

import sys, os, json, time, subprocess, signal, traceback
from datetime import datetime
from pathlib import Path

# ── Configuration ───────────────────────────────────────────────

BATCAVE = os.path.expanduser("~/batcave")

FORGE_SCRIPTS = {
    "spark":    os.path.join(BATCAVE, "spark-forge", "scripts", "spark.py"),
    "genre":    os.path.join(BATCAVE, "genre-forge", "scripts", "genre.py"),
    "world":    os.path.join(BATCAVE, "world-forge", "scripts", "world.py"),
    "character": os.path.join(BATCAVE, "character-forge", "scripts", "character.py"),
    "outline":  os.path.join(BATCAVE, "outline-forge", "scripts", "outline.py"),
    "voice":    os.path.join(BATCAVE, "voice-forge", "scripts", "voice.py"),
    "cover":    os.path.join(BATCAVE, "cover-forge", "scripts", "cover.py"),
    "audio":    os.path.join(BATCAVE, "audio-forge", "scripts", "audio.py"),
}

LAVINMQ_URL = os.environ.get("LAVINMQ_URL", "amqps://localhost")
LAVINMQ_VHOST = os.environ.get("LAVINMQ_VHOST", "/")
QUEUE_PREFIX = "forge"

# ── LavinMQ Connection ─────────────────────────────────────────

def get_lavinmq_connection():
    """Connect to LavinMQ (CloudAMQP). Uses pika library."""
    import pika
    params = pika.URLParameters(LAVINMQ_URL)
    return pika.BlockingConnection(params)


def declare_queues(channel, forge_names: list):
    """Declare queues for each forge. One queue per forge for independent scaling."""
    queues = {}
    for name in forge_names:
        qname = f"{QUEUE_PREFIX}-{name}"
        channel.queue_declare(queue=qname, durable=True)
        queues[name] = qname
    return queues


# ── Job Execution ───────────────────────────────────────────────

def execute_forge_job(forge_name: str, job_data: dict) -> dict:
    """Execute a forge script with the given job data. Returns result."""
    script = FORGE_SCRIPTS.get(forge_name)
    if not script:
        return {"ok": False, "error": f"Unknown forge: {forge_name}"}
    
    if not os.path.exists(script):
        return {"ok": False, "error": f"Script not found: {script}"}
    
    start = time.time()
    params = job_data.get("params", {})
    cmd = [sys.executable, script]
    
    try:
        # Build command based on forge type
        if forge_name == "spark":
            cmd += ["generate", "--count", str(params.get("count", 10))]
            if params.get("genre"): cmd += ["--genre", params["genre"]]
        elif forge_name == "genre":
            cmd += ["research", "--genre", params.get("genre", "fiction")]
        elif forge_name == "world":
            cmd += ["build", "--seed", params.get("seed", "")]
            if params.get("genre"): cmd += ["--genre", params["genre"]]
        elif forge_name == "character":
            cmd += ["build", "--seed", params.get("seed", "")]
            if params.get("genre"): cmd += ["--genre", params["genre"]]
        elif forge_name == "outline":
            cmd += ["build", "--title", params.get("title", "Untitled"),
                    "--genre", params.get("genre", "fiction"),
                    "--chapters", str(params.get("chapters", 18))]
        elif forge_name == "voice":
            cmd += ["extract", "--sample", params.get("sample", "")]
        elif forge_name == "cover":
            cmd += ["design", "--title", params.get("title", "Untitled"),
                    "--genre", params.get("genre", "fiction")]
        elif forge_name == "audio":
            cmd += ["produce", "--project", params.get("project", "")]
        
        # Run the forge
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(script),
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        elapsed = round(time.time() - start, 1)
        ok = result.returncode == 0
        
        response = {
            "ok": ok,
            "forge": forge_name,
            "elapsed": elapsed,
            "params": params,
            "stdout": result.stdout[-1000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if not ok and result.stderr else "",
            "error": result.stderr[-200:] if not ok else None,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Try to parse output JSON for structured results
        if ok and result.stdout:
            try:
                for line in result.stdout.split('\n'):
                    if 'world_id' in line or 'character_id' in line or 'outline_id' in line:
                        pass  # Structured output detected
            except:
                pass
        
        return response
    
    except subprocess.TimeoutExpired:
        return {"ok": False, "forge": forge_name, "error": "Timeout (300s)", "elapsed": 300}
    except Exception as e:
        return {"ok": False, "forge": forge_name, "error": str(e), "elapsed": round(time.time() - start, 1)}


# ── Supabase Integration ────────────────────────────────────────

def store_result_supabase(job_data: dict, result: dict):
    """Store forge job result in Supabase."""
    try:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            print("   ⚠️  Supabase not configured — skipping DB write")
            return
        
        client = create_client(url, key)
        client.table("forge_runs").insert({
            "run_id": job_data.get("run_id", ""),
            "project_id": job_data.get("project_id", ""),
            "user_id": job_data.get("user_id", ""),
            "forge_name": result.get("forge", ""),
            "status": "completed" if result.get("ok") else "failed",
            "result": json.dumps(result),
            "cost": job_data.get("cost", 0),
            "started_at": job_data.get("started_at"),
            "finished_at": datetime.now().isoformat(),
        }).execute()
        print("   ✅ Result stored in Supabase")
    except Exception as e:
        print(f"   ⚠️  Supabase write failed: {e}")


# ── Worker Process ──────────────────────────────────────────────

class ForgeWorker:
    """Worker that listens on LavinMQ and executes forge jobs."""
    
    def __init__(self, forge_names: list):
        self.forge_names = forge_names
        self.running = True
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def shutdown(self, signum, frame):
        print(f"\n🛑 Shutting down worker...")
        self.running = False
    
    def start(self):
        """Connect to LavinMQ and start consuming jobs."""
        print(f"🔌 Connecting to LavinMQ...")
        
        try:
            conn = get_lavinmq_connection()
            channel = conn.channel()
            queues = declare_queues(channel, self.forge_names)
            
            print(f"✅ Connected. Listening on queues:")
            for name, qname in queues.items():
                print(f"   📨 {qname} → {name}")
            
            # Set up consumers for each queue
            for forge_name in self.forge_names:
                qname = queues[forge_name]
                
                def make_callback(fn):
                    def callback(ch, method, properties, body):
                        self.process_job(fn, ch, method, properties, body, conn)
                    return callback
                
                channel.basic_consume(
                    queue=qname,
                    on_message_callback=make_callback(forge_name),
                    auto_ack=False,
                )
            
            print(f"\n⚡ Worker ready. Waiting for jobs...\n")
            
            while self.running:
                try:
                    conn.process_data_events(time_limit=1)
                except Exception as e:
                    if self.running:
                        print(f"⚠️  Connection error: {e}. Reconnecting...")
                        time.sleep(5)
                        try:
                            conn = get_lavinmq_connection()
                            channel = conn.channel()
                            queues = declare_queues(channel, self.forge_names)
                            for forge_name in self.forge_names:
                                qname = queues[forge_name]
                                channel.basic_consume(
                                    queue=qname,
                                    on_message_callback=make_callback(forge_name),
                                    auto_ack=False,
                                )
                        except Exception as reconnect_err:
                            print(f"❌ Reconnect failed: {reconnect_err}")
            
            conn.close()
            print("Worker stopped.")
        
        except Exception as e:
            print(f"❌ Failed to start worker: {e}")
            traceback.print_exc()
    
    def process_job(self, forge_name, channel, method, properties, body, conn):
        """Process a single forge job from the queue."""
        try:
            job_data = json.loads(body)
            run_id = job_data.get("run_id", "unknown")
            project_id = job_data.get("project_id", "unknown")
            
            print(f"\n{'─'*60}")
            print(f"📥 Job received: {forge_name} | Run: {run_id} | Project: {project_id}")
            print(f"   Params: {json.dumps(job_data.get('params', {}))[:100]}")
            
            # Execute the forge
            job_data["started_at"] = datetime.now().isoformat()
            result = execute_forge_job(forge_name, job_data)
            
            # Store result
            store_result_supabase(job_data, result)
            
            # Ack the message
            if result.get("ok"):
                channel.basic_ack(delivery_tag=method.delivery_tag)
                status = "✅ DONE"
            else:
                # Don't requeue on permanent failure
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                status = "❌ FAILED"
            
            elapsed = result.get("elapsed", 0)
            print(f"   {status} in {elapsed}s")
            
        except Exception as e:
            print(f"   ❌ Job processing error: {e}")
            traceback.print_exc()
            try:
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except:
                pass


# ── Job Publisher (API side) ────────────────────────────────────

def publish_job(forge_name: str, job_data: dict):
    """Publish a job to LavinMQ. Called from the API server."""
    conn = get_lavinmq_connection()
    channel = conn.channel()
    qname = f"{QUEUE_PREFIX}-{forge_name}"
    channel.queue_declare(queue=qname, durable=True)
    
    channel.basic_publish(
        exchange="",
        routing_key=qname,
        body=json.dumps(job_data),
        properties=None,
    )
    
    conn.close()
    return {"ok": True, "queue": qname, "forge": forge_name}


# ── CLI ─────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description='Cloud Forge Worker')
    s = p.add_subparsers(dest='cmd')
    
    # Start worker
    w = s.add_parser('start', help='Start worker process')
    w.add_argument('--forge', required=True, help='Forge name or "all"')
    
    # Publish a job (for testing)
    pub = s.add_parser('publish', help='Publish a test job')
    pub.add_argument('--forge', required=True)
    pub.add_argument('--run-id', default='test-001')
    pub.add_argument('--params', default='{}', help='JSON params')
    
    a = p.parse_args()
    
    if a.cmd == 'start':
        if a.forge == 'all':
            forge_names = list(FORGE_SCRIPTS.keys())
        else:
            forge_names = [a.forge]
        
        worker = ForgeWorker(forge_names)
        worker.start()
    
    elif a.cmd == 'publish':
        job = {
            "run_id": a.run_id,
            "project_id": "test",
            "user_id": "test-user",
            "forge": a.forge,
            "params": json.loads(a.params) if a.params else {},
            "created_at": datetime.now().isoformat(),
        }
        result = publish_job(a.forge, job)
        print(f"📤 Published: {json.dumps(result, indent=2)}")
    
    else:
        p.print_help()


if __name__ == '__main__':
    main()