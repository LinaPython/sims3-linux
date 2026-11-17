#!/usr/bin/env python3
# push pre cli novo, tá muito confuso para o tipo de pessoa que vai usar isso aqui, simplificar o maximo para usuarios leigos.


import os
import re
import sys
import time
import shutil
import zipfile
import subprocess
import getpass
from html import unescape
from pathlib import Path

try:
    from curl_cffi import requests as cffi_requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[erro] Instala: pip install -r requirements.txt")
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


R = "\033[0;31m"; G = "\033[0;32m"; Y = "\033[1;33m"
C = "\033[0;36m"; B = "\033[1;34m"; NC = "\033[0m"
L = "\033[1;34;4m"; BR = "\033[1;31m"; BG = "\033[1;32m" 

def log(msg):  print(f"{G}[sims3]{NC} {msg}")
def warn(msg): print(f"{Y}[warn]{NC}  {msg}")
def die(msg):  print(f"{R}[erro]{NC}  {msg}", file=sys.stderr); sys.exit(1)
def sep():     print(f"{B}{'─' * 55}{NC}")


def check_deps():
    for cmd in ("wine", "winetricks"):
        if not shutil.which(cmd):
            die(f"'{cmd}' não encontrado. Instala antes de continuar.")


_CDN_RE = re.compile(r'https://download\d+\.mediafire\.com/[^\s"\'<>]+')

def mediafire_direct_link(url_pagina: str) -> str:
    if not url_pagina.endswith("/file"):
        url_pagina = url_pagina.rstrip("/") + "/file"

    sessao = cffi_requests.Session(impersonate="chrome120")

    for tentativa, espera in enumerate([0, 3, 6], start=1):
        if espera:
            log(f"Cloudflare challenge — aguardando {espera}s (tentativa {tentativa}/3)...")
            time.sleep(espera)

        resp = sessao.get(url_pagina, timeout=20, allow_redirects=True)

        if resp.status_code == 403:
            continue
        if resp.status_code != 200:
            raise ConnectionError(f"Mediafire retornou HTTP {resp.status_code}")

        m = _CDN_RE.search(unescape(resp.text))
        if m:
            return m.group(0).rstrip("\"'\\&")

        raise ValueError("Página carregou mas link CDN não encontrado no HTML.")

    raise ConnectionError("Cloudflare bloqueou após 3 tentativas (403).")


def download_file(url: str, dest: Path) -> Path:
    filename = url.split("/")[-1].split("?")[0] or "LinaPySims3.zip"
    output   = dest / filename
    dest.mkdir(parents=True, exist_ok=True)

    log(f"Baixando the sims 3...")
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
                    bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
                    print(
                        f"\r  [{bar}] {pct:.1f}%  "
                        f"{downloaded // 1024 // 1024}MB/{total // 1024 // 1024}MB",
                        end="", flush=True,
                    )
    print()
    log(f"Download completo: {output}")
    return output

def fluxo_download() -> Path:
    zip_esperado = DOWNLOAD_DIR / "LinaPySims3.zip"

    while True:
        sep()
        print(f"\n  {B}Download{NC}\n")
        print(f"  {G}1{NC}. Baixar the sims 3 via Mediafire")
        if zip_esperado.exists():
            tamanho = zip_esperado.stat().st_size // 1024 // 1024
            print(f"  {G}2{NC}. Usar arquivo já baixado  {Y}({zip_esperado}, {tamanho}MB){NC}")
        print()

        escolha = input("  Escolha: ").strip()

        if escolha == "2" and zip_esperado.exists():
            log(f"Usando arquivo existente: {zip_esperado}")
            return zip_esperado

        if escolha in ("1", "2"):
            while True:
                try:
                    direct_url = mediafire_direct_link(MEDIAFIRE_URL)
                    log(f"Link direto: {direct_url[:72]}...")
                    return download_file(direct_url, DOWNLOAD_DIR)
                except (ConnectionError, ValueError) as e:
                    print()
                    warn(str(e))
                    sep()
                    print(f"\n  {R}Download falhou.{NC}\n")
                    print(f"  {G}1{NC}. Tentar novamente")
                    print(f"  {G}2{NC}. Cancelar")
                    print()
                    if input("  Escolha: ").strip() != "1":
                        die("Download cancelado.")
        else:
            warn("Opção inválida.")


