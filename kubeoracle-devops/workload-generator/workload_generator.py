#!/usr/bin/env python3
"""
KubeOracle Demo Workload Generator
====================================
Generates realistic synthetic load on the demo cluster:
  - CPU spikes on specific pods
  - Memory pressure / OOMKill simulation
  - Pod crash/restart cycles
  - Transient network errors
  - Cascading failure scenarios

Usage:
  python workload_generator.py [--scenario SCENARIO] [--duration SECONDS]

Scenarios: cpu_spike, memory_leak, crash_loop, cascading, quiet, random
"""

import argparse
import asyncio
import logging
import math
import os
import random
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("workload-gen")

NAMESPACE = os.getenv("KUBEORACLE_NAMESPACE", "kubeoracle")
KUBECTL = os.getenv("KUBECTL_PATH", "kubectl")

# ──── Scenario Definitions ────────────────────────────────────────────────────

@dataclass
class Scenario:
    name: str
    description: str
    fn: Callable

def run_kubectl(*args) -> tuple[int, str, str]:
    """Execute a kubectl command, return (returncode, stdout, stderr)."""
    cmd = [KUBECTL, *args]
    log.debug(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def get_running_pods(label_selector: str = "") -> list[str]:
    """Return list of running pod names in the kubeoracle namespace."""
    args = ["get", "pods", "-n", NAMESPACE,
            "--field-selector=status.phase=Running",
            "-o", "jsonpath={.items[*].metadata.name}"]
    if label_selector:
        args += ["-l", label_selector]
    rc, out, _ = run_kubectl(*args)
    if rc != 0 or not out:
        return []
    return out.split()

def exec_in_pod(pod: str, command: str) -> tuple[int, str]:
    """Run a shell command inside a pod."""
    rc, out, err = run_kubectl(
        "exec", pod, "-n", NAMESPACE, "--", "sh", "-c", command
    )
    return rc, out or err

# ──── CPU Spike ───────────────────────────────────────────────────────────────

async def scenario_cpu_spike(duration: int = 60):
    """Spike CPU on a random pod using a stress loop."""
    log.info("🔥 SCENARIO: CPU Spike")
    pods = get_running_pods("tier=backend")
    if not pods:
        log.warning("No backend pods found, skipping CPU spike")
        return
    target = random.choice(pods)
    log.info(f"  Targeting pod: {target} for {duration}s")
    # Use a Python busy-loop inside the pod
    stress_cmd = (
        f"python3 -c \""
        f"import time; end=time.time()+{duration}; "
        f"[x**2 for _ in iter(int, 1) if time.time()<end]\""
        f" &"
    )
    rc, out = exec_in_pod(target, stress_cmd)
    log.info(f"  CPU stress started: rc={rc} {out[:60]}")
    await asyncio.sleep(duration)
    log.info(f"  CPU spike complete on {target}")

# ──── Memory Leak ─────────────────────────────────────────────────────────────

async def scenario_memory_leak(duration: int = 90):
    """Gradually consume memory in a pod to trigger OOMKill."""
    log.info("💾 SCENARIO: Memory Leak / OOMKill")
    pods = get_running_pods("app=auth-service")
    if not pods:
        pods = get_running_pods()
    if not pods:
        log.warning("No pods found")
        return
    target = random.choice(pods)
    log.info(f"  Targeting pod: {target}")
    # Allocate ~10MB chunks every 2s
    mem_cmd = (
        "python3 -c \""
        "import time; blocks=[]; "
        "[blocks.append(' ' * 10_000_000) or time.sleep(2) for _ in range(50)]\""
        " &"
    )
    rc, out = exec_in_pod(target, mem_cmd)
    log.info(f"  Memory leak started: rc={rc}")
    await asyncio.sleep(duration)

# ──── Crash Loop ──────────────────────────────────────────────────────────────

async def scenario_crash_loop(cycles: int = 4, interval: int = 20):
    """Kill a pod repeatedly to generate CrashLoopBackOff events."""
    log.info(f"💥 SCENARIO: Crash Loop ({cycles} cycles)")
    for i in range(cycles):
        pods = get_running_pods("tier=backend")
        if not pods:
            log.warning("No backend pods available")
            await asyncio.sleep(interval)
            continue
        target = random.choice(pods)
        log.info(f"  Cycle {i+1}/{cycles}: deleting pod {target}")
        rc, out, err = run_kubectl("delete", "pod", target, "-n", NAMESPACE, "--grace-period=0")
        log.info(f"  Deleted: rc={rc} {(out or err)[:80]}")
        await asyncio.sleep(interval)
    log.info("  Crash loop scenario complete")

# ──── Transient Errors ────────────────────────────────────────────────────────

async def scenario_transient_errors(duration: int = 120):
    """
    Scale a deployment down then back up to simulate transient unavailability.
    Mimics a service going offline briefly.
    """
    log.info("⚡ SCENARIO: Transient Errors (scale down/up)")
    deployments = ["notification-service", "analytics-service", "inventory-service"]
    target = random.choice(deployments)
    log.info(f"  Scaling {target} to 0")
    run_kubectl("scale", "deployment", target, "-n", NAMESPACE, "--replicas=0")
    await asyncio.sleep(random.randint(15, 30))
    log.info(f"  Scaling {target} back up")
    run_kubectl("scale", "deployment", target, "-n", NAMESPACE, "--replicas=2")
    log.info(f"  Transient error scenario complete for {target}")

# ──── Cascading Failure ───────────────────────────────────────────────────────

async def scenario_cascading_failure(duration: int = 180):
    """
    Simulate a cascading failure:
    1. Kill auth-service → payment-service becomes degraded
    2. Spike CPU on user-service
    3. Auto-recovery after ~60s
    """
    log.info("🌊 SCENARIO: Cascading Failure")

    log.info("  Step 1: Crashing auth-service")
    pods = get_running_pods("app=auth-service")
    if pods:
        run_kubectl("delete", "pod", pods[0], "-n", NAMESPACE, "--grace-period=0")
    await asyncio.sleep(15)

    log.info("  Step 2: CPU spike on user-service")
    pods = get_running_pods("app=user-service")
    if pods:
        exec_in_pod(pods[0], "python3 -c \"x=0\nwhile True: x+=1\" &")
    await asyncio.sleep(30)

    log.info("  Step 3: Scaling down notification-service")
    run_kubectl("scale", "deployment", "notification-service", "-n", NAMESPACE, "--replicas=0")
    await asyncio.sleep(30)

    log.info("  Step 4: Recovery — restoring services")
    run_kubectl("scale", "deployment", "notification-service", "-n", NAMESPACE, "--replicas=2")
    log.info("  Cascading failure scenario complete")

# ──── Quiet Period ────────────────────────────────────────────────────────────

async def scenario_quiet(duration: int = 60):
    """Let everything settle — useful between scenarios."""
    log.info(f"😴 SCENARIO: Quiet period ({duration}s)")
    await asyncio.sleep(duration)

# ──── Random Loop ─────────────────────────────────────────────────────────────

async def scenario_random(duration: int = 600):
    """Randomly cycle through scenarios for demo realism."""
    log.info(f"🎲 SCENARIO: Random cycling for {duration}s")
    scenarios_pool = [
        (scenario_cpu_spike,       {"duration": 40}),
        (scenario_crash_loop,      {"cycles": 3, "interval": 15}),
        (scenario_transient_errors, {"duration": 60}),
        (scenario_memory_leak,     {"duration": 60}),
        (scenario_quiet,           {"duration": 30}),
    ]
    start = time.time()
    while time.time() - start < duration:
        fn, kwargs = random.choice(scenarios_pool)
        await fn(**kwargs)
        await asyncio.sleep(random.randint(10, 20))
    log.info("  Random cycling complete")

# ──── Registry ────────────────────────────────────────────────────────────────

SCENARIOS: dict[str, Scenario] = {
    "cpu_spike":   Scenario("cpu_spike",   "Spike CPU on a random backend pod", lambda: scenario_cpu_spike()),
    "memory_leak": Scenario("memory_leak", "Gradually leak memory (triggers OOMKill)", lambda: scenario_memory_leak()),
    "crash_loop":  Scenario("crash_loop",  "Delete pods repeatedly (CrashLoopBackOff)", lambda: scenario_crash_loop()),
    "cascading":   Scenario("cascading",   "Multi-service cascading failure + recovery", lambda: scenario_cascading_failure()),
    "transient":   Scenario("transient",   "Brief service downtime via scale-to-zero", lambda: scenario_transient_errors()),
    "quiet":       Scenario("quiet",       "Quiet period, let things settle", lambda: scenario_quiet()),
    "random":      Scenario("random",      "Random scenario cycling (default for demo)", lambda: scenario_random()),
}

# ──── Entry Point ─────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="KubeOracle Demo Workload Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Available scenarios:\n" + "\n".join(
            f"  {k:12} – {v.description}" for k, v in SCENARIOS.items()
        )
    )
    parser.add_argument("--scenario", default="random",
                        choices=list(SCENARIOS.keys()),
                        help="Scenario to run (default: random)")
    parser.add_argument("--duration", type=int, default=600,
                        help="Max duration in seconds (default: 600)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without executing")
    return parser.parse_args()

async def main():
    args = parse_args()
    if args.dry_run:
        log.info(f"[DRY RUN] Would run scenario: {args.scenario} for {args.duration}s")
        for name, s in SCENARIOS.items():
            log.info(f"  {name:12} – {s.description}")
        return
    log.info(f"Starting workload generator: scenario={args.scenario} duration={args.duration}s")
    scenario = SCENARIOS[args.scenario]
    await scenario.fn()
    log.info("Workload generator finished.")

if __name__ == "__main__":
    asyncio.run(main())
