# -*- coding: utf-8 -*-
"""
setup.py -- Configuracion automatica de Sigma Proyectos
Ejecutar una sola vez por maquina: python scripts/setup.py
"""
import os
import sys
import secrets
import urllib.request
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
ENV_TEMPLATE = ROOT / ".env.template"

ONEDRIVE_CANDIDATES = [
    Path.home() / "OneDrive - Sigma Energia SpA" / "sigma-proyectos",
    Path.home() / "OneDrive" / "sigma-proyectos",
]

HF_API = "https://huggingface.co/api"
HF_REPO = "sebas1989/sigma-proyectos"


# helpers

def banner(text):
    print("\n" + "="*60)
    print("  " + text)
    print("="*60)


def ask(prompt, default=""):
    val = input("  " + prompt + " [" + default + "]: ").strip()
    return val if val else default


def gen_fernet_key():
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


def gen_secret(n=48):
    return secrets.token_urlsafe(n)


def load_env(path):
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def write_env(path, env):
    lines = []
    if ENV_TEMPLATE.exists():
        template_lines = ENV_TEMPLATE.read_text(encoding="utf-8").splitlines()
        written = set()
        for line in template_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=")[0].strip()
                if k in env:
                    lines.append(k + "=" + env[k])
                    written.add(k)
                else:
                    lines.append(line)
            else:
                lines.append(line)
        for k, v in env.items():
            if k not in written:
                lines.append(k + "=" + v)
    else:
        for k, v in env.items():
            lines.append(k + "=" + v)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def hf_set_secret(token, repo, key, value):
    url = HF_API + "/spaces/" + repo + "/variables"
    data = json.dumps({"key": key, "value": value}).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
            return True
    except Exception as e:
        print("    [!] Error subiendo " + key + ": " + str(e))
        return False


def get_hf_token_from_git():
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "huggingface"],
            capture_output=True, text=True, cwd=ROOT
        )
        url = result.stdout.strip()
        if "@" in url and ":" in url.split("@")[0]:
            token = url.split(":")[1].split("@")[0]
            if token.startswith("hf_"):
                return token
    except Exception:
        pass
    return ""


# pasos

def step_generate_secrets(env):
    banner("1/4  Generando secretos de seguridad")

    needs_fernet = not env.get("CUENTAS_SECRET_KEY")
    needs_jwt = not env.get("JWT_SECRET")
    needs_session = not env.get("SESSION_SECRET")
    needs_sync = not env.get("SYNC_API_KEY")

    if needs_fernet:
        try:
            env["CUENTAS_SECRET_KEY"] = gen_fernet_key()
            print("  [ok] CUENTAS_SECRET_KEY generada (Fernet)")
        except ImportError:
            print("  [!] cryptography no instalado. Instala con: pip install cryptography")
            sys.exit(1)
    else:
        print("  [--] CUENTAS_SECRET_KEY ya existe, se mantiene")

    if needs_jwt:
        env["JWT_SECRET"] = gen_secret()
        print("  [ok] JWT_SECRET generada")
    else:
        print("  [--] JWT_SECRET ya existe, se mantiene")

    if needs_session:
        env["SESSION_SECRET"] = gen_secret()
        print("  [ok] SESSION_SECRET generada")
    else:
        print("  [--] SESSION_SECRET ya existe, se mantiene")

    if needs_sync:
        env["SYNC_API_KEY"] = gen_secret(24)
        print("  [ok] SYNC_API_KEY generada")
        print("")
        print("  IMPORTANTE: actualiza config.txt del scraper con esta clave:")
        print("  SYNC_API_KEY = " + env["SYNC_API_KEY"])
        print("")
    else:
        print("  [--] SYNC_API_KEY ya existe, se mantiene")

    return env


def step_onedrive(env):
    banner("2/4  Configurando carpeta OneDrive")

    existing = env.get("ONEDRIVE_DB_DIR", "")
    if existing and Path(existing).exists():
        print("  [--] Carpeta ya configurada: " + existing)
        return env

    found = None
    for candidate in ONEDRIVE_CANDIDATES:
        if candidate.parent.exists():
            found = candidate
            break

    if found:
        print("  [ok] OneDrive detectado: " + str(found.parent))
        db_dir = found
    else:
        print("  OneDrive no encontrado automaticamente.")
        default_path = str(Path.home() / "OneDrive - Sigma Energia SpA" / "sigma-proyectos")
        manual = ask("Ingresa la ruta completa de la carpeta OneDrive de Sigma Energia", default_path)
        db_dir = Path(manual)

    db_dir.mkdir(parents=True, exist_ok=True)
    env["ONEDRIVE_DB_DIR"] = str(db_dir)
    print("  [ok] Carpeta creada/verificada: " + str(db_dir))
    return env


def step_write_env(env):
    banner("3/4  Escribiendo archivo .env")
    write_env(ENV_FILE, env)
    print("  [ok] " + str(ENV_FILE))
    print("  [--] .env esta en .gitignore y NO se subira a GitHub")