def extract_zip(zip_path: Path, dest: Path) -> Path:
    log(f"Extraindo {zip_path.name}...")
    dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)

    contents = list(dest.iterdir())
    if len(contents) == 1 and contents[0].is_dir():
        return contents[0]
    return dest


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
    env = {**os.environ, "WINEPREFIX": str(WINEPREFIX), "DISPLAY": ":0", "WAYLAND_DISPLAY": ""}

    if WINEPREFIX.exists():
        warn(f"Prefixo existente em {WINEPREFIX} — mantendo, pulando criação.")
        return

    log("Criando prefixo Wine...")
    subprocess.run(
        ["wineboot", "--init"], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    log("Instalando dependências (d3dx9, vcrun2008, vcrun2010)...")
    subprocess.run(
        ["winetricks", "-q", "d3dx9", "vcrun2008", "vcrun2010"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    log("Prefixo pronto.")


def mostrar_chave():
    sep()
    print(f"\n  {B}Chave do Produto{NC}\n")
    print(f"  {Y}{PRODUCT_KEY}{NC}\n")
    print(f"  Seleciona o texto acima com o mouse para copiar.")
    print(f"  Ou usa {C}Ctrl+Shift+C{NC} no terminal.\n")
    input("  Pressiona Enter quando estiver pronto para abrir o instalador... ")


def run_installer(installer_path: Path):
    log(f"Iniciando instalador: {installer_path.name}")
    env = {**os.environ, "WINEPREFIX": str(WINEPREFIX), "DISPLAY": ":0", "WAYLAND_DISPLAY": ""}
    subprocess.run(["wine", str(installer_path)], env=env)


def find_game_bin() -> Path:
    candidates = [
        WINEPREFIX / "drive_c" / "Program Files (x86)" / "Electronic Arts" / "The Sims 3" / "Game" / "Bin",
        WINEPREFIX / "drive_c" / "Program Files" / "Electronic Arts" / "The Sims 3" / "Game" / "Bin",
        WINEPREFIX / "drive_c" / "users" / USERNAME / "Documents" / "Games" / "sims3rld" / "Game" / "Bin",
    ]
    for c in candidates:
        if c.exists() and any(c.glob("TS3*.exe")):
            return c

    matches = list(WINEPREFIX.rglob("Game/Bin"))
    if matches:
        return matches[0]

    die(
        "Pasta Game/Bin não encontrada após instalação.\n"
        "       Verifica onde o instalador instalou o jogo."
    )


def apply_crack(crack_exe: Path, game_bin: Path):
    dest = game_bin / "TS3.exe"
    log(f"Aplicando crack → {dest}")
    shutil.copy2(crack_exe, dest)
    dest.chmod(0o755)
    log("Crack aplicado.")


def create_launcher(game_bin: Path):
    LAUNCHER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHER_PATH.write_text(
        f"#!/usr/bin/env bash\n"
        f"WINEPREFIX=\"{WINEPREFIX}\" DISPLAY=\":0\" WAYLAND_DISPLAY=\"\" \\\n"
        f"    wine \"{game_bin}/TS3.exe\" \"$@\"\n"
    )
    LAUNCHER_PATH.chmod(0o755)
    log(f"Launcher criado: {LAUNCHER_PATH}")


def create_desktop_entry(game_bin: Path):
    assets_dir = Path(__file__).parent / "assets"
    ico_src    = assets_dir / "TheSims3.ico"

    ICON_DEST.parent.mkdir(parents=True, exist_ok=True)

    if ico_src.exists():
        shutil.copy2(ico_src, ICON_DEST)
        log(f"Ícone copiado: {ICON_DEST}")
        icon_field = str(ICON_DEST)
    else:
        warn(f"Ícone não encontrado em {ico_src} — usando ícone genérico.")
        icon_field = "application-x-executable"

    DESKTOP_DEST.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP_DEST.write_text(
        f"[Desktop Entry]\n"
        f"Name=The Sims 3\n"
        f"Comment=The Sims 3 via Wine\n"
        f"Exec={LAUNCHER_PATH}\n"
        f"Icon={icon_field}\n"
        f"Terminal=false\n"
        f"Type=Application\n"
        f"Categories=Game;\n"
        f"StartupNotify=true\n"
    )
    DESKTOP_DEST.chmod(0o755)
    log(f"Desktop entry criado: {DESKTOP_DEST}")

    subprocess.run(
        ["update-desktop-database", str(HOME / ".local" / "share" / "applications")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


SIMS3_DOCS   = HOME / "Documents" / "Electronic Arts" / "The Sims 3"
OPTIONS_PATH = SIMS3_DOCS / "Options.ini"

OPTIONS_PATCH = {
    "texturequality":   "3",
    "visualeffects":    "3",
    "simquality":       "3",
    "lightingquality":  "2",
    "treequality":      "2",
    "reflections":      "1",
    "edgesmoothing":    "0",
    "drawdistance":     "3",
    "audioquality":     "2",
    "enableaging":      "1",
    "fullscreen":       "1",
    "resolution":       "1920 1080 0",
}


def _patch_ini(patch: dict):
    """Lê o Options.ini gerado pelo jogo e sobrescreve apenas as chaves do patch."""
    if not OPTIONS_PATH.exists():
        warn("Options.ini não encontrado para patch.")
        return

    texto = OPTIONS_PATH.read_text()
    for chave, valor in patch.items():
        texto = re.sub(
            rf"^{re.escape(chave)}\s*=.*$",
            f"{chave} = {valor}",
            texto,
            flags=re.MULTILINE,
        )
        if not re.search(rf"^{re.escape(chave)}\s*=", texto, re.MULTILINE):
            texto += f"\n{chave} = {valor}\n"

    OPTIONS_PATH.write_text(texto)
    log(f"Options.ini patcheado: {OPTIONS_PATH}")


def primeiro_run_patch(game_bin: Path, patch: dict):
    """
    Abre o jogo, espera o Options.ini ser criado,
    mata o processo e aplica o patch.
    """
    SIMS3_DOCS.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "WINEPREFIX": str(WINEPREFIX), "DISPLAY": ":0", "WAYLAND_DISPLAY": ""}

    log("Iniciando primeiro run para gerar Options.ini...")
    proc = subprocess.Popen(
        ["wine", str(game_bin / "TS3.exe")],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    log("Aguardando Options.ini ser criado pelo jogo...")
    timeout = 120  
    intervalo = 1
    decorrido = 0

    while decorrido < timeout:
        if OPTIONS_PATH.exists() and OPTIONS_PATH.stat().st_size > 0:
            time.sleep(2)
            break
        time.sleep(intervalo)
        decorrido += intervalo
        print(f"\r  aguardando... {decorrido}s/{timeout}s", end="", flush=True)
    print()

    if not OPTIONS_PATH.exists():
        warn(f"Options.ini não foi criado em {timeout}s — o jogo pode ter travado.")
        proc.terminate()
        return

    log("Options.ini detectado — encerrando o jogo...")
    subprocess.run(
        ["wineserver", "-k"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    proc.wait(timeout=10)

    _patch_ini(patch)


def _menu_opcao(titulo: str, opcoes: list[tuple[str, str]], atual: str) -> str:
    """Exibe menu numerado e retorna o valor escolhido."""
    sep()
    print(f"\n  {B}{titulo}{NC}\n")
    for i, (label, _) in enumerate(opcoes, 1):
        marcador = f"{Y}*{NC}" if opcoes[i-1][1] == atual else " "
        print(f"  {marcador} {G}{i}{NC}. {label}")
    print()
    while True:
        escolha = input("  Escolha (Enter para manter atual): ").strip()
        if escolha == "":
            return atual
        if escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            return opcoes[int(escolha) - 1][1]
        warn("Opção inválida.")


def configurar_options_ini() -> dict:
    opcoes = dict(OPTIONS_PATCH)

    
    print("  +======================================+")
    print("  |                                      |")
    print(f"  |   {BG}Configuração do The Sims 3{NC}         |")
    print("  |                                      |")
    print("  +======================================+")
    print("  |                                      |")
    print(f"  |  {Y}confiuguere as opções do the sims{NC}   |")
    print(f"  |  {Y}antes de abrir para evitar erros{NC}    |")
    print("  |                                      |")
    print("  +======================================+")
    print(f"  {C}* = valor atual selecionado  |  Enter = mantém{NC}\n")


    resolucoes = [
        ("800x600",   "800 600 0"),
        ("1024x768",  "1024 768 0"),
        ("1280x720",  "1280 720 0"),
        ("1366x768",  "1366 768 0"),
        ("1600x900",  "1600 900 0"),
        ("1920x1080", "1920 1080 0"),
        ("2560x1440", "2560 1440 0"),
    ]
    opcoes["resolution"] = _menu_opcao("Resolução", resolucoes, opcoes["resolution"])


    tela = [("Tela cheia", "1"), ("Janela", "0")]
    opcoes["fullscreen"] = _menu_opcao(f"Modo de exibição\n  {Y}aviso: tela cheia deixa o jogo escuro, infelizmente tenho muita preguiça pra resolver isso", tela, opcoes["fullscreen"])


    qualidades = [
        ("Baixa  (1)", "1"),
        ("Média  (2)", "2"),
        ("Alta   (3)", "3"),
    ]
    sep()
    print(f"\n  {B}Qualidade gráfica{NC}")
    print(f"  Aplica em: texturas, sims, iluminação, árvores, efeitos visuais\n")
    q = _menu_opcao("Qualidade gráfica", qualidades, opcoes["texturequality"])
    for chave in ("texturequality", "simquality", "lightingquality",
                  "treequality", "visualeffects"):
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
    tamanho = sum(f.stat().st_size for f in DOWNLOAD_DIR.rglob("*") if f.is_file())
    tamanho_mb = tamanho // 1024 // 1024
    sep()
    print(f"\n  {B}Limpeza{NC}\n")
    print(f"  A pasta temporária {Y}{DOWNLOAD_DIR}{NC}")
    print(f"  ocupa {Y}{tamanho_mb}MB{NC} e não é mais necessária.\n")
    print(f"  {G}1{NC}. Remover e liberar espaço")
    print(f"  {G}2{NC}. Manter")
    print()
    if input("  Escolha: ").strip() == "1":
        shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
        log("Pasta temporária removida.")
    else:
        log(f"Pasta mantida em {DOWNLOAD_DIR}")

def link(texto, url):
    # OSC 8: \033]8;;URL\033\\TEXTO\033]8;;\033\\
    return f"\033]8;;{url}\033\\{texto}\033]8;;\033\\"

def menu_principal() -> str:
    sep()

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



    print(f"\n  {B}github:{NC} {link('clique aqui', 'https://github.com/LinaPython')}")
    print(f"  {B}youtube:{NC} {link('clique aqui', 'https://www.youtube.com/@LinaSemCalcinha')}")
    print(f"  {B}play my game:{NC} {link('clique aqui', 'https://www.roblox.com/games/112548124461222')}")
    print(f"\n  {G}1{NC}. Instalação completa  (download + prefixo + jogo)")
    print(f"  {G}2{NC}. Só instalar          (pula download — faz a instalção do game)")
    print(f"  {G}3{NC}. Só aplicar crack     (caso o the sims 3 não abra)")
    print(f"  {G}4{NC}. Sair")
    print()
    return input("  Escolha: ").strip()

def main():
    check_deps()
    log(f"Usuário: {USERNAME}  |  Prefixo: {WINEPREFIX}")

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
                warn("Roda a opção 1 primeiro ou extrai o zip manualmente para essa pasta.")
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
            print("  Saindo.")
            sys.exit(0)

        else:
            warn("Opção inválida.")

    perguntar_cleanup()

    sep()
    log("Instalação completa.")
    log("o icone do the sims 3 foi criado na sua area de trabalho")
    log(f"PATH necessário:  export PATH=\"$HOME/.local/bin:$PATH\"")
    log(
        f"Para desinstalar: rm -rf "
        f"\"{WINEPREFIX}\" "
        f"\"{LAUNCHER_PATH}\" "
        f"\"{ICON_DEST}\" "
        f"\"{DESKTOP_DEST}\" "
        f"\"{SIMS3_DOCS}\""
    )
    sep()

if __name__ == "__main__":
    main()