#!/usr/bin/env python3

import os
import re
import sys
import time
import shutil
import signal
import zipfile
import subprocess
import getpass
from html import unescape
from pathlib import Path

try:
    from curl_cffi import requests as cffi_requests
    from bs4 import BeautifulSoup
except ImportError:
    print("\033[0;31m[erro]\033[0m  Instala: pip install -r requirements.txt")
    sys.exit(1)


MEDIAFIRE_URL = "https://www.mediafire.com/file/ghcw8q7txwod4yk/LinaPythonSims3.zip"
USERNAME      = getpass.getuser()
HOME          = Path.home()
WINEPREFIX    = HOME / ".wine_sims3_LinaPython"
LAUNCHER_PATH = HOME / ".local" / "bin" / "sims3"
DOWNLOAD_DIR  = HOME / "Downloads" / "sims3_tmp"
ICON_DEST     = HOME / ".local" / "share" / "icons" / "TheSims3.ico"
DESKTOP_DEST  = HOME / ".local" / "share" / "applications" / "sims3.desktop"
PRODUCT_KEY   = "FL2J-TFWL-5V6E-V5VZ-VRLD"
SIMS3_DOCS    = HOME / "Documents" / "Electronic Arts" / "The Sims 3"
OPTIONS_PATH  = SIMS3_DOCS / "Options.ini"

OPTIONS_PATCH = {
    "texturequality":  "3",
    "visualeffects":   "3",
    "simquality":      "3",
    "lightingquality": "2",
    "treequality":     "2",
    "reflections":     "1",
    "edgesmoothing":   "0",
    "drawdistance":    "3",
    "audioquality":    "2",
    "enableaging":     "1",
    "fullscreen":      "1",
    "resolution":      "1920 1080 0",
}

R  = "\033[0;31m";  G  = "\033[0;32m";  Y  = "\033[1;33m"
C  = "\033[0;36m";  B  = "\033[1;34m";  NC = "\033[0m"
DIM = "\033[2m";    BLD = "\033[1m";     BG = "\033[1;32m"
BR = "\033[1;31m";  W  = "\033[1;37m";  M  = "\033[0;35m"


def _hr(char="─", width=60, color=DIM):
    print(f"{color}{char * width}{NC}")

def _box_top(width=60):
    print(f"{DIM}╭{'─' * (width - 2)}╮{NC}")

def _box_bot(width=60):
    print(f"{DIM}╰{'─' * (width - 2)}╯{NC}")

def _box_row(text="", width=60, pad=2):
    inner = width - 2
    line = f"{' ' * pad}{text}"
    visible = len(re.sub(r'\033\[[0-9;]*m', '', line))
    padding = inner - visible
    if padding < 0:
        padding = 0
    print(f"{DIM}│{NC}{line}{' ' * padding}{DIM}│{NC}")

def log(msg):
    print(f"  {G}✓{NC}  {msg}")

def warn(msg):
    print(f"  {Y}!{NC}  {msg}")

def die(msg):
    print(f"\n  {R}✗{NC}  {msg}\n", file=sys.stderr)
    sys.exit(1)

def step(msg):
    print(f"\n  {B}→{NC}  {BLD}{msg}{NC}")


def check_deps():
    missing = [cmd for cmd in ("wine", "winetricks") if not shutil.which(cmd)]
    if missing:
        die(f"Dependências ausentes: {', '.join(missing)}\nInstala antes de continuar.")


def wine_env() -> dict:
    env = {**os.environ, "WINEPREFIX": str(WINEPREFIX)}
    if os.environ.get("DISPLAY"):
        pass
    elif os.environ.get("WAYLAND_DISPLAY"):
        env["DISPLAY"] = ":0"
        env["WAYLAND_DISPLAY"] = ""
        warn("Wayland detectado. Wine requer Xwayland.")
    else:
        env["DISPLAY"] = ":0"
        env["WAYLAND_DISPLAY"] = ""
    return env


_CDN_RE = re.compile(r'https://download\d+\.mediafire\.com/[^\s"\'<>]+')

def mediafire_direct_link(url_pagina: str) -> str:
    if not url_pagina.endswith("/file"):
        url_pagina = url_pagina.rstrip("/") + "/file"
    sessao = cffi_requests.Session(impersonate="chrome120")
    for tentativa, espera in enumerate([0, 3, 6], start=1):
        if espera:
            log(f"Cloudflare — aguardando {espera}s (tentativa {tentativa}/3)...")
            time.sleep(espera)
        resp = sessao.get(url_pagina, timeout=20, allow_redirects=True)
        if resp.status_code == 403:
            continue
        if resp.status_code != 200:
            raise ConnectionError(f"Mediafire retornou HTTP {resp.status_code}")
        m = _CDN_RE.search(unescape(resp.text))
        if m:
            return m.group(0).rstrip("\"'\\&")
        raise ValueError("Página carregou mas link CDN não encontrado.")
    raise ConnectionError("Cloudflare bloqueou após 3 tentativas.")


