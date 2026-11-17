#!/usr/bin/env python3

import sys
import shutil
import subprocess
from pathlib import Path

HOME          = Path.home()
WINEPREFIX    = HOME / ".wine_sims3_LinaPython"
LAUNCHER_PATH = HOME / ".local" / "bin" / "sims3"
ICON_DEST     = HOME / ".local" / "share" / "icons" / "TheSims3.ico"
DESKTOP_DEST  = HOME / ".local" / "share" / "applications" / "sims3.desktop"
SIMS3_DOCS    = HOME / "Documents" / "Electronic Arts" / "The Sims 3"
DOWNLOAD_DIR  = HOME / "Downloads" / "sims3_tmp"

NC  = "\033[0m";   R  = "\033[0;31m";  G  = "\033[0;32m"
Y   = "\033[1;33m"; B  = "\033[1;34m";  W  = "\033[1;37m"
DIM = "\033[2m";   C  = "\033[0;36m"


def _box_top(width=60):
    print(f"{DIM}╭{'─' * (width - 2)}╮{NC}")

def _box_bot(width=60):
    print(f"{DIM}╰{'─' * (width - 2)}╯{NC}")

def _box_row(text="", width=60, pad=2):
    import re
    inner = width - 2
    line  = f"{' ' * pad}{text}"
    vis   = len(re.sub(r'\033\[[0-9;]*m', '', line))
    print(f"{DIM}│{NC}{line}{' ' * max(0, inner - vis)}{DIM}│{NC}")

def log(msg):  print(f"  {G}✓{NC}  {msg}")
def warn(msg): print(f"  {Y}!{NC}  {msg}")
def skip(msg): print(f"  {DIM}–{NC}  {DIM}{msg}{NC}")


TARGETS = [
    (WINEPREFIX,    "Prefixo Wine   (~/.wine_sims3_LinaPython)",   True),
    (LAUNCHER_PATH, "Launcher       (~/.local/bin/sims3)",         False),
    (ICON_DEST,     "Ícone          (~/.local/share/icons/...)",   False),
    (DESKTOP_DEST,  "Desktop entry  (~/.local/share/applications/...)", False),
    (SIMS3_DOCS,    "Saves e mods   (~/Documents/Electronic Arts          ", True),
    (DOWNLOAD_DIR,  "Pasta temp     (~/Downloads/sims3_tmp)",      True),
]


def main():
    print()
    _box_top()
    _box_row(f"{W}Desinstalador — The Sims 3{NC}")
    _box_row()
    _box_row(f"{DIM}Seleciona o que remover{NC}")
    _box_bot()
    print()

    selecionados = {}
    for i, (path, label, _) in enumerate(TARGETS, 1):
        existe = path.exists()
        status = f"{G}encontrado{NC}" if existe else f"{DIM}não encontrado{NC}"
        print(f"  {G}{i}{NC}  {label}")
        print(f"     {status}")
        print()
        if existe:
            resp = input(f"     {DIM}Remover? (s/N){NC} › ").strip().lower()
            selecionados[i] = resp == "s"
        else:
            selecionados[i] = False

    remover = [(path, label, big) for i, (path, label, big) in enumerate(TARGETS, 1) if selecionados.get(i)]

    if not remover:
        print()
        warn("Nada selecionado para remover.")
        sys.exit(0)

    print()
    _box_top()
    _box_row(f"{Y}Confirmar remoção{NC}")
    _box_row()
    for _, label, _ in remover:
        _box_row(f"{R}✗{NC}  {label}")
    _box_bot()
    print()

    confirm = input(f"  {DIM}Continuar? (s/N){NC} › ").strip().lower()
    if confirm != "s":
        print()
        warn("Cancelado.")
        sys.exit(0)

    print()
    for path, label, is_dir in remover:
        if not path.exists():
            skip(f"Já removido: {path.name}")
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            log(label.split("(")[0].strip())
        except Exception as e:
            warn(f"Erro ao remover {path}: {e}")

    subprocess.run(
        ["update-desktop-database", str(HOME / ".local" / "share" / "applications")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    print()
    _box_top()
    _box_row(f"{G}Desinstalação concluída{NC}")
    _box_bot()
    print()


if __name__ == "__main__":
    main()