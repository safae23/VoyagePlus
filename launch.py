"""Launch VoyagePlus and stop every child process on Ctrl+C."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request


def wait_for_services(processes, ports, timeout):
    # Local readiness must not depend on HTTP_PROXY / HTTPS_PROXY settings.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    started = time.monotonic()
    deadline = started + timeout
    next_update = started + 15
    pending = list(ports)
    while pending and time.monotonic() < deadline:
        for process in processes:
            code = process.poll()
            if code is not None:
                raise RuntimeError(f"Un backend a quitté pendant le démarrage (code {code}). Consultez son erreur ci-dessus.")
        for port in pending[:]:
            try:
                with opener.open(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                    if response.status == 200:
                        pending.remove(port)
            except OSError:
                pass
        now = time.monotonic()
        if pending and now >= next_update:
            print(f"Chargement ADK en cours ({int(now - started)} s), ports attendus : {pending}", flush=True)
            next_update = now + 15
        if pending:
            time.sleep(.5)
    if pending:
        raise RuntimeError(f"Services non disponibles après {timeout:g} s : {pending}. Consultez les messages du backend ; augmentez --startup-timeout si le chargement est encore en cours.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--a2a", action="store_true", help="Start four remote A2A services")
    parser.add_argument("--startup-timeout", type=float, default=300,
                        help="Délai maximal de chargement des backends, en secondes (300 par défaut)")
    args = parser.parse_args()
    if not 0 < args.startup_timeout < float("inf"):
        parser.error("--startup-timeout doit être un nombre positif et fini")
    root = Path(__file__).resolve().parent
    local_python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python_executable = str(local_python) if local_python.is_file() else sys.executable
    print(f"Python utilisé : {python_executable}", flush=True)
    env = os.environ.copy()
    from dotenv import load_dotenv
    load_dotenv(root / ".env")
    env.update(os.environ)
    transport = "a2a" if args.a2a else env.get("VOYAGEPLUS_TRANSPORT", "local")
    env["VOYAGEPLUS_TRANSPORT"] = transport
    processes = []
    ports = [8000, 8501] + ([8001, 8002, 8003, 8004] if transport == "a2a" else [])
    import socket
    for port in ports:
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                raise SystemExit(f"Port {port} déjà occupé. Arrêtez le service existant avant le lancement.")
    try:
        modules = [f"agents.{name}_agent" for name in ("flight", "stay", "activities", "weather")] if transport == "a2a" else []
        modules.append("agents.orchestrateur_agent")
        for module in modules:
            processes.append(subprocess.Popen([python_executable, "-u", "-m", module], cwd=root, env=env))
        print("Initialisation des agents ADK…", flush=True)
        wait_for_services(processes, [p for p in ports if p != 8501], args.startup_timeout)
        processes.append(subprocess.Popen([python_executable, "-m", "streamlit", "run", "travel_ui.py"], cwd=root, env=env))
        print(f"VoyagePlus : http://localhost:8501 ; transport {transport}. Ctrl+C pour arrêter.")
        while all(p.poll() is None for p in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
