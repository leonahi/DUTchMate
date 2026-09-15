"""Run a 15 s Pico 1 synthetic UART profile with an optional host pause."""

import argparse
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("SUSTAIN", "BURST"))
    parser.add_argument("--stall-ms", type=float, default=0.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.stall_ms < 0 or args.stall_ms > 1000:
        parser.error("--stall-ms must be between 0 and 1000")

    repo_root = Path(__file__).resolve().parents[4]
    cli = repo_root / ".venv/bin/dutchmate"
    pid_file = repo_root / ".dutchmate/dutchmate-service.pid"
    service_pid = int(pid_file.read_text(encoding="utf-8").strip())
    environment = dict(os.environ)
    environment["PATH"] = f"{repo_root / '.venv/bin'}:{environment.get('PATH', '')}"
    process = subprocess.Popen(
        [str(cli), "capture", "--seconds", "15"],
        cwd=repo_root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    paused = False
    pause_ms = 0.0
    send_result: subprocess.CompletedProcess[str] | None = None
    try:
        time.sleep(0.5)
        send_result = subprocess.run(
            [str(cli), "send", args.command, "--force"],
            cwd=repo_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if send_result.returncode == 0 and args.stall_ms > 0:
            time.sleep(1.5)
            os.kill(service_pid, signal.SIGSTOP)
            paused = True
            started_ns = time.monotonic_ns()
            time.sleep(args.stall_ms / 1000)
            os.kill(service_pid, signal.SIGCONT)
            paused = False
            pause_ms = (time.monotonic_ns() - started_ns) / 1_000_000
        capture_output, _ = process.communicate(timeout=40)
    finally:
        if paused:
            os.kill(service_pid, signal.SIGCONT)
        if process.poll() is None:
            process.kill()
            process.communicate()

    result = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixture_command": args.command,
        "requested_pause_ms": args.stall_ms,
        "measured_pause_ms": pause_ms,
        "service_pid": service_pid,
        "host_load_after": os.getloadavg(),
        "send_exit_code": send_result.returncode if send_result else None,
        "send_output": send_result.stdout if send_result else None,
        "send_error": send_result.stderr if send_result else None,
        "capture_exit_code": process.returncode,
        "capture_output": capture_output,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if send_result is None or send_result.returncode != 0 or process.returncode != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