def download_file(url: str, dest: Path) -> Path:
    filename = url.split("/")[-1].split("?")[0] or "LinaPySims3.zip"
    output   = dest / filename
    dest.mkdir(parents=True, exist_ok=True)
    step("Baixando The Sims 3...")
    sessao   = cffi_requests.Session(impersonate="chrome120")
    response = sessao.get(url, stream=True, timeout=60)
    if response.status_code != 200:
        raise ConnectionError(f"Download falhou: HTTP {response.status_code}")
    total      = int(response.headers.get("content-length", 0))
    downloaded = 0
    with open(output, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 512):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    filled = int(pct / 2)
                    bar = f"{G}{'█' * filled}{DIM}{'░' * (50 - filled)}{NC}"
                    mb_done = downloaded // 1024 // 1024
                    mb_total = total // 1024 // 1024
                    print(f"\r  {bar}  {W}{pct:5.1f}%{NC}  {DIM}{mb_done}/{mb_total} MB{NC}", end="", flush=True)
    print()
    log(f"Concluído → {output.name}")
    return output


def fluxo_download() -> Path:
    zip_esperado = DOWNLOAD_DIR / "LinaPySims3.zip"
    while True:
        print()
        _box_top()
        _box_row(f"{W}Download{NC}")
        _box_row()
        _box_row(f"{G}1{NC}  Baixar via Mediafire")
        if zip_esperado.exists():
            mb = zip_esperado.stat().st_size // 1024 // 1024
            _box_row(f"{G}2{NC}  Usar arquivo existente  {DIM}({mb} MB){NC}")
        _box_bot()
        print()
        escolha = input(f"  {DIM}›{NC} ").strip()
        if escolha == "2" and zip_esperado.exists():
            log(f"Usando arquivo existente")
            return zip_esperado
        if escolha in ("1", "2"):
            while True:
                try:
                    direct_url = mediafire_direct_link(MEDIAFIRE_URL)
                    return download_file(direct_url, DOWNLOAD_DIR)
                except (ConnectionError, ValueError) as e:
                    print()
                    warn(str(e))
                    print()
                    _box_top()
                    _box_row(f"{R}Download falhou.{NC}")
                    _box_row()
                    _box_row(f"{G}1{NC}  Tentar novamente")
                    _box_row(f"{G}2{NC}  Cancelar")
                    _box_bot()
                    print()
                    if input(f"  {DIM}›{NC} ").strip() != "1":
                        die("Download cancelado.")
        else:
            warn("Opção inválida.")


def extract_zip(zip_path: Path, dest: Path) -> Path:
    step(f"Extraindo {zip_path.name}...")
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)
    contents = list(dest.iterdir())
    root = contents[0] if len(contents) == 1 and contents[0].is_dir() else dest
    has_installer = list(root.rglob("Sims3Setup.exe")) or list(root.rglob("setup.exe"))
    if not has_installer:
        die(f"Zip extraído mas instalador não encontrado em {root}.")
    log("Extração concluída")
    return root


def find_installer(root: Path) -> Path:
    for pattern in ("Sims3Setup.exe", "setup.exe", "Setup.exe"):
        matches = list(root.rglob(pattern))
        if matches:
            return matches[0]
    die(f"Instalador não encontrado em {root}")


def find_crack(root: Path) -> Path:
    matches = list(root.rglob("Crack/TS3.exe"))
    if not matches:
        matches = [p for p in root.rglob("TS3.exe") if "crack" in str(p).lower()]
    if not matches:
        die(f"Crack/TS3.exe não encontrado em {root}")
    return matches[0]


