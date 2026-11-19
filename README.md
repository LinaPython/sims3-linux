# The Sims 3 — Instalador Linux via Wine


![banner](https://i.imgur.com/3RnkT0G.gif)

Instala automaticamente o The Sims 3 no Linux via Wine.  

---

## Preview


![menu](https://i.imgur.com/CSdmGCI.png)
![jogo](https://i.imgur.com/P3tzKSq.gif)

---

## Requisitos

| Dependência | Versão mínima | Instalar |
|---|---|---|
| Python | 3.11+ | ver abaixo |
| Wine | 7.0+ | ver abaixo |
| Winetricks | qualquer | ver abaixo |

**NVIDIA:** instala `lib32-nvidia-utils` (Arch) ou `wine32:i386` (Ubuntu/Debian) antes de rodar. Sem eles o Wine não renderiza via driver proprietário.

---

**Arch Linux**
```bash
sudo pacman -S wine winetricks python python-pip git
```
```bash
sudo pacman -S lib32-nvidia-utils #para usuarios nvidia, ignore se sua gpu for outra.
```
**Ubuntu / Debian**
```bash
sudo dpkg --add-architecture i386
sudo apt install wine wine32:i386 winetricks python3 python3-pip python3-venv git
```

---

## Instalação

```bash
git clone https://github.com/LinaPython/sims3-linux
cd sims3-linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
### Chave do produto

Copie a chave utilizando o atalho `CTRL + SHIFT + C` e pressione `ENTER` para confirmar. Em seguida, cole a chave no campo indicado pelo instalador.

![Copiar chave](https://i.imgur.com/iF636c7.gif) ![Colar chave](https://i.imgur.com/flLFkbw.gif)

---

## Uso

```
╭──────────────────────────────────────────────────────────╮
│  The Sims 3  — Instalador Linux via Wine                 │
│                                                          │
│  1  Instalação completa   download + prefixo + jogo      │
│  2  Só instalar           pula download, usa zip         │
│  3  Só aplicar crack      caso o jogo não abra           │
│  4  Sair                                                 │
╰──────────────────────────────────────────────────────────╯
```

**Opção 1** — fluxo completo: baixa o zip do Mediafire, extrai, cria o prefixo Wine,
abre o instalador, aplica o crack, cria launcher e desktop entry, configura o Options.ini.

**Opção 2** — pula o download. Usa o zip já extraído em `~/Downloads/sims3_tmp/extracted`.
Útil se o download já foi feito antes ou foi feito manualmente.

**Opção 3** — só reaplica o crack. é um debug, pode ser util se o jogo não abrir para você.

---

## Após instalar

Após concluir a instalação, você pode iniciar o jogo de duas maneiras:

**1. Pelo ícone na área de trabalho**

Basta clicar no atalho do The Sims 3 criado automaticamente durante a instalação.

![The Sims 3](assets/TheSims3.ico)

**2. Pelo terminal**

Caso o diretório `~/.local/bin` ainda não esteja no seu `PATH`, adicione-o com os comandos:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```
---

## Configurações do jogo

Durante a instalação o script pede as preferências de gráficos, resolução e áudio
e aplica direto no `Options.ini` antes do primeiro run. Para reconfigurar depois,
edita o arquivo em:

```
~/Documents/Electronic Arts/The Sims 3/Options.ini
```

---

## Desinstalar

```bash
python uninstall.py
```

Pergunta item por item o que remover — prefixo Wine, launcher, ícone, desktop entry,
pasta temporária de download e saves.

---

## Testado em

| Distro | Wine | GPU | Status |
|---|---|---|---|
| Arch Linux | 11.21 | NVIDIA RTX 2060 TI & RX 9060 XT| ✓ funcionando |
| Ubuntu 25.10 | 10.0 | GTX 1050 TI | ✓ funcionando |

---

## Problemas conhecidos

**Tela escura em fullscreen**  
Troca pra modo janela nas configurações do jogo ou edita `fullscreen = 0` no `Options.ini`.
não tenho interesse em consertar isso.

**Output `fixme:` no terminal ao rodar via Wine**  
Normal. São stubs não implementados do Wine que não afetam o jogo.
Ver [o que significam esses logs](#).

**Xwayland não encontrado em Wayland puro**  
```bash
# Arch
sudo pacman -S xorg-xwayland

# Ubuntu
sudo apt install xwayland
```

---

## Créditos