def step_hf_secrets(env):
    banner("4/4  Subiendo secretos a HuggingFace Spaces")

    token = get_hf_token_from_git() or env.get("HF_TOKEN", "")
    if not token:
        print("  Token de HuggingFace no encontrado en el remote git.")
        token = ask("Ingresa tu HF token (o presiona Enter para omitir)", "")

    if not token:
        print("  [--] Omitido. Configura los secretos manualmente en:")
        print("       https://huggingface.co/spaces/sebas1989/sigma-proyectos/settings")
        return

    repo = env.get("HF_REPO", HF_REPO)
    secrets_to_push = ["CUENTAS_SECRET_KEY", "JWT_SECRET", "SESSION_SECRET", "SYNC_API_KEY"]

    print("  Subiendo a HF Space: " + repo)
    all_ok = True
    for key in secrets_to_push:
        val = env.get(key, "")
        if val:
            ok = hf_set_secret(token, repo, key, val)
            status = "[ok]" if ok else "[!!]"
            print("  " + status + "  " + key)
            if not ok:
                all_ok = False

    if all_ok:
        print("")
        print("  [ok] Todos los secretos subidos. HuggingFace reiniciara el Space.")
    else:
        print("")
        print("  [!] Algunos secretos fallaron. Verifica el token y el nombre del Space.")


def step_zerotier(env):
    banner("5/5  Red privada ZeroTier")

    zt_id = env.get("ZEROTIER_NETWORK_ID", "")

    # Detectar si ZeroTier esta instalado
    zt_installed = False
    try:
        result = subprocess.run(["zerotier-cli", "info"], capture_output=True, text=True)
        zt_installed = result.returncode == 0
    except FileNotFoundError:
        pass

    if not zt_installed:
        print("  ZeroTier no esta instalado en este equipo.")
        print("")
        print("  PASO 1: Crea la red de Sigma (solo una vez, el admin):")
        print("    a) Ve a https://my.zerotier.com y crea una cuenta gratuita")
        print("    b) Haz clic en 'Create A Network'")
        print("    c) Copia el Network ID (16 caracteres, ej: a09acf0233d1e175)")
        print("    d) En la red: Access Control = Certificate (Private)")
        print("    e) Guarda el Network ID en .env como ZEROTIER_NETWORK_ID=...")
        print("")
        print("  PASO 2: Instala ZeroTier en el PC servidor:")
        print("    https://www.zerotier.com/download/")
        print("")
        print("  PASO 3: Une el PC a la red:")
        print("    zerotier-cli join <NETWORK_ID>")
        print("")
        print("  PASO 4: Aprueba el dispositivo en https://my.zerotier.com")
        print("")
        print("  Para cada nuevo integrante del equipo, comparte el archivo:")
        print("    scripts\\unirse_a_sigma.txt")
    else:
        print("  [ok] ZeroTier esta instalado.")
        # Mostrar redes activas
        result = subprocess.run(["zerotier-cli", "listnetworks"], capture_output=True, text=True)
        lines = [l for l in result.stdout.strip().splitlines() if "OK" in l]
        if lines:
            print("  Redes activas:")
            for l in lines:
                parts = l.split()
                if len(parts) >= 9:
                    net_id = parts[2] if len(parts) > 2 else "?"
                    ip = parts[8].split("/")[0] if len(parts) > 8 else "?"
                    print("    - Red: " + net_id + "  IP: " + ip)
        elif zt_id:
            print("  Uniendo a la red " + zt_id + "...")
            subprocess.run(["zerotier-cli", "join", zt_id])
            print("  [ok] Solicitud enviada. Aprueba el dispositivo en my.zerotier.com")
        else:
            print("  Sin redes configuradas. Agrega ZEROTIER_NETWORK_ID en .env y")
            print("  vuelve a ejecutar setup.py, o corre manualmente:")
            print("    zerotier-cli join <NETWORK_ID>")


# main

def main():
    print("")
    print("="*60)
    print("  Sigma Proyectos -- Setup automatico")
    print("="*60)
    print("  Directorio: " + str(ROOT))

    env = load_env(ENV_FILE)

    env = step_generate_secrets(env)
    env = step_onedrive(env)
    step_write_env(env)
    step_hf_secrets(env)
    step_zerotier(env)

    print("")
    print("="*60)
    print("  Setup completado.")
    print("")
    print("  Siguientes pasos:")
    print("    1. Completa la configuracion de ZeroTier (instrucciones arriba)")
    print("    2. Doble clic en start.bat para iniciar el servidor")
    print("    3. Comparte la URL ZeroTier con tu equipo")
    print("    4. Cada nuevo integrante ejecuta scripts\\unirse_a_sigma.txt")
    print("="*60)
    print("")


if __name__ == "__main__":
    main()