def setup_wine_prefix():
    env = wine_env()
    if WINEPREFIX.exists():
        drive_c = WINEPREFIX / "drive_c" / "windows"
        if not drive_c.exists():
            warn("Prefixo existente parece corrompido (drive_c/windows ausente).")
            resp = input(f"  {DIM}Recriar? (s/N){NC} › ").strip().lower()
            if resp == "s":
                shutil.rmtree(WINEPREFIX)
            else:
                warn("Continuando com prefixo potencialmente quebrado.")
                return
        else:
            warn("Prefixo existente encontrado — mantendo.")
            return
    step("Criando prefixo Wine...")
    subprocess.run(
        ["wineboot", "--init"], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    step("Instalando dependências Wine (d3dx9, vcrun2008, vcrun2010)...")
    subprocess.run(
        ["winetricks", "-q", "d3dx9", "vcrun2008", "vcrun2010"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    log("Prefixo pronto")


def mostrar_chave():
    print()
    _box_top()
    _box_row(f"{W}Chave do Produto{NC}")
    _box_row()
    _box_row(f"  {Y}{BLD}{PRODUCT_KEY}{NC}")
    _box_row()
    _box_row(f"{DIM}Seleciona com o mouse ou {B}Ctrl+Shift+C{NC}")
    _box_bot()
    print()
    input(f"  {DIM}Pressiona Enter para abrir o instalador...{NC} ")


def run_installer(installer_path: Path):
    step(f"Iniciando instalador: {installer_path.name}")
    subprocess.run(["wine", str(installer_path)], env=wine_env())


def find_game_bin() -> Path:
    candidates = [
        WINEPREFIX / "drive_c" / "Program Files (x86)" / "Electronic Arts" / "The Sims 3" / "Game" / "Bin",
        WINEPREFIX / "drive_c" / "Program Files" / "Electronic Arts" / "The Sims 3" / "Game" / "Bin",
        WINEPREFIX / "drive_c" / "users" / USERNAME / "Documents" / "Games" / "sims3rld" / "Game" / "Bin",
    ]
    for c in candidates:
        if c.exists() and any(c.glob("TS3*.exe")):
            return c
    matches = [m for m in WINEPREFIX.rglob("Game/Bin") if any(m.glob("TS3*.exe"))]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        warn("Múltiplas instalações encontradas:")
        for i, m in enumerate(matches, 1):
            print(f"  {G}{i}{NC}  {DIM}{m}{NC}")
        print()
        while True:
            escolha = input(f"  {DIM}Qual usar?{NC} › ").strip()
            if escolha.isdigit() and 1 <= int(escolha) <= len(matches):
                return matches[int(escolha) - 1]
            warn("Opção inválida.")
    die("Pasta Game/Bin não encontrada. Verifica onde o instalador instalou o jogo.")


def apply_crack(crack_exe: Path, game_bin: Path):
    dest = game_bin / "TS3.exe"
    step("Aplicando crack...")
    shutil.copy2(crack_exe, dest)
    dest.chmod(0o755)
    log("Crack aplicado")


def create_launcher(game_bin: Path):
    LAUNCHER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHER_PATH.write_text(
        f'#!/usr/bin/env bash\n'
        f'WINEPREFIX="{WINEPREFIX}" DISPLAY=":0" WAYLAND_DISPLAY="" \\\n'
        f'    wine "{game_bin}/TS3.exe" "$@"\n'
    )
    LAUNCHER_PATH.chmod(0o755)
    log(f"Launcher → {LAUNCHER_PATH}")


def create_desktop_entry(game_bin: Path):
    assets_dir = Path(__file__).parent / "assets"
    ico_src    = assets_dir / "TheSims3.ico"
    ICON_DEST.parent.mkdir(parents=True, exist_ok=True)
    if ico_src.exists():
        shutil.copy2(ico_src, ICON_DEST)
        icon_field = str(ICON_DEST)
    else:
        warn(f"Ícone não encontrado em {ico_src} — usando genérico")
        icon_field = "application-x-executable"
    DESKTOP_DEST.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP_DEST.write_text(
        f'[Desktop Entry]\n'
        f'Name=The Sims 3\n'
        f'Comment=The Sims 3 via Wine\n'
        f'Exec="{LAUNCHER_PATH}"\n'
        f'Icon={icon_field}\n'
        f'Terminal=false\n'
        f'Type=Application\n'
        f'Categories=Game;\n'
        f'StartupNotify=true\n'
    )
    DESKTOP_DEST.chmod(0o755)
    log(f"Desktop entry → {DESKTOP_DEST}")
    subprocess.run(
        ["update-desktop-database", str(HOME / ".local" / "share" / "applications")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _patch_ini(patch: dict):
    if not OPTIONS_PATH.exists():
        warn("Options.ini não encontrado para patch.")
        return
    texto = OPTIONS_PATH.read_text()
    sep_match = re.search(r"^\w+(\s*=\s*)", texto, re.MULTILINE)
    sep_str = sep_match.group(1) if sep_match else " = "
    for chave, valor in patch.items():
        novo = f"{chave}{sep_str}{valor}"
        texto, n = re.subn(
            rf"^{re.escape(chave)}\s*=.*$",
            novo,
            texto,
            flags=re.MULTILINE,
        )
        if n == 0:
            texto += f"\n{novo}\n"
    OPTIONS_PATH.write_text(texto)
    log(f"Options.ini atualizado")


def primeiro_run_patch(game_bin: Path, patch: dict):
    SIMS3_DOCS.mkdir(parents=True, exist_ok=True)
    env = wine_env()
    step("Iniciando primeiro run para gerar Options.ini...")
    proc = subprocess.Popen(
        ["wine", str(game_bin / "TS3.exe")],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log("Aguardando Options.ini...")
    timeout   = 120
    decorrido = 0
    while decorrido < timeout:
        if OPTIONS_PATH.exists() and OPTIONS_PATH.stat().st_size > 0:
            time.sleep(2)
            break
        time.sleep(1)
        decorrido += 1
        bar_w  = 30
        filled = int(decorrido / timeout * bar_w)
        bar    = f"{G}{'█' * filled}{DIM}{'░' * (bar_w - filled)}{NC}"
        print(f"\r  {bar}  {DIM}{decorrido}/{timeout}s{NC}", end="", flush=True)
    print()
    if not OPTIONS_PATH.exists():
        warn(f"Options.ini não criado em {timeout}s — jogo pode ter travado.")
        proc.terminate()
        return
    step("Options.ini detectado — encerrando o jogo...")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        proc.wait()
    _patch_ini(patch)


def _menu_opcao(titulo: str, opcoes: list[tuple[str, str]], atual: str) -> str:
    linhas = titulo.split("\n")
    print()
    _box_top()
    for linha in linhas:
        _box_row(f"{W}{linha}{NC}" if linha == linhas[0] else f"{Y}{linha}{NC}")
    _box_row()
    for i, (label, val) in enumerate(opcoes, 1):
        marcador = f"{Y}●{NC}" if val == atual else f"{DIM}○{NC}"
        _box_row(f"{marcador}  {G}{i}{NC}  {label}")
    _box_bot()
    print()
    while True:
        escolha = input(f"  {DIM}› Enter para manter atual:{NC} ").strip()
        if escolha == "":
            return atual
        if escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            return opcoes[int(escolha) - 1][1]
        warn("Opção inválida.")

def configurar_options_ini() -> dict:
    opcoes = dict(OPTIONS_PATCH)
    print()
    _box_top()
    _box_row(f"{W}Configuração do The Sims 3{NC}")
    _box_row()
    _box_row(f"{DIM}Configure antes de abrir para evitar erros de exibição{NC}")
    _box_row()
    _box_row(f"{Y}●{NC} = selecionado  │  Enter = mantém atual{NC}")
    _box_bot()

    resolucoes = [
        ("800×600",   "800 600 0"),
        ("1024×768",  "1024 768 0"),
        ("1280×720",  "1280 720 0"),
        ("1366×768",  "1366 768 0"),
        ("1600×900",  "1600 900 0"),
        ("1920×1080", "1920 1080 0"),
        ("2560×1440", "2560 1440 0"),
    ]
    opcoes["resolution"] = _menu_opcao("Resolução", resolucoes, opcoes["resolution"])

    tela = [("Tela cheia", "1"), ("Janela", "0")]
    opcoes["fullscreen"] = _menu_opcao(
        "Modo de exibição  " + f"{Y}aviso: tela cheia deixa o game escuro,\ntenho muita preguiça para resolver isso.{NC}",
        tela, opcoes["fullscreen"]
    )

    qualidades = [
        ("Baixa  (1)", "1"),
        ("Média  (2)", "2"),
        ("Alta   (3)", "3"),
    ]
    print()
    _box_top()
    _box_row(f"{W}Qualidade gráfica{NC}")
    _box_row(f"{DIM}Aplica em: texturas, sims, iluminação, árvores, efeitos{NC}")
    _box_bot()
    q = _menu_opcao("Qualidade gráfica", qualidades, opcoes["texturequality"])
    for chave in ("texturequality", "simquality", "lightingquality", "treequality", "visualeffects"):
        opcoes[chave] = q

    ref = [("Desligado", "0"), ("Ligado", "1")]
    opcoes["reflections"] = _menu_opcao("Reflexos", ref, opcoes["reflections"])

    edge = [("Desligado", "0"), ("Ligado", "1")]
    opcoes["edgesmoothing"] = _menu_opcao("Suavização de bordas (AA)", edge, opcoes["edgesmoothing"])

    dist = [
        ("Curta  (1)", "1"),
        ("Média  (2)", "2"),
        ("Longa  (3)", "3"),
    ]
    opcoes["drawdistance"] = _menu_opcao("Distância de renderização", dist, opcoes["drawdistance"])

    audio = [
        ("Baixa  (1)", "1"),
        ("Alta   (2)", "2"),
    ]
    opcoes["audioquality"] = _menu_opcao("Qualidade de áudio", audio, opcoes["audioquality"])

    aging = [("Desligado", "0"), ("Ligado", "1")]
    opcoes["enableaging"] = _menu_opcao("Envelhecimento dos sims", aging, opcoes["enableaging"])

    return opcoes


def perguntar_cleanup():
    if not DOWNLOAD_DIR.exists():
        return
    tamanho_mb = sum(f.stat().st_size for f in DOWNLOAD_DIR.rglob("*") if f.is_file()) // 1024 // 1024
    print()
    _box_top()
    _box_row(f"{W}Limpeza{NC}")
    _box_row()
    _box_row(f"Pasta temporária ocupa {Y}{tamanho_mb} MB{NC}")
    _box_row(f"{DIM}{DOWNLOAD_DIR}{NC}")
    _box_row()
    _box_row(f"{G}1{NC}  Remover e liberar espaço")
    _box_row(f"{G}2{NC}  Manter")
    _box_bot()
    print()
    if input(f"  {DIM}›{NC} ").strip() == "1":
        shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
        log("Pasta temporária removida")
    else:
        log(f"Pasta mantida")


def _link(texto, url):
    return f"\033]8;;{url}\033\\{texto}\033]8;;\033\\"


def menu_principal() -> str:
    print(r"""
    [0;37m█▀▀▀▀▀▀▀▀▀▀▀█ █▀▀▀█  █▀▀▀█  ▄▀▀▀▀▀▀▀▀▄        ▄▀▀▀▀▀▀▀▀▀█ █▀▀▀█ █▀▀▀█    █▀▀▀█  ▄▀▀▀▀▀▀▀▀▀█       ▄▀▀▀▀▀▀▀▀▄      [0m
    [0;97;47m░[0;34m░░░░░░░░░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;97;47m░[0;37m  [0;97;47m░[0;34m░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;37m▄▄▄[0;34m░░░░[0;97;47m░[0;37m      [0;97;47m░[0;34m░░░░[0;37m▄▄▄▄▄▄[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;37;44m▐[0;37m▌  ▐[0;37;44m▌[0;34m░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░░[0;37m▄▄▄▄▄▄[0;97;47m░[0;37m      [0;97;47m░[0;34m░░░░[0;37m▄▄▄[0;34m░░░[0;97;47m░[0;37m     [0m
    [0;90;47m▄▄▄▄[0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90;47m▄▄▄▄[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m  [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90m▒▒[0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m      [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90m▒▒▒░░░░[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m [0;97;47m▒[0;34m▒▒▒▒[0;97;47m▒[0;37m  [0;97;47m▒[0;34m▒▒▒▒[0;97;47m▒[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90m▒▒▒░░░░[0;37m      [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90m▒▒[0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m     [0m
    [0;90m█▓▒░[0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m█▓▒░[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m  [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m▒▒[0;97;47m▓[0;97;44m▄▄▄[0;97;47m▓[0;37m      [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m▒▒▒░░░░[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m [0;97;47m▓[0;34m▓▓▓▓[0;97;44m▐[0;97m▌▐[0;97;44m▌[0;34m▓▓▓▓[0;97;47m▓[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m▒▒▒░░░░[0;37m      [0;97;47m▓[0;97;44m▄▄▄[0;97;47m▓[0;90m▒▒[0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m     [0m
    [0;37m    [0;97;47m█[0;34m███[0;97;47m█[0;37m     [0;97;47m█[0;34m███[0;97;44m▀▀▀▀[0;34m███[0;97;47m█[0;37m [0;97;47m█[0;34m███[0;97;44m▀▀[0;97m█[0;90m█▓▓▒░[0;37m      [0;97;47m█[0;34m████[0;97;44m▀▀▀▀▀[0;97m▄[0;37m  [0;97;47m█[0;34m███[0;97m█[0;37m [0;97;47m█[0;34m█████[0;97;47m██[0;34m█████[0;97;47m█[0;37m [0;97;47m█[0;34m████[0;97;44m▀▀▀▀▀[0;97m▄[0;37m       [0;90m░▒▓▓█[0;97m█[0;97;44m▀▀[0;34m███[0;97;47m█[0;37m     [0m
    [0;37m    [0;97m█[0;94;44m░░░[0;97m█[0;37m     [0;97m█[0;94;44m░░░[0;97;44m▄▄▄▄[0;94;44m░░░[0;97m█[0;37m [0;97m█[0;94;44m░░░[0;97;44m▄▄[0;97m█[0;90m▀▀▀▀▀[0;37m      [0;90m█[0;90;47m▄[0;97;44m▄▄▄▄▄[0;94;44m░░░░[0;97;44m█[0;37m [0;97;44m█[0;94;44m░░░[0;97;44m█[0;37m [0;97;44m█[0;94;44m░░░[0;97;44m▄[0;94;44m░[0;97;44m▀▀[0;94;44m░[0;97;44m▄[0;94;44m░░░[0;97;44m█[0;37m [0;90m█[0;90;47m▄[0;97;44m▄▄▄▄▄[0;94;44m░░░░[0;97;44m█[0;37m      [0;90m▀▀▀▀▀[0;97m█[0;97;44m▄▄[0;94;44m░░░[0;97m█[0;37m     [0m
    [0;37m    [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m     [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;90m▓▓[0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;90m▒▒[0;97;47m▀[0;97;44m▀▀▀[0;97;47m▀[0;37m      [0;90m██▓▓▒▒▒[0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓▒[0;94;44m▒▒[0;90;47m▒▓[0;94;44m▒▒▒[0;90;47m▓[0;37m [0;90m██▓▓▒▒▒[0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m      [0;97;47m▀[0;97;44m▀▀▀[0;97;47m▀[0;90m▒▒[0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m     [0m
    [0;37m    [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m     [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;90m▓▓[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;90m▒▒[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m       [0;90m▀▓▓▒▒▒[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒▌[0;94;47m▐▌[0;90;47m▐▒[0;94;44m▓▓▓[0;90;47m▒[0;37m  [0;90m▀▓▓▒▒▒[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m      [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;90m▒▒[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m     [0m
    [0;37m    [0;90;47m░[0;94;44m███[0;90;47m░[0;37m     [0;90;47m░[0;94;44m███[0;90;47m░[0;90m▌[0;37m [0;90;47m░[0;94;44m███[0;90;47m░[0;37m [0;90;47m░[0;94;44m███[0;94m█[0;94;47m▄▄[0;94;44m████[0;90;47m░[0;37m      █[0;94;47m▄▄▄▄▄▄[0;94;44m████[0;90;47m░[0;37m [0;90;47m░[0;94;44m███[0;90;47m░[0;37m [0;90;47m░[0;94;44m███[0;90;47m░[0;90m▓[0;90;47m░░[0;90m▒[0;90;47m░[0;94;44m███[0;90;47m░[0;37m █[0;94;47m▄▄▄▄▄▄[0;94;44m████[0;90;47m░[0;37m      [0;90;47m░[0;94;44m████[0;94;47m▄▄[0;94m█[0;94;44m███[0;90;47m░[0;37m     [0m
    [0;37m    █[0;37;44m▄▄▄█[0;37m     █[0;37;44m▄▄▄[0;37m█[0;90m▌[0;37m █[0;37;44m▄▄▄[0;37m█ [0;90m░[0;90;47m▄[0;37;44m▄▄▄▄▄▄▄▄[0;90;47m▄[0;90m░[0;37m      █[0;37;44m▄▄▄▄▄▄▄▄▄[0;90;47m▄[0;90m░[0;37m █[0;37;44m▄▄▄[0;37m█ █[0;37;44m▄▄▄[0;37m█[0;90m▓[0;90;47m▌▐[0;90m░[0;37m█[0;37;44m▄▄▄[0;37m█ █[0;37;44m▄▄▄▄▄▄▄▄▄[0;90;47m▄[0;90m░[0;37m      [0;90m░[0;90;47m▄[0;37;44m▄▄▄▄▄▄▄▄[0;90;47m▄[0;90m░[0;37m     [0m
    [0;37m    [0;90m██▓▒░[0;37m     [0;90m█▓▓▒▒▌[0;37m [0;90m█▓▓▒▒[0;37m [0;90m░░▒▓▒▒▒▒▒▒░░[0;37m      [0;90m█▓▓▒▒▒▒▒▒▒░░[0;37m [0;90m█▓▓▒▒[0;37m [0;90m█▓▓▒▒▌▓░[0;37m [0;90m█▓▓▒▒[0;37m [0;90m█▓▓▒▒▒▒▒▒▒░░[0;37m      [0;90m░░▒▒▒▒▒▒▓▒░░[0;37m     [0m
    [0;37m    [0;90m██▓▒░[0;37m     [0;90m█▓▓▒▒▌[0;37m [0;90m█▓▓▒▒[0;37m  [0;90m░▒▓▒▒▒▒▒▒░[0;37m       [0;90m█▓▓▒▒▒▒▒▒▒░[0;37m  [0;90m█▓▓▒▒[0;37m [0;90m█▓▓▒▒▌▐[0;37m  [0;90m█▓▓▒▒[0;37m [0;90m█▓▓▒▒▒▒▒▒▒░[0;37m        [0;90m░▒▒▒▒▒▒▓▒░[0;37m      [0m
    [0;37m█▀▀▀▀▀▀▀▀▀▄  █▀▀▀█   █▀▀▀█      █▀▀▀█     █▀▀▀█ █▀▀▀▀▀▀▀▀▀▄   ▄▀▀▀▀▀▀▀▀▄  █▀▀▀▀▀▀▀▀▀▄  █▀▀▀█   █▀▀▀█ █▀▀▀▀▀▀▀▀▀▀▀█ █▀▀▀█  █▀▀▀█  ▄▀▀▀▀▀▀▀▀▄  █▀▀▀▀▀▀▀▀▀▄ [0m
    [0;97;47m░[0;34m░░░[0;37m▄▄▄[0;34m░░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;97;47m░[0;37m   [0;97;47m░[0;34m░░░[0;97;47m░[0;37m      [0;97;47m░[0;34m░░░[0;97;47m░[0;37m     [0;97;47m░[0;34m░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;37m▄▄▄[0;34m░░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░░[0;37m▄▄[0;34m░░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;37m▄▄▄[0;34m░░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;97;47m░[0;37m   [0;97;47m░[0;34m░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░░░░░░░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;97;47m░[0;37m  [0;97;47m░[0;34m░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;37m▄▄▄[0;34m░░░░[0;97;47m░[0;37m [0;97;47m░[0;34m░░░[0;37m▄▄▄[0;34m░░░░[0;97;47m░[0m
    [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90m▒▒[0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m   [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m      [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m     [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90m▓▓[0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90m▒▒[0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90m▒▒[0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m   [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m [0;90;47m▄▄▄▄[0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90;47m▄▄▄▄[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m  [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90m▓▓[0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;37m [0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0;90m▓▓[0;97;47m▒[0;34m▒▒▒[0;97;47m▒[0m
    [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m▒▒[0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m   [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m      [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m     [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m▒▒[0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m▒▒[0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m▒▒[0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m   [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m [0;90m█▓▒░[0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m█▓▒░[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m  [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m▒▒[0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;37m [0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0;90m▒▒[0;97;47m▓[0;34m▓▓▓[0;97;47m▓[0m
    [0;97;47m█[0;34m███[0;97;44m▀▀▀[0;34m███[0;97m█[0;37m  [0;90;47m▄[0;97;44m▄[0;34m██[0;97;44m▀[0;97m▄[0;37m [0;97m▄[0;97;44m▀[0;34m██[0;97;44m▄▀[0;37m      [0;97;47m█[0;34m███[0;97m█[0;37m     [0;97;47m█[0;34m███[0;97m█[0;37m [0;97;47m█[0;34m███[0;97;47m█[0;37m  [0;97;47m█[0;34m███[0;97;47m█[0;37m [0;97;47m█[0;34m███[0;97;44m▀▀▀▀[0;34m███[0;97;47m█[0;37m [0;97;47m█[0;34m███[0;97;44m▀▀▀▀[0;34m███[0;97m█[0;37m [0;90;47m▄[0;97;44m▄[0;34m██[0;97;44m▀[0;97m▄[0;37m [0;97m▄[0;97;44m▀[0;34m██[0;97;44m▄▀[0;37m     [0;97;47m█[0;34m███[0;97;47m█[0;37m     [0;97;47m█[0;34m███[0;97;44m▀▀▀▀[0;34m███[0;97;47m█[0;37m [0;97;47m█[0;34m███[0;97;47m█[0;37m  [0;97;47m█[0;34m███[0;97;47m█[0;37m [0;97;47m█[0;34m███[0;97;47m█[0;37m  [0;97;47m█[0;34m███[0;97;47m█[0m
    [0;97m█[0;94;44m░░░[0;97;44m▄▄▄[0;94;44m░░░░[0;97;44m█[0;37m [0;90m██[0;90;47m▄[0;97;44m▄[0;94;44m░░[0;97;44m▀[0;94;44m░░[0;97;44m▄▀[0;90m░░[0;37m      [0;97;44m█[0;94;44m░░░[0;97;44m█[0;37m     [0;97;44m█[0;94;44m░░░[0;97;44m█[0;37m [0;97m█[0;94;44m░░░[0;97m█[0;37m  [0;97m█[0;94;44m░░░[0;97;44m█[0;37m [0;97;44m█[0;94;44m░░░[0;97;44m▄▄▄▄[0;94;44m░░░[0;97;44m█[0;37m [0;97m█[0;94;44m░░░[0;97;44m▄▄▄▄▄▄▄[0;90;47m▄[0;37m [0;90m██[0;90;47m▄[0;97;44m▄[0;94;44m░░[0;97;44m▀[0;94;44m░░[0;97;44m▄▀[0;90m░░[0;37m     [0;97m█[0;94;44m░░░[0;97m█[0;37m     [0;97m█[0;94;44m░░░[0;97;44m▄▄▄▄[0;94;44m░░░[0;97m█[0;37m [0;97m█[0;94;44m░░░[0;97m█[0;37m  [0;97;44m█[0;94;44m░░░[0;97;44m█[0;37m [0;97m█[0;94;44m░░░[0;97m█[0;37m  [0;97m█[0;94;44m░░░[0;97;44m█[0m
    [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;90m▒▒[0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m [0;90m▀██▓[0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;90m░░░[0;37m       [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m     [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m  [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;90m▓▓[0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;90m██▓▓▒░░[0;37m [0;90m▀██▓[0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;90m░░░[0;37m      [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m     [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;90m▓▓[0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m  [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0;37m  [0;90;47m▓[0;94;44m▒▒▒[0;90;47m▓[0m
    [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;90m▒▒[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m   [0;90m▀▓[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;90m░░[0;37m        [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m     [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m  [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;90m▓▓[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;90m██▓▓▒░[0;37m    [0;90m▀▓[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;90m░░[0;37m       [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m     [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;90m▓▓[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;90m▄▄[0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0;37m  [0;90;47m▒[0;94;44m▓▓▓[0;90;47m▒[0m
    [0;90;47m░[0;94;44m███[0;94m█[0;94;47m▄▄[0;94;44m████[0;90;47m░[0;37m     [0;90;47m░[0;94;44m███[0;90;47m░[0;90m▌[0;37m         [0;90;47m░[0;94;44m███[0;94;47m▄▄▄▄[0;90;47m░[0;37m [0;90;47m░[0;94;44m███[0;90;47m░[0;37m [0;90;47m░[0;94;44m███[0;90;47m░[0;37m  [0;90;47m░[0;94;44m███[0;90;47m░[0;37m [0;90;47m░[0;94;44m███[0;90;47m░[0;90m▌[0;37m [0;90;47m░[0;94;44m███[0;90;47m░[0;37m [0;90;47m░[0;94;44m███[0;90;47m░[0;37m            [0;90;47m░[0;94;44m███[0;90;47m░[0;90m▌[0;37m        [0;90;47m░[0;94;44m███[0;90;47m░[0;37m     [0;90;47m░[0;94;44m███[0;90;47m░[0;90m▌[0;37m [0;90;47m░[0;94;44m███[0;90;47m░[0;37m [0;90;47m░[0;94;44m███[0;94m█[0;94;47m▄▄[0;94;44m████[0;90;47m░[0;37m [0;90;47m░[0;94;44m███[0;90;47m░[0;37m  [0;90;47m░[0;94;44m███[0;90;47m░[0m
    [0;37m█[0;37;44m▄▄▄▄▄▄▄▄▄[0;90;47m▄[0;90m░[0;37m     █[0;37;44m▄▄▄[0;37m█[0;90m▌[0;37m         [0;90m░[0;90;47m▄[0;37;44m▄▄▄▄▄▄█[0;37m █[0;37;44m▄▄▄[0;37m█ █[0;37;44m▄▄▄█[0;37m  [0;37;44m█▄▄▄█[0;37m █[0;37;44m▄▄▄[0;37m█[0;90m▌[0;37m █[0;37;44m▄▄▄[0;37m█ █[0;37;44m▄▄▄[0;37m█            █[0;37;44m▄▄▄[0;37m█[0;90m▌[0;37m        █[0;37;44m▄▄▄█[0;37m     █[0;37;44m▄▄▄[0;37m█[0;90m▌[0;37m █[0;37;44m▄▄▄[0;37m█ [0;90m░[0;90;47m▄[0;37;44m▄▄▄▄▄▄▄▄[0;90;47m▄[0;90m░[0;37m █[0;37;44m▄▄▄█[0;37m  [0;37;44m█▄▄▄█[0m
    [0;90m█▓▓▒▒▒▒▒▒▒░░[0;37m     [0;90m█▓▓▒▒▌[0;37m         [0;90m░░▒▓▒▒▒▒▒[0;37m [0;90m█▓▓▒▒[0;37m [0;90m██▓▒░[0;37m  [0;90m██▓▒░[0;37m [0;90m█▓▓▒▒▌[0;37m [0;90m█▓▓▒▒[0;37m [0;90m█▓▓▒░[0;37m            [0;90m█▓▓▒▒▌[0;37m        [0;90m██▓▒░[0;37m     [0;90m█▓▓▒▒▌[0;37m [0;90m█▓▓▒▒[0;37m [0;90m░░▒▓▓██▓▓▒░░[0;37m [0;90m██▓▒░[0;37m  [0;90m██▓▒░[0m
    [0;90m█▓▓▒▒▒▒▒▒▒░[0;37m      [0;90m█▓▓▒▒▌[0;37m          [0;90m░▒▓▒▒▒▒▒[0;37m [0;90m█▓▓▒▒[0;37m [0;90m██▓▒░[0;37m  [0;90m██▓▒░[0;37m [0;90m█▓▓▒▒▌[0;37m [0;90m█▓▓▒▒[0;37m [0;90m█▓▓▒░[0;37m            [0;90m█▓▓▒▒▌[0;37m        [0;90m██▓▒░[0;37m     [0;90m█▓▓▒▒▌[0;37m [0;90m█▓▓▒▒[0;37m  [0;90m░▒▓▓██▓▓▒░[0;37m  [0;90m██▓▒░[0;37m  [0;90m██▓▒░[0m
""")

    print(f"\n  {DIM}github{NC}    {_link(f'{C}LinaPython{NC}', 'https://github.com/LinaPython')}")
    print(f"  {DIM}youtube{NC}   {_link(f'{C}Inscreva-se{NC}', 'https://www.youtube.com/@LinaSemCalcinha')}")
    print(f"  {DIM}roblox{NC}    {_link(f'{C}play my game{NC}', 'https://www.roblox.com/games/112548124461222')}")

    print()
    _box_top()
    _box_row(f"{W}The Sims 3  {DIM}— Instalador Linux via Wine{NC}")
    _box_row()
    _box_row(f"{G}1{NC}  Instalação completa   {DIM}download + prefixo + jogo{NC}")
    _box_row(f"{G}2{NC}  Instalar              {DIM}pula download{NC}                  ")
    _box_row(f"{G}3{NC}  Aplicar crack         {DIM}caso o jogo não abra{NC}   ")
    _box_row(f"{G}4{NC}  Sair")
    _box_bot()
    print()
    return input(f"  {DIM}›{NC} ").strip()


def main():
    check_deps()

    while True:
        opcao = menu_principal()

        if opcao == "1":
            zip_path     = fluxo_download()
            extract_root = extract_zip(zip_path, DOWNLOAD_DIR / "extracted")
            installer    = find_installer(extract_root)
            crack_exe    = find_crack(extract_root)
            setup_wine_prefix()
            mostrar_chave()
            run_installer(installer)
            game_bin = find_game_bin()
            apply_crack(crack_exe, game_bin)
            create_launcher(game_bin)
            create_desktop_entry(game_bin)
            opcoes_ini = configurar_options_ini()
            primeiro_run_patch(game_bin, opcoes_ini)
            break

        elif opcao == "2":
            extract_root = DOWNLOAD_DIR / "extracted"
            if not extract_root.exists():
                warn(f"Pasta extraída não encontrada: {extract_root}")
                warn("Roda a opção 1 primeiro ou extrai o zip manualmente.")
                continue
            installer = find_installer(extract_root)
            crack_exe = find_crack(extract_root)
            setup_wine_prefix()
            mostrar_chave()
            run_installer(installer)
            game_bin = find_game_bin()
            apply_crack(crack_exe, game_bin)
            create_launcher(game_bin)
            create_desktop_entry(game_bin)
            opcoes_ini = configurar_options_ini()
            primeiro_run_patch(game_bin, opcoes_ini)
            break

        elif opcao == "3":
            extract_root = DOWNLOAD_DIR / "extracted"
            if not extract_root.exists():
                die(f"Pasta extraída não encontrada: {extract_root}")
            crack_exe = find_crack(extract_root)
            game_bin  = find_game_bin()
            apply_crack(crack_exe, game_bin)
            create_launcher(game_bin)
            create_desktop_entry(game_bin)
            opcoes_ini = configurar_options_ini()
            primeiro_run_patch(game_bin, opcoes_ini)
            break

        elif opcao == "4":
            print()
            sys.exit(0)

        else:
            warn("Opção inválida.")

    perguntar_cleanup()

    print()
    _box_top()
    _box_row(f"{BG}Instalação concluída{NC}")
    _box_row()
    _box_row(f"{DIM}Ícone criado na área de trabalho{NC}")
    _box_row()
    _box_row(f"PATH  {C}export PATH=\"$HOME/.local/bin:$PATH\"{NC}")
    _box_row()
    _box_row(f"{DIM}Para desinstalar, rode:{NC}  {C}python uninstall.py{NC}")
    _box_bot()
    print()


if __name__ == "__main__":
    main()