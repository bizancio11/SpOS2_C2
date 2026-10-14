#!/usr/bin/env python3
"""SpOS2 - escritorio en pygame (ediciones N / </> Programmer / Premium).
Ejecutar:  python3 main.py [--edition normal|programmer|premium]
Empaquetar: ./build_pyinstaller.sh
"""
import os, sys
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

if len(sys.argv) >= 3 and sys.argv[1] == "--run-script":      # modo "ejecutar script" (IDE / terminal)
    core.run_script_main(sys.argv[2])
    sys.exit(0)

import math, time, random, threading
import pygame

def _edition_file():
    base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
    try:
        with open(os.path.join(base, "edition.txt"), "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


FIXED_EDITION = _edition_file()                     # lo escribe build_pyinstaller.sh junto a cada binario
if "--edition" in sys.argv and sys.argv.index("--edition") + 1 < len(sys.argv):
    FIXED_EDITION = sys.argv[sys.argv.index("--edition") + 1]
if FIXED_EDITION not in core.EDITIONS:
    FIXED_EDITION = None

VERSION = "2.3"
W, H, TB, TH = 1280, 720, 48, 32            # pantalla, barra de tareas, barra de titulo

# ---------------------------------------------------------------- paleta: negro, verde, azul, rojo
GREEN, BLUE, RED = (0, 255, 106), (48, 140, 255), (255, 64, 76)
PAL = {"green": GREEN, "blue": BLUE, "red": RED}
BLACK, PANEL, WIN, RAISED, LINE = (5, 7, 9), (10, 13, 17), (15, 20, 26), (26, 34, 44), (42, 54, 66)
TERM_BG = (8, 11, 14)
TEXT, DIM, LIME = (226, 236, 230), (125, 138, 146), (160, 255, 120)
LBLUE = (130, 190, 255)


class Theme:
    accent = GREEN


T = Theme()


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


# ---------------------------------------------------------------- texto
_fonts, _tc = {}, {}
_FONT_PATH = None


def font(size=15, bold=False):
    global _FONT_PATH
    k = (size, bold)
    if k not in _fonts:
        if _FONT_PATH is None:
            _FONT_PATH = pygame.font.match_font("ubuntumono,dejavusansmono,liberationmono,freemono,couriernew") or ""
        _fonts[k] = pygame.font.Font(_FONT_PATH or None, size + (0 if _FONT_PATH else 2))
        if bold and _FONT_PATH:
            _fonts[k].set_bold(True)
    return _fonts[k]


def txt(s, size=15, color=TEXT, bold=False):
    k = (s, size, color, bold)
    surf = _tc.get(k)
    if surf is None:
        if len(_tc) > 3000:
            _tc.clear()
        surf = _tc[k] = font(size, bold).render(s, True, color)
    return surf


def text_w(s, size=15, bold=False):
    return font(size, bold).size(s)[0]


def draw_text(surf, s, x, y, size=15, color=TEXT, bold=False, anchor="l"):
    if not s:
        return 0
    img = txt(s, size, color, bold)
    w = img.get_width()
    if anchor == "c":
        x -= w // 2
    elif anchor == "r":
        x -= w
    surf.blit(img, (x, y))
    return w


def ellipsize(s, size, maxw, bold=False):
    if text_w(s, size, bold) <= maxw:
        return s
    while len(s) > 1 and text_w(s + "..", size, bold) > maxw:
        s = s[:-1]
    return s + ".."


def rrect(surf, color, rect, r=8, width=0):
    pygame.draw.rect(surf, color, rect, width, border_radius=r)


_sh = {}


def shadow(w, h):
    k = (w, h)
    if k not in _sh:
        sm = pygame.Surface((w // 4 + 10, h // 4 + 10), pygame.SRCALPHA)
        pygame.draw.rect(sm, (0, 0, 0, 170), (5, 5, w // 4, h // 4), border_radius=3)
        _sh[k] = pygame.transform.smoothscale(sm, (w + 40, h + 40))
    return _sh[k]


# ---------------------------------------------------------------- logo
_logo, _logo_cache = None, {}


def load_logo():
    global _logo
    try:
        _logo = pygame.image.load(core.resource_path("logo.png")).convert()
    except Exception:
        _logo = pygame.Surface((400, 400))
        pygame.draw.circle(_logo, GREEN, (200, 200), 150, 6)
        pygame.draw.circle(_logo, GREEN, (200, 200), 80, 3)


def logo_img(h, bright=1.0):
    k = (h, int(bright * 20))
    if k not in _logo_cache:
        if len(_logo_cache) > 80:
            _logo_cache.clear()
        w = int(h * _logo.get_width() / _logo.get_height())
        img = pygame.transform.smoothscale(_logo, (w, h))
        if bright < 1.0:
            b = int(255 * max(0.0, bright))
            img.fill((b, b, b), special_flags=pygame.BLEND_RGB_MULT)
        _logo_cache[k] = img
    return _logo_cache[k]


def blit_logo(surf, h, cx, cy, bright=1.0):          # BLEND_ADD: el fondo negro del logo desaparece
    img = logo_img(h, bright)
    surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2), special_flags=pygame.BLEND_ADD)


def spinner(surf, cx, cy, rad, color, t, width=3):
    a = t * 5.0
    pygame.draw.arc(surf, color, (cx - rad, cy - rad, rad * 2, rad * 2), a, a + 4.2, width)


# ---------------------------------------------------------------- iconos vectoriales
APP_ICON_COLOR = {"terminal": GREEN, "files": BLUE, "music": RED, "wifi": BLUE, "ide": GREEN,
                  "info": GREEN, "settings": BLUE}


def draw_icon(s, kind, cx, cy, sz, c):
    h = sz // 2
    if kind == "terminal":
        rrect(s, c, (cx - h, cy - h + 3, sz, sz - 6), 5, 2)
        pygame.draw.lines(s, c, False, [(cx - h + 6, cy - 4), (cx - h + 12, cy + 1), (cx - h + 6, cy + 6)], 2)
        pygame.draw.line(s, c, (cx - 2, cy + 7), (cx + 7, cy + 7), 2)
    elif kind == "files":
        pygame.draw.rect(s, c, (cx - h, cy - h + 5, h, 7), 2, border_top_left_radius=3, border_top_right_radius=3)
        rrect(s, c, (cx - h, cy - h + 9, sz, sz - 13), 4, 2)
    elif kind == "music":
        pygame.draw.circle(s, c, (cx - 5, cy + 8), 6)
        pygame.draw.line(s, c, (cx + 0, cy + 7), (cx + 0, cy - 10), 3)
        pygame.draw.polygon(s, c, [(cx, cy - 10), (cx + 11, cy - 5), (cx, cy)])
    elif kind == "wifi":
        for i, r in enumerate((16, 10, 4)):
            pygame.draw.arc(s, c, (cx - r, cy + 6 - r, r * 2, r * 2), 0.8, 2.34, 3)
        pygame.draw.circle(s, c, (cx, cy + 8), 2)
    elif kind == "ide":
        draw_text(s, "</>", cx, cy - 10, 20, c, True, "c")
    elif kind == "info":
        pygame.draw.circle(s, c, (cx, cy), h - 2, 2)
        draw_text(s, "i", cx, cy - 10, 20, c, True, "c")
    elif kind == "settings":
        pygame.draw.circle(s, c, (cx, cy), 8, 3)
        for i in range(8):
            a = i * math.pi / 4
            pygame.draw.line(s, c, (cx + math.cos(a) * 10, cy + math.sin(a) * 10),
                             (cx + math.cos(a) * 15, cy + math.sin(a) * 15), 3)


def wifi_bars(s, x, y, sig, color=None, dim=LINE):
    n = 4 if sig >= 75 else 3 if sig >= 50 else 2 if sig >= 25 else 1 if sig > 0 else 0
    col = color or (GREEN if sig > 60 else BLUE if sig > 35 else RED)
    for i in range(4):
        hh = 5 + i * 4
        pygame.draw.rect(s, col if i < n else dim, (x + i * 6, y + 18 - hh, 4, hh), border_radius=1)


# ---------------------------------------------------------------- widgets
class TextInput:
    def __init__(self, placeholder="", password=False, maxlen=32):
        self.text, self.ph, self.pw, self.maxlen = "", placeholder, password, maxlen

    def key(self, e):
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return "enter"
        if e.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif e.unicode and e.unicode.isprintable() and len(self.text) < self.maxlen:
            self.text += e.unicode
        return None

    def draw(self, s, rect, focused):
        rect = pygame.Rect(rect)
        rrect(s, RAISED, rect, 7)
        rrect(s, T.accent if focused else LINE, rect, 7, 2 if focused else 1)
        shown = ("*" * len(self.text)) if self.pw else self.text
        if shown:
            shown = shown[-((rect.w - 24) // max(1, text_w("M"))):]
            w = draw_text(s, shown, rect.x + 12, rect.y + (rect.h - 18) // 2)
        else:
            w = 0
            draw_text(s, self.ph, rect.x + 12, rect.y + (rect.h - 18) // 2, 15, DIM)
        if focused and int(time.time() * 2) % 2 == 0:
            pygame.draw.rect(s, T.accent, (rect.x + 13 + w, rect.y + 8, 2, rect.h - 16))


class App:
    title, size, kind, single = "App", (640, 420), "info", False

    def __init__(self, sysm, desk):
        self.s, self.desk, self.hits = sysm, desk, []

    def window_title(self):
        return self.title

    def begin(self):
        self.hits = []

    def add(self, rect, ident):
        self.hits.append((pygame.Rect(rect), ident))

    def hit(self, pos):
        for rect, ident in reversed(self.hits):
            if rect.collidepoint(pos):
                return ident
        return None

    def button(self, surf, rect, label, ident, color=None, enabled=True, size=14):
        rect = pygame.Rect(rect)
        over = enabled and rect.collidepoint(pygame.mouse.get_pos())
        base = color or T.accent
        if enabled:
            rrect(surf, mix(RAISED, base, 0.35 if over else 0.16), rect, 7)
            rrect(surf, base, rect, 7, 1)
        else:
            rrect(surf, RAISED, rect, 7)
        draw_text(surf, label, rect.centerx, rect.centery - size // 2 - 2, size, TEXT if enabled else DIM, False, "c")
        if enabled:
            self.add(rect, ident)

    def draw(self, s, r): pass
    def event(self, e, r): pass
    def update(self, dt): pass
    def on_close(self): pass


# ================================================================ reproductor de musica
class Player:
    def __init__(self, sysm):
        self.s = sysm
        self.tracks, self.idx, self.state = [], -1, "stop"
        self.shuffle, self.repeat = False, "all"
        self.offset, self.started = 0.0, 0.0
        self.audio = pygame.mixer.get_init() is not None
        self.volume = float(sysm.cfg.get("volume", 0.7))
        if self.audio:
            pygame.mixer.music.set_volume(self.volume)
        for key in ("ode", "theme"):
            if sysm.assets.get(key):
                self.add(sysm.assets[key], save=False)
        for p in sysm.cfg.get("playlist", []):
            if os.path.isfile(p):
                self.add(p, save=False)

    # ---- lista
    def title_of(self, path):
        for k, p in self.s.assets.items():
            if p == path and k in core.TITLES:
                return core.TITLES[k]
        return os.path.splitext(os.path.basename(path))[0]

    def add(self, path, play=False, save=True):
        path = os.path.abspath(path)
        if not path.lower().endswith(core.MUSIC_EXT) or not os.path.isfile(path):
            return -1
        for i, t in enumerate(self.tracks):
            if t["path"] == path:
                if play:
                    self.play(i)
                return i
        tr = {"path": path, "title": self.title_of(path), "len": 0.0}
        self.tracks.append(tr)
        threading.Thread(target=self._measure, args=(tr,), daemon=True).start()
        if save:
            self.save()
        if play:
            self.play(len(self.tracks) - 1)
        return len(self.tracks) - 1

    def add_folder(self, folder, limit=300):
        n = 0
        for root, dirs, files in os.walk(folder):
            if root[len(folder):].count(os.sep) >= 2:
                dirs[:] = []
            for f in sorted(files):
                if f.lower().endswith(core.MUSIC_EXT) and n < limit:
                    if self.add(os.path.join(root, f), save=False) >= 0:
                        n += 1
        self.save()
        return n

    def clear(self):
        self.stop()
        self.tracks, self.idx = [], -1
        self.save()

    def save(self):
        self.s.cfg["playlist"] = [t["path"] for t in self.tracks if not t["path"].startswith(core.CACHE)]
        core.save_config(self.s.cfg)

    @staticmethod
    def _measure(tr):
        n = 0.0
        try:
            from mutagen import File as MFile
            n = float(MFile(tr["path"]).info.length)
        except Exception:
            try:
                if os.path.getsize(tr["path"]) < 40e6:
                    n = float(pygame.mixer.Sound(tr["path"]).get_length())
            except Exception:
                n = 0.0
        tr["len"] = n

    # ---- control
    def play(self, i):
        if not self.tracks:
            return
        if not self.audio:
            self.s.toast("Sin dispositivo de audio", RED)
            return
        i %= len(self.tracks)
        try:
            pygame.mixer.music.load(self.tracks[i]["path"])
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
        except pygame.error as e:
            self.s.toast("No se pudo reproducir: %s" % str(e)[:50], RED)
            self.state = "stop"
            return
        self.idx, self.state, self.offset, self.started = i, "play", 0.0, time.time()

    def toggle(self):
        if self.state == "play":
            pygame.mixer.music.pause()
            self.state = "pause"
        elif self.state == "pause":
            pygame.mixer.music.unpause()
            self.state = "play"
        else:
            self.play(max(0, self.idx))

    def stop(self):
        if self.audio:
            pygame.mixer.music.stop()
        self.state = "stop"

    def next(self, auto=False):
        if not self.tracks:
            return
        if auto and self.repeat == "one":
            return self.play(self.idx)
        if self.shuffle and len(self.tracks) > 1:
            n = self.idx
            while n == self.idx:
                n = random.randrange(len(self.tracks))
            return self.play(n)
        n = self.idx + 1
        if n >= len(self.tracks):
            if auto and self.repeat == "off":
                return self.stop()
            n = 0
        self.play(n)

    def prev(self):
        if self.tracks:
            if self.pos() > 3:
                return self.play(self.idx)
            self.play(self.idx - 1)

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, v))
        if self.audio:
            pygame.mixer.music.set_volume(self.volume)

    def current(self):
        return self.tracks[self.idx] if 0 <= self.idx < len(self.tracks) else None

    def pos(self):
        if self.state == "stop" or not self.audio:
            return 0.0
        return self.offset + max(0, pygame.mixer.music.get_pos()) / 1000.0

    def seek(self, frac):
        tr = self.current()
        if not tr or not tr["len"] or self.state == "stop":
            return
        sec = max(0.0, min(tr["len"] - 0.5, frac * tr["len"]))
        try:
            pygame.mixer.music.set_pos(sec)
            self.offset = sec - max(0, pygame.mixer.music.get_pos()) / 1000.0
        except pygame.error:
            self.s.toast("Este formato no permite adelantar", BLUE)

    def update(self):
        if self.state == "play" and self.audio and not pygame.mixer.music.get_busy() \
                and time.time() - self.started > 0.7:
            self.next(auto=True)


# ================================================================ Terminal
class TerminalApp(App):
    title, size, kind = "Terminal", (740, 450), "terminal"

    def __init__(self, sysm, desk):
        super().__init__(sysm, desk)
        self.cwd, self.lines, self.input = sysm.home, [], ""
        self.hist, self.hpos, self.scroll = [], 0, 0
        self.mode, self.repl, self.more, self.runner = "shell", None, False, None
        self.out("SpOS2 Shell v%s - edicion %s" % (VERSION, sysm.ed["name"]), T.accent)
        self.out("Escribe 'help' para ver los comandos.\n", DIM)

    # ---- salida
    def out(self, t, color=TEXT):
        for ln in str(t).split("\n"):
            self.lines.append((ln, color))
        if len(self.lines) > 1500:
            del self.lines[:300]
        self.scroll = 0

    def short(self, p):
        h = self.s.home
        return "~" + p[len(h):] if p == h or p.startswith(h + os.sep) else p

    def prompt_parts(self):
        if self.mode == "python":
            return [("... " if self.more else ">>> ", LIME)]
        return [(self.s.user + "@SpOS2", T.accent), (":", DIM), (self.short(self.cwd), LBLUE), ("$ ", TEXT)]

    def rp(self, p):
        return os.path.normpath(os.path.join(self.cwd, os.path.expanduser(p)))

    # ---- entrada
    def visual(self, cols, need):
        res = []
        for t, c in reversed(self.lines):
            chunks = [t[i:i + cols] for i in range(0, max(len(t), 1), cols)]
            res.extend((ch, c) for ch in reversed(chunks))
            if len(res) >= need:
                break
        res.reverse()
        return res

    def event(self, e, r):
        if e.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(3000, self.scroll + e.y * 3))
            return
        if e.type != pygame.KEYDOWN:
            return
        if e.mod & pygame.KMOD_CTRL:
            if e.key == pygame.K_c:
                self.interrupt()
            elif e.key == pygame.K_l:
                self.lines = []
            return
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.submit()
        elif e.key == pygame.K_BACKSPACE:
            self.input = self.input[:-1]
        elif e.key == pygame.K_UP and self.hist:
            self.hpos = max(0, self.hpos - 1)
            self.input = self.hist[self.hpos]
        elif e.key == pygame.K_DOWN:
            self.hpos = min(len(self.hist), self.hpos + 1)
            self.input = self.hist[self.hpos] if self.hpos < len(self.hist) else ""
        elif e.key == pygame.K_PAGEUP:
            self.scroll += 10
        elif e.key == pygame.K_PAGEDOWN:
            self.scroll = max(0, self.scroll - 10)
        elif e.key == pygame.K_TAB:
            self.complete()
        elif e.unicode and e.unicode.isprintable() and len(self.input) < 200:
            self.input += e.unicode
            self.scroll = 0

    def interrupt(self):
        if self.runner:
            self.runner.stop()
            self.out("^C", RED)
        elif self.mode == "python":
            self.mode, self.repl, self.input = "shell", None, ""
            self.out("^C - consola Python cerrada", BLUE)
        else:
            self.out("^C", DIM)
            self.input = ""

    def complete(self):
        head, _, tok = self.input.rpartition(" ")
        d, b = os.path.split(tok)
        base = self.rp(d) if d else self.cwd
        names = [n + ("/" if isd else "") for n, isd, _ in (core.list_dir(base) or []) if n.startswith(b)]
        if not names:
            return
        pre = os.path.commonprefix(names)
        self.input = (head + " " if head or self.input.endswith(" ") else "") + (d + "/" if d else "") + pre

    def submit(self):
        line, self.input = self.input, ""
        if self.runner:
            return
        if self.mode == "python":
            if line.strip() in ("exit()", "exit", "quit()", "quit"):
                self.mode, self.repl = "shell", None
                return
            self.out(("... " if self.more else ">>> ") + line, LIME)
            res, self.more = self.repl.push(line)
            if res:
                self.out(res.rstrip("\n"), RED if "Traceback" in res else TEXT)
            return
        parts = line.split()
        shown = line
        if len(parts) >= 4 and parts[0] == "wifi" and parts[1] == "connect":
            shown = " ".join(parts[:3]) + " ****"
        self.out("%s@SpOS2:%s$ %s" % (self.s.user, self.short(self.cwd), shown), TEXT)
        if not line.strip():
            return
        if shown == line and (not self.hist or self.hist[-1] != line):
            self.hist.append(line)
        self.hpos = len(self.hist)
        import shlex
        try:
            args = shlex.split(line)
        except ValueError:
            args = line.split()
        fn = getattr(self, "cmd_" + args[0].replace("-", "_"), None) if args[0].isidentifier() else None
        if fn is None:
            self.out("%s: comando no encontrado (prueba 'help')" % args[0], RED)
        else:
            try:
                fn(args[1:])
            except Exception as ex:
                self.out("error: %s" % ex, RED)

    # ---- comandos
    def need(self, feat):
        if self.s.feature(feat):
            return True
        self.out("Disponible solo en las ediciones </> Programmer y Premium", RED)
        return False

    def cmd_help(self, a):
        self.out("Archivos : ls cd pwd cat mkdir touch open", LIME)
        self.out("Sistema  : clear date whoami neofetch edition uname", LIME)
        self.out("Musica   : play [archivo] pause stop next prev vol N playlist music", LIME)
        self.out("Red      : wifi [scan | connect SSID [clave]]", LIME)
        if self.s.feature("python"):
            self.out("Python   : python | py archivo.py | edit archivo.py", LBLUE)
        if self.s.feature("themes"):
            self.out("Premium  : theme green|blue|red", RED)
        self.out("Sesion   : logout reboot shutdown exit    (Tab completa, Ctrl+C corta)", LIME)

    def cmd_ls(self, a):
        p = self.rp(a[0]) if a else self.cwd
        ents = core.list_dir(p)
        if ents is None:
            return self.out("ls: no se puede abrir '%s'" % p, RED)
        for n, isd, size in ents[:80]:
            c = BLUE if isd else RED if n.lower().endswith(core.MUSIC_EXT) else GREEN if n.endswith(".py") else TEXT
            self.out(n + ("/" if isd else "   " + core.human_size(size)), c)
        if len(ents) > 80:
            self.out("... %d mas" % (len(ents) - 80), DIM)
        if not ents:
            self.out("(vacio)", DIM)

    def cmd_cd(self, a):
        p = self.rp(a[0]) if a else self.s.home
        if os.path.isdir(p):
            self.cwd = p
        else:
            self.out("cd: no existe '%s'" % (a[0] if a else p), RED)

    def cmd_pwd(self, a):
        self.out(self.cwd)

    def cmd_cat(self, a):
        if not a:
            return self.out("uso: cat archivo", DIM)
        p = self.rp(a[0])
        if not os.path.isfile(p) or os.path.getsize(p) > 65536:
            return self.out("cat: archivo inexistente o muy grande", RED)
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for i, ln in enumerate(f):
                if i >= 120:
                    self.out("...", DIM)
                    break
                self.out(ln.rstrip("\n"))

    def cmd_mkdir(self, a):
        for n in a:
            os.makedirs(self.rp(n), exist_ok=True)

    def cmd_touch(self, a):
        for n in a:
            open(self.rp(n), "a").close()

    def cmd_echo(self, a):
        self.out(" ".join(a))

    def cmd_clear(self, a):
        self.lines = []

    def cmd_date(self, a):
        self.out(time.strftime("%a %d %b %Y  %H:%M:%S"))

    def cmd_whoami(self, a):
        self.out(self.s.user)

    def cmd_uname(self, a):
        self.out("SpOS2 %s (%s) Python %s" % (VERSION, self.s.ed["name"], sys.version.split()[0]))

    def cmd_edition(self, a):
        ed = self.s.ed
        self.out("Edicion: %s  [%s]" % (ed["name"], ed["tag"]), PAL[ed["color"]])
        self.out(ed["blurb"], DIM)

    def cmd_neofetch(self, a):
        art = ["      .  *  .  o  .      ", "   *   .-''''''-.   *   ", "  .   /  .-''''-.  \\  .  ",
               "  o  |  /  (  )  \\  |  o ", "  .   \\  '-....-'  /  .  ", "   *   '-.______.-'   *   "]
        for i, ln in enumerate(art):
            self.out(ln, (GREEN, BLUE, RED)[i % 3])
        net = "demo" if self.s.wifi.demo else (self.s.wifi.current or "sin conexion")
        for k, v in (("OS", "SpOS2 %s %s" % (VERSION, self.s.ed["name"])), ("Usuario", self.s.user),
                     ("Python", sys.version.split()[0]), ("Pantalla", "%dx%d" % (W, H)),
                     ("Audio", "SDL_mixer" if self.s.player.audio else "no disponible"), ("WiFi", net)):
            self.out("%-8s %s" % (k + ":", v))

    def cmd_open(self, a):
        if a:
            self.desk.open_file(self.rp(a[0]))

    def cmd_files(self, a):
        self.desk.open("files")

    def cmd_music(self, a):
        self.desk.open("music")

    def cmd_settings(self, a):
        self.desk.open("settings")

    def cmd_play(self, a):
        pl = self.s.player
        if a:
            i = pl.add(self.rp(a[0]), play=True)
            if i < 0:
                self.out("play: formato no valido (mp3, ogg, wav, flac)", RED)
        else:
            pl.toggle() if pl.state != "play" else None
        c = pl.current()
        if c and pl.state == "play":
            self.out("Reproduciendo: " + c["title"], RED)

    def cmd_pause(self, a):
        self.s.player.toggle()

    def cmd_stop(self, a):
        self.s.player.stop()

    def cmd_next(self, a):
        self.s.player.next()

    def cmd_prev(self, a):
        self.s.player.prev()

    def cmd_vol(self, a):
        if a and a[0].isdigit():
            self.s.player.set_volume(int(a[0]) / 100.0)
        self.out("Volumen: %d%%" % round(self.s.player.volume * 100))

    def cmd_playlist(self, a):
        pl = self.s.player
        for i, t in enumerate(pl.tracks):
            self.out("%s %2d. %s" % (">" if i == pl.idx else " ", i + 1, t["title"]), RED if i == pl.idx else TEXT)
        if not pl.tracks:
            self.out("(lista vacia)", DIM)

    def cmd_wifi(self, a):
        w = self.s.wifi
        if a and a[0] == "scan":
            w.refresh()
            return self.out("Buscando redes...", BLUE)
        if a and a[0] == "connect" and len(a) >= 2:
            w.connect(a[1], a[2] if len(a) > 2 else None)
            return self.out("Conectando a %s..." % a[1], BLUE)
        self.out("Modo: " + ("demostracion (sin WiFi real)" if w.demo else "NetworkManager"), BLUE)
        self.out("Conectado a: %s" % (w.current or "ninguna red"), GREEN if w.current else RED)
        for n, sig, sec in w.networks[:12]:
            self.out("  %-22s %3d%%  %s" % (n[:22], sig, sec or "abierta"), TEXT)
        if w.message:
            self.out(w.message, GREEN if w.ok else RED)

    def cmd_python(self, a):
        if not self.need("python"):
            return
        self.mode, self.repl, self.more = "python", core.PyRepl(), False
        self.out("Python %s (SpOS2)  -  exit() para volver" % sys.version.split()[0], BLUE)

    def cmd_py(self, a):
        if not self.need("python"):
            return
        if not a:
            return self.cmd_python(a)
        p = self.rp(a[0])
        if not os.path.isfile(p):
            return self.out("py: no existe '%s'" % a[0], RED)
        self.runner = core.ScriptRunner(p)
        self.runner.start()

    def cmd_edit(self, a):
        if self.need("ide"):
            self.desk.open("ide", path=self.rp(a[0]) if a else None)

    def cmd_ide(self, a):
        self.cmd_edit(a)

    def cmd_theme(self, a):
        if not self.s.feature("themes"):
            return self.out("Los temas son exclusivos de la edicion Premium", RED)
        if a and a[0] in PAL:
            self.s.set_accent(a[0])
        else:
            self.out("uso: theme green|blue|red", DIM)

    def cmd_logout(self, a):
        self.s.goto("login")

    def cmd_reboot(self, a):
        self.s.goto("boot")

    def cmd_shutdown(self, a):
        self.s.quit = True

    def cmd_exit(self, a):
        self.desk.close_app(self)

    # ---- bucle
    def update(self, dt):
        if self.runner:
            for ln in self.runner.drain():
                self.out(ln, TEXT)
            if self.runner.finished and self.runner.q.empty():
                rc = self.runner.returncode
                self.out("[proceso terminado, codigo %s]" % rc, GREEN if rc == 0 else RED)
                self.runner = None

    def draw(self, s, r):
        s.fill(TERM_BG, r)
        f = font(15)
        cw, lh = f.size("M")[0], f.get_linesize() + 1
        cols, rows = max(8, (r.w - 24) // cw), max(2, (r.h - 16) // lh)
        vl = self.visual(cols, rows - 1 + self.scroll)
        if len(vl) < rows - 1 + self.scroll:
            self.scroll = max(0, len(vl) - (rows - 1))
        shown = (vl[:len(vl) - self.scroll] if self.scroll else vl)[-(rows - 1):]
        y = r.y + 8
        for t, c in shown:
            draw_text(s, t, r.x + 12, y, 15, c)
            y += lh
        if self.scroll:
            draw_text(s, "[historial - PgDn para volver]", r.right - 10, r.y + 4, 13, DIM, False, "r")
            return
        x = r.x + 12
        if self.runner:
            draw_text(s, "(ejecutando... Ctrl+C para detener)", x, y, 15, DIM)
            return
        plen = 0
        for t, c in self.prompt_parts():
            x += draw_text(s, t, x, y, 15, c)
            plen += len(t)
        shown_in = self.input[-max(1, cols - plen - 1):]
        x += draw_text(s, shown_in, x, y, 15, TEXT)
        if int(time.time() * 2) % 2 == 0:
            pygame.draw.rect(s, T.accent, (x + 1, y + 2, cw - 2, lh - 3))


# ================================================================ Archivos
class FilesApp(App):
    title, size, kind = "Archivos", (700, 450), "files"
    ROW = 28

    def __init__(self, sysm, desk):
        super().__init__(sysm, desk)
        self.path, self.scroll, self.entries = sysm.home, 0, []
        self.go(self.path)

    def go(self, path):
        ents = core.list_dir(path)
        if ents is None:
            return self.s.toast("No se puede abrir la carpeta", RED)
        self.path, self.entries, self.scroll = path, ents, 0

    def places(self):
        h = self.s.home
        pl = [("Inicio", h), ("Musica", h + "/Musica"), ("Proyectos", h + "/Proyectos"), ("Documentos", h + "/Documentos")]
        m = os.path.expanduser("~/Music")
        if os.path.isdir(m):
            pl.append(("~/Music", m))
        pl.append(("Raiz /", "/"))
        return pl

    def event(self, e, r):
        if e.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - e.y * 2)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            i = self.hit(e.pos)
            if i is None:
                return
            if i[0] == "go":
                self.go(i[1])
            elif i[0] == "up":
                self.go(os.path.dirname(self.path.rstrip("/")) or "/")
            elif i[0] == "row":
                n, isd, _ = self.entries[i[1]]
                p = os.path.join(self.path, n)
                self.go(p) if isd else self.desk.open_file(p)

    def draw(self, s, r):
        self.begin()
        mouse = pygame.mouse.get_pos()
        s.fill(WIN, r)
        s.fill(PANEL, (r.x, r.y, 140, r.h))
        y = r.y + 12
        for label, path in self.places():
            rect = pygame.Rect(r.x + 8, y, 124, 28)
            if rect.collidepoint(mouse) or path == self.path:
                rrect(s, mix(RAISED, T.accent, 0.18 if path == self.path else 0.0), rect, 6)
            draw_text(s, label, rect.x + 10, rect.y + 5, 14, T.accent if path == self.path else TEXT)
            self.add(rect, ("go", path))
            y += 32
        x0 = r.x + 140
        s.fill(PANEL, (x0, r.y, r.w - 140, 38))
        self.button(s, (x0 + 8, r.y + 6, 34, 26), "<", ("up",), BLUE)
        draw_text(s, ellipsize(self.path, 14, r.w - 140 - 70), x0 + 54, r.y + 10, 14, LBLUE)
        top, area = r.y + 42, r.h - 42 - 24
        vis = max(1, area // self.ROW)
        self.scroll = max(0, min(self.scroll, max(0, len(self.entries) - vis)))
        old = s.get_clip()
        s.set_clip(pygame.Rect(x0, top, r.w - 140, area))
        for k in range(vis + 1):
            i = self.scroll + k
            if i >= len(self.entries):
                break
            n, isd, size = self.entries[i]
            rect = pygame.Rect(x0 + 6, top + k * self.ROW, r.w - 140 - 12, self.ROW - 2)
            if rect.collidepoint(mouse):
                rrect(s, RAISED, rect, 6)
            low = n.lower()
            col = BLUE if isd else RED if low.endswith(core.MUSIC_EXT) else GREEN if low.endswith(".py") else DIM
            rrect(s, col, (rect.x + 6, rect.y + 5, 16, 16), 4, 0 if isd else 2)
            draw_text(s, ellipsize(n + ("/" if isd else ""), 14, rect.w - 150), rect.x + 32, rect.y + 5, 14, TEXT)
            if not isd:
                draw_text(s, core.human_size(size), rect.right - 10, rect.y + 5, 13, DIM, False, "r")
            self.add(rect, ("row", i))
        s.set_clip(old)
        if not self.entries:
            draw_text(s, "(carpeta vacia)", x0 + 20, top + 10, 14, DIM)
        draw_text(s, "%d elementos  -  clic en .mp3 para reproducir, .py para editar" % len(self.entries),
                  x0 + 10, r.bottom - 20, 12, DIM)


# ================================================================ Musica
class MusicApp(App):
    title, size, kind, single = "Reproductor de musica", (790, 500), "music", True
    LW, ROW = 300, 30

    def __init__(self, sysm, desk):
        super().__init__(sysm, desk)
        self.scroll, self.drag, self.seek_frac = 0, None, 0.0
        self.seek_rect = self.vol_rect = pygame.Rect(0, 0, 1, 1)
        self.bars, self.t = [0.0] * 36, 0.0

    def event(self, e, r):
        pl = self.s.player
        if e.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - e.y * 2)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            i = self.hit(e.pos)
            if i is None:
                return
            if i == "play":
                pl.toggle()
            elif i == "prev":
                pl.prev()
            elif i == "next":
                pl.next()
            elif i == "shuffle":
                pl.shuffle = not pl.shuffle
            elif i == "repeat":
                pl.repeat = {"all": "one", "one": "off", "off": "all"}[pl.repeat]
            elif i == "folder":
                n = 0
                for d in (os.path.join(self.s.home, "Musica"), os.path.expanduser("~/Music")):
                    if os.path.isdir(d):
                        n += pl.add_folder(d)
                self.s.toast("%d canciones agregadas" % n, GREEN if n else BLUE)
            elif i == "files":
                self.desk.open("files")
            elif i == "builtin":
                for k in ("ode", "theme"):
                    if self.s.assets.get(k):
                        pl.add(self.s.assets[k])
            elif i == "clear":
                pl.clear()
            elif i in ("seek", "vol"):
                self.drag = i
                if i == "vol":
                    pl.set_volume((e.pos[0] - self.vol_rect.x) / self.vol_rect.w)
                else:
                    self.seek_frac = (e.pos[0] - self.seek_rect.x) / self.seek_rect.w
            elif isinstance(i, tuple) and i[0] == "row":
                pl.play(i[1])

    def update(self, dt):
        self.t += dt
        pl = self.s.player
        if self.drag:
            mx = pygame.mouse.get_pos()[0]
            if pygame.mouse.get_pressed()[0]:
                if self.drag == "vol":
                    pl.set_volume((mx - self.vol_rect.x) / self.vol_rect.w)
                else:
                    self.seek_frac = max(0.0, min(1.0, (mx - self.seek_rect.x) / self.seek_rect.w))
            else:
                if self.drag == "seek":
                    pl.seek(self.seek_frac)
                else:
                    self.s.cfg["volume"] = pl.volume
                    core.save_config(self.s.cfg)
                self.drag = None
        play = pl.state == "play"
        for i in range(len(self.bars)):
            tgt = (0.2 + 0.8 * abs(math.sin(self.t * 2.7 + i * 0.55) * math.cos(self.t * 1.3 + i * 0.21))) if play else 0.04
            self.bars[i] += (tgt - self.bars[i]) * min(1.0, dt * 10)

    def draw(self, s, r):
        self.begin()
        pl, acc = self.s.player, T.accent
        s.fill(WIN, r)
        s.fill(PANEL, (r.x, r.y, self.LW, r.h))
        cx = r.x + self.LW // 2
        play = pl.state == "play"
        blit_logo(s, 130, cx, r.y + 105, 0.9)
        a = self.t * (1.4 if play else 0.0)
        for rad, col, off in ((82, GREEN, 0.0), (90, BLUE, 2.1), (98, RED, 4.2)):
            pygame.draw.arc(s, col, (cx - rad, r.y + 105 - rad, rad * 2, rad * 2), a * (rad / 82.0) + off, a * (rad / 82.0) + off + 1.7, 3)
        tr = pl.current()
        title = tr["title"] if tr else ("Sin pista" if not pl.tracks else "Pulsa play")
        draw_text(s, ellipsize(title, 16, self.LW - 30, True), cx, r.y + 214, 16, TEXT, True, "c")
        sub = "%d / %d" % (pl.idx + 1, len(pl.tracks)) if tr else "%d pistas" % len(pl.tracks)
        draw_text(s, sub + ("   (sin audio)" if not pl.audio else ""), cx, r.y + 238, 12, DIM if pl.audio else RED, False, "c")
        # progreso
        self.seek_rect = pygame.Rect(r.x + 24, r.y + 270, self.LW - 48, 8)
        ln = tr["len"] if tr else 0.0
        frac = self.seek_frac if self.drag == "seek" else (pl.pos() / ln if ln else 0.0)
        frac = max(0.0, min(1.0, frac))
        rrect(s, LINE, self.seek_rect, 4)
        if frac > 0:
            rrect(s, acc, (self.seek_rect.x, self.seek_rect.y, max(8, int(self.seek_rect.w * frac)), 8), 4)
            pygame.draw.circle(s, TEXT, (self.seek_rect.x + int(self.seek_rect.w * frac), self.seek_rect.centery), 7)
        self.add(self.seek_rect.inflate(0, 22), "seek")
        draw_text(s, core.fmt_time(frac * ln if self.drag == "seek" else pl.pos()), self.seek_rect.x, r.y + 286, 12, DIM)
        draw_text(s, core.fmt_time(ln) if ln else "--:--", self.seek_rect.right, r.y + 286, 12, DIM, False, "r")
        # controles
        y = r.y + 328
        for x, ident, lab, on in ((r.x + 40, "shuffle", "mix", pl.shuffle),
                                  (r.x + 260, "repeat", {"all": "rep", "one": "rep1", "off": "rep-"}[pl.repeat], pl.repeat != "off")):
            rect = pygame.Rect(0, 0, 42, 26)
            rect.center = (x, y)
            rrect(s, mix(RAISED, BLUE, 0.4) if on else RAISED, rect, 6)
            draw_text(s, lab, rect.centerx, rect.y + 5, 12, TEXT if on else DIM, False, "c")
            self.add(rect, ident)
        for x, ident in ((r.x + 100, "prev"), (r.x + 200, "next")):
            over = pygame.Rect(x - 20, y - 16, 40, 32).collidepoint(pygame.mouse.get_pos())
            c = TEXT if over else LBLUE
            if ident == "prev":
                pygame.draw.rect(s, c, (x - 10, y - 8, 3, 16))
                pygame.draw.polygon(s, c, [(x + 10, y - 8), (x + 10, y + 8), (x - 5, y)])
            else:
                pygame.draw.rect(s, c, (x + 7, y - 8, 3, 16))
                pygame.draw.polygon(s, c, [(x - 10, y - 8), (x - 10, y + 8), (x + 5, y)])
            self.add((x - 20, y - 16, 40, 32), ident)
        pygame.draw.circle(s, acc, (cx, y), 25)
        if play:
            pygame.draw.rect(s, BLACK, (cx - 9, y - 10, 6, 20))
            pygame.draw.rect(s, BLACK, (cx + 3, y - 10, 6, 20))
        else:
            pygame.draw.polygon(s, BLACK, [(cx - 8, y - 11), (cx - 8, y + 11), (cx + 12, y)])
        self.add((cx - 25, y - 25, 50, 50), "play")
        # volumen
        self.vol_rect = pygame.Rect(r.x + 64, r.y + 380, self.LW - 128, 6)
        draw_text(s, "Vol", r.x + 24, r.y + 372, 13, DIM)
        rrect(s, LINE, self.vol_rect, 3)
        rrect(s, BLUE, (self.vol_rect.x, self.vol_rect.y, max(6, int(self.vol_rect.w * pl.volume)), 6), 3)
        pygame.draw.circle(s, TEXT, (self.vol_rect.x + int(self.vol_rect.w * pl.volume), self.vol_rect.centery), 6)
        draw_text(s, "%d%%" % round(pl.volume * 100), self.vol_rect.right + 12, r.y + 372, 13, DIM)
        self.add(self.vol_rect.inflate(0, 20), "vol")
        # visualizador (Premium)
        vr = pygame.Rect(r.x + 24, r.y + 400, self.LW - 48, 44)
        if self.s.feature("visualizer"):
            bw = vr.w / len(self.bars)
            for i, b in enumerate(self.bars):
                h = max(2, int(b * vr.h))
                col = mix(GREEN, BLUE, b * 1.7) if b < 0.6 else mix(BLUE, RED, (b - 0.6) / 0.4)
                pygame.draw.rect(s, col, (vr.x + i * bw, vr.bottom - h, max(2, bw - 2), h))
        else:
            draw_text(s, "Visualizador: edicion Premium", cx, vr.y + 14, 12, DIM, False, "c")
        self.button(s, (r.x + 24, r.bottom - 36, 118, 26), "+ Carpeta Musica", "folder", BLUE, True, 12)
        self.button(s, (r.x + 150, r.bottom - 36, 126, 26), "Abrir Archivos", "files", BLUE, True, 12)
        # lista
        x0, rw = r.x + self.LW, r.w - self.LW
        draw_text(s, "Lista de reproduccion (%d)" % len(pl.tracks), x0 + 16, r.y + 14, 15, TEXT, True)
        self.button(s, (x0 + rw - 96, r.y + 10, 84, 26), "Limpiar", "clear", RED, True, 12)
        self.button(s, (x0 + rw - 236, r.y + 10, 132, 26), "+ Sonidos SpOS2", "builtin", GREEN, True, 12)
        top, area = r.y + 48, r.h - 48 - 8
        vis = max(1, area // self.ROW)
        self.scroll = max(0, min(self.scroll, max(0, len(pl.tracks) - vis)))
        old = s.get_clip()
        s.set_clip(pygame.Rect(x0, top, rw, area))
        mouse = pygame.mouse.get_pos()
        for k in range(vis + 1):
            i = self.scroll + k
            if i >= len(pl.tracks):
                break
            t = pl.tracks[i]
            rect = pygame.Rect(x0 + 8, top + k * self.ROW, rw - 16, self.ROW - 2)
            cur = i == pl.idx
            if cur:
                rrect(s, mix(RAISED, RED, 0.25), rect, 6)
            elif rect.collidepoint(mouse):
                rrect(s, RAISED, rect, 6)
            draw_text(s, ">" if cur and play else str(i + 1), rect.x + 8, rect.y + 6, 13, RED if cur else DIM)
            draw_text(s, ellipsize(t["title"], 14, rect.w - 110), rect.x + 40, rect.y + 6, 14, TEXT if cur else LIME if cur else TEXT)
            draw_text(s, core.fmt_time(t["len"]) if t["len"] else "--:--", rect.right - 8, rect.y + 6, 13, DIM, False, "r")
            self.add(rect, ("row", i))
        s.set_clip(old)
        if not pl.tracks:
            draw_text(s, "Arrastra archivos .mp3 a esta ventana,", x0 + rw // 2, top + 40, 14, DIM, False, "c")
            draw_text(s, "o usa Archivos / el comando 'play'.", x0 + rw // 2, top + 62, 14, DIM, False, "c")


# ================================================================ WiFi
class WifiApp(App):
    title, size, kind, single = "Redes WiFi", (480, 540), "wifi", True

    def __init__(self, sysm, desk):
        super().__init__(sysm, desk)
        self.pw, self.ask, self.scroll = TextInput("Clave de la red", True, 63), None, 0
        self.s.wifi.refresh()

    def connect_to(self, ssid, sec):
        if sec:
            self.ask, self.pw.text = ssid, ""
        else:
            self.s.wifi.connect(ssid)

    def event(self, e, r):
        w = self.s.wifi
        if self.ask:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.ask = None
                elif self.pw.key(e) == "enter" and self.pw.text:
                    w.connect(self.ask, self.pw.text)
                    self.ask = None
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                i = self.hit(e.pos)
                if i == "ok" and self.pw.text:
                    w.connect(self.ask, self.pw.text)
                    self.ask = None
                elif i == "cancel":
                    self.ask = None
            return
        if e.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - e.y)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            i = self.hit(e.pos)
            if i == "scan":
                w.refresh()
            elif i == "disc":
                w.disconnect()
            elif isinstance(i, tuple) and i[0] == "net" and not w.busy:
                ssid, sig, sec = w.networks[i[1]]
                if ssid != w.current:
                    self.connect_to(ssid, sec)

    def draw(self, s, r):
        self.begin()
        w, t = self.s.wifi, time.time()
        s.fill(WIN, r)
        card = pygame.Rect(r.x + 12, r.y + 12, r.w - 24, 70)
        rrect(s, PANEL, card, 10)
        rrect(s, GREEN if w.current else RED, card, 10, 1)
        draw_text(s, "Conectado: " + w.current if w.current else "Sin conexion", card.x + 16, card.y + 12, 16,
                  GREEN if w.current else RED, True)
        draw_text(s, "Modo demostracion (clave valida: 8+ caracteres)" if w.demo else "NetworkManager (nmcli)",
                  card.x + 16, card.y + 40, 12, BLUE)
        self.button(s, (card.right - 218, card.y + 20, 100, 28), "Actualizar", "scan", BLUE, not w.busy, 13)
        self.button(s, (card.right - 110, card.y + 20, 98, 28), "Desconectar", "disc", RED, bool(w.current) and not w.busy, 12)
        top, rowh = r.y + 96, 46
        area = r.h - 96 - 34
        vis = max(1, area // rowh)
        self.scroll = max(0, min(self.scroll, max(0, len(w.networks) - vis)))
        mouse = pygame.mouse.get_pos()
        for k in range(vis):
            i = self.scroll + k
            if i >= len(w.networks):
                break
            ssid, sig, sec = w.networks[i]
            rect = pygame.Rect(r.x + 12, top + k * rowh, r.w - 24, rowh - 4)
            cur = ssid == w.current
            rrect(s, mix(RAISED, GREEN, 0.18) if cur else RAISED if rect.collidepoint(mouse) and not self.ask else PANEL, rect, 8)
            wifi_bars(s, rect.x + 14, rect.y + 11, sig)
            draw_text(s, ellipsize(ssid, 15, rect.w - 190), rect.x + 52, rect.y + 6, 15, TEXT, cur)
            draw_text(s, "%d%%  %s" % (sig, sec or "abierta"), rect.x + 52, rect.y + 25, 11, DIM)
            if cur:
                draw_text(s, "Conectada", rect.right - 12, rect.y + 13, 13, GREEN, True, "r")
            elif sec:
                draw_text(s, "clave", rect.right - 12, rect.y + 13, 13, BLUE, False, "r")
            self.add(rect, ("net", i))
        if w.busy:
            spinner(s, r.right - 28, r.bottom - 17, 8, BLUE, t, 2)
        draw_text(s, ellipsize(w.message, 13, r.w - 70), r.x + 14, r.bottom - 25, 13, GREEN if w.ok else RED)
        if self.ask:
            veil = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 170))
            s.blit(veil, r.topleft)
            d = pygame.Rect(0, 0, r.w - 80, 176)
            d.center = (r.centerx, r.centery - 20)
            self.add(d, "noop")
            rrect(s, PANEL, d, 12)
            rrect(s, BLUE, d, 12, 2)
            draw_text(s, ellipsize("Conectar a " + self.ask, 16, d.w - 32, True), d.x + 16, d.y + 14, 16, TEXT, True)
            self.pw.draw(s, (d.x + 16, d.y + 56, d.w - 32, 36), True)
            self.button(s, (d.x + 16, d.bottom - 50, 110, 32), "Conectar", "ok", GREEN, bool(self.pw.text))
            self.button(s, (d.right - 126, d.bottom - 50, 110, 32), "Cancelar", "cancel", RED)


# ================================================================ IDE Python
SYN = {"keyword": BLUE, "string": (120, 255, 160), "comment": (88, 112, 100), "number": (255, 120, 130),
       "builtin": LIME, "def": LBLUE, "plain": TEXT}


class IDEApp(App):
    title, size, kind = "Python IDE", (940, 600), "ide"
    LH = 20

    def __init__(self, sysm, desk, path=None):
        super().__init__(sysm, desk)
        self.lines, self.cx, self.cy, self.top, self.left = [""], 0, 0, 0, 0
        self.path, self.dirty, self.runner = None, False, None
        self.output, self.out_scroll, self.status, self.status_col = [], 0, "Listo", DIM
        self.ed_rect = self.out_rect = pygame.Rect(0, 0, 1, 1)
        if path and os.path.isfile(path):
            self.load(path)
        else:
            self.lines = ["# Nuevo programa de SpOS2", 'print("Hola, SpOS2!")', ""]
            self.cy = 2

    def window_title(self):
        return "Python IDE - %s%s" % (os.path.basename(self.path) if self.path else "sin titulo", " *" if self.dirty else "")

    # ---- archivos
    def load(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                self.lines = f.read().replace("\t", "    ").split("\n") or [""]
            self.path, self.dirty, self.cx, self.cy, self.top = path, False, 0, 0, 0
        except OSError as ex:
            self.s.toast("No se pudo abrir: %s" % ex, RED)

    def save(self):
        if not self.path:
            d = os.path.join(self.s.home, "Proyectos")
            os.makedirs(d, exist_ok=True)
            n, p = 1, os.path.join(d, "programa.py")
            while os.path.exists(p):
                n += 1
                p = os.path.join(d, "programa%d.py" % n)
            self.path = p
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.lines))
            self.dirty = False
            self.status, self.status_col = "Guardado: " + self.path, GREEN
            return True
        except OSError as ex:
            self.status, self.status_col = "Error al guardar: %s" % ex, RED
            return False

    def new(self):
        self.lines, self.cx, self.cy, self.top, self.path, self.dirty = [""], 0, 0, 0, None, False

    def run(self):
        if self.runner:
            return
        if not self.save():
            return
        self.output, self.out_scroll = [], 0
        self.runner = core.ScriptRunner(self.path)
        try:
            self.runner.start()
        except OSError as ex:
            self.runner = None
            self.output = ["No se pudo iniciar Python: %s" % ex]
            return
        self.status, self.status_col = "Ejecutando...", BLUE

    def stop(self):
        if self.runner:
            self.runner.stop()

    def on_close(self):
        self.stop()

    def update(self, dt):
        if self.runner:
            self.output.extend(self.runner.drain())
            del self.output[:-2000]
            if self.runner.finished and self.runner.q.empty():
                rc, dur = self.runner.returncode, time.time() - self.runner.t0
                self.status = "Terminado (codigo %s) en %.1fs" % (rc, dur)
                self.status_col = GREEN if rc == 0 else RED
                self.runner = None

    # ---- edicion
    def insert(self, text):
        ln = self.lines[self.cy]
        self.lines[self.cy] = ln[:self.cx] + text + ln[self.cx:]
        self.cx += len(text)
        self.dirty = True

    def event(self, e, r):
        if e.type == pygame.MOUSEWHEEL:
            if self.out_rect.collidepoint(pygame.mouse.get_pos()):
                self.out_scroll = max(0, self.out_scroll + e.y * 3)
            else:
                self.top = max(0, min(len(self.lines) - 1, self.top - e.y * 3))
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            i = self.hit(e.pos)
            if i == "new":
                self.new()
            elif i == "save":
                self.save()
            elif i == "run":
                self.run()
            elif i == "stop":
                self.stop()
            elif self.ed_rect.collidepoint(e.pos):
                cw = font(15).size("M")[0]
                self.cy = max(0, min(len(self.lines) - 1, self.top + (e.pos[1] - self.ed_rect.y) // self.LH))
                self.cx = max(0, min(len(self.lines[self.cy]), self.left + int(round((e.pos[0] - self.ed_rect.x - 58) / cw))))
            return
        if e.type != pygame.KEYDOWN:
            return
        k, ctrl = e.key, e.mod & pygame.KMOD_CTRL
        if ctrl:
            if k == pygame.K_s:
                self.save()
            elif k == pygame.K_n:
                self.new()
            elif k == pygame.K_r:
                self.run()
            elif k == pygame.K_c:
                self.stop()
            return
        ln = self.lines[self.cy]
        if k == pygame.K_F5:
            self.run()
        elif k == pygame.K_LEFT:
            if self.cx > 0:
                self.cx -= 1
            elif self.cy > 0:
                self.cy -= 1
                self.cx = len(self.lines[self.cy])
        elif k == pygame.K_RIGHT:
            if self.cx < len(ln):
                self.cx += 1
            elif self.cy < len(self.lines) - 1:
                self.cy, self.cx = self.cy + 1, 0
        elif k == pygame.K_UP:
            self.cy = max(0, self.cy - 1)
            self.cx = min(self.cx, len(self.lines[self.cy]))
        elif k == pygame.K_DOWN:
            self.cy = min(len(self.lines) - 1, self.cy + 1)
            self.cx = min(self.cx, len(self.lines[self.cy]))
        elif k == pygame.K_HOME:
            self.cx = 0
        elif k == pygame.K_END:
            self.cx = len(ln)
        elif k == pygame.K_PAGEUP:
            self.cy = max(0, self.cy - 15)
            self.cx = min(self.cx, len(self.lines[self.cy]))
        elif k == pygame.K_PAGEDOWN:
            self.cy = min(len(self.lines) - 1, self.cy + 15)
            self.cx = min(self.cx, len(self.lines[self.cy]))
        elif k == pygame.K_BACKSPACE:
            if self.cx > 0:
                self.lines[self.cy] = ln[:self.cx - 1] + ln[self.cx:]
                self.cx -= 1
            elif self.cy > 0:
                prev = self.lines[self.cy - 1]
                self.lines[self.cy - 1] = prev + ln
                del self.lines[self.cy]
                self.cy, self.cx = self.cy - 1, len(prev)
            self.dirty = True
        elif k == pygame.K_DELETE:
            if self.cx < len(ln):
                self.lines[self.cy] = ln[:self.cx] + ln[self.cx + 1:]
            elif self.cy < len(self.lines) - 1:
                self.lines[self.cy] = ln + self.lines[self.cy + 1]
                del self.lines[self.cy + 1]
            self.dirty = True
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            ind = len(ln) - len(ln.lstrip(" "))
            if ln[:self.cx].rstrip().endswith(":"):
                ind += 4
            self.lines[self.cy] = ln[:self.cx]
            self.lines.insert(self.cy + 1, " " * ind + ln[self.cx:])
            self.cy, self.cx, self.dirty = self.cy + 1, ind, True
        elif k == pygame.K_TAB:
            self.insert("    ")
        elif e.unicode and e.unicode.isprintable():
            self.insert(e.unicode)

    # ---- dibujo
    def draw(self, s, r):
        self.begin()
        s.fill(WIN, r)
        s.fill(PANEL, (r.x, r.y, r.w, 38))
        self.button(s, (r.x + 8, r.y + 6, 70, 26), "Nuevo", "new", BLUE, True, 13)
        self.button(s, (r.x + 84, r.y + 6, 80, 26), "Guardar", "save", BLUE, True, 13)
        self.button(s, (r.x + 170, r.y + 6, 110, 26), "Ejecutar F5", "run", GREEN, not self.runner, 13)
        self.button(s, (r.x + 286, r.y + 6, 80, 26), "Detener", "stop", RED, bool(self.runner), 13)
        draw_text(s, ellipsize(self.path or "(sin guardar)", 12, r.w - 400), r.right - 10, r.y + 12, 12, DIM, False, "r")
        eh = int((r.h - 38) * 0.62)
        self.ed_rect = pygame.Rect(r.x, r.y + 38, r.w, eh)
        self.out_rect = pygame.Rect(r.x, self.ed_rect.bottom, r.w, r.bottom - self.ed_rect.bottom)
        f = font(15)
        cw, lh = f.size("M")[0], self.LH
        vis, cols = max(1, eh // lh), max(5, (r.w - 70) // cw)
        if self.cy < self.top:
            self.top = self.cy
        elif self.cy >= self.top + vis:
            self.top = self.cy - vis + 1
        if self.cx < self.left:
            self.left = self.cx
        elif self.cx >= self.left + cols:
            self.left = self.cx - cols + 1
        old = s.get_clip()
        s.set_clip(self.ed_rect)
        s.fill(TERM_BG, self.ed_rect)
        s.fill(PANEL, (r.x, self.ed_rect.y, 50, eh))
        for k in range(vis):
            i = self.top + k
            if i >= len(self.lines):
                break
            y = self.ed_rect.y + k * lh
            if i == self.cy:
                s.fill((18, 26, 34), (r.x + 50, y, r.w - 50, lh))
            draw_text(s, str(i + 1), r.x + 42, y + 1, 13, T.accent if i == self.cy else DIM, False, "r")
            x = r.x + 58
            for seg, kind in core.highlight(self.lines[i][self.left:]):
                x += draw_text(s, seg, x, y + 1, 15, SYN[kind], kind in ("keyword", "def"))
        if int(time.time() * 2) % 2 == 0:
            cy = self.ed_rect.y + (self.cy - self.top) * lh
            pygame.draw.rect(s, T.accent, (r.x + 58 + (self.cx - self.left) * cw, cy + 1, 2, lh - 2))
        s.set_clip(old)
        # salida
        pygame.draw.line(s, T.accent, (r.x, self.out_rect.y), (r.right, self.out_rect.y), 1)
        s.fill(PANEL, (r.x, self.out_rect.y + 1, r.w, 22))
        draw_text(s, "Salida", r.x + 10, self.out_rect.y + 4, 13, LBLUE, True)
        if self.runner:
            spinner(s, r.right - 16, self.out_rect.y + 12, 7, BLUE, time.time(), 2)
        draw_text(s, ellipsize(self.status, 12, r.w - 120), r.right - 30, self.out_rect.y + 5, 12, self.status_col, False, "r")
        body = pygame.Rect(r.x, self.out_rect.y + 24, r.w, self.out_rect.h - 24)
        ocols, orows = max(10, (r.w - 24) // cw), max(1, body.h // lh)
        vl = []
        for ln in reversed(self.output[-300:]):
            chunks = [ln[i:i + ocols] for i in range(0, max(len(ln), 1), ocols)]
            vl.extend(reversed(chunks))
            if len(vl) >= orows + self.out_scroll:
                break
        vl.reverse()
        self.out_scroll = max(0, min(self.out_scroll, max(0, len(vl) - orows)))
        shown = (vl[:len(vl) - self.out_scroll] if self.out_scroll else vl)[-orows:]
        old = s.get_clip()
        s.set_clip(body)
        for k, ln in enumerate(shown):
            bad = ln.startswith(("Traceback", "  File")) or "Error" in ln or "Exception" in ln
            draw_text(s, ln, r.x + 12, body.y + 2 + k * lh, 15, RED if bad else TEXT)
        s.set_clip(old)


# ================================================================ Info y Ajustes
class InfoApp(App):
    title, size, kind, single = "Acerca de SpOS2", (600, 470), "info", True
    ROWS = [("Terminal, archivos y escritorio", None), ("Musica mp3/ogg/wav/flac", None), ("Redes WiFi y login", None),
            ("Python: consola + IDE + .py", "python"), ("Temas de color", "themes"),
            ("Visualizador de musica", "visualizer"), ("Fondo animado", "wallpaper")]

    def draw(self, s, r):
        s.fill(WIN, r)
        ed = self.s.ed
        blit_logo(s, 120, r.x + 90, r.y + 82)
        draw_text(s, "SpOS2", r.x + 180, r.y + 22, 32, T.accent, True)
        draw_text(s, "Operating System  v" + VERSION, r.x + 180, r.y + 62, 14, DIM)
        badge = pygame.Rect(r.x + 180, r.y + 88, 190, 28)
        rrect(s, mix(PANEL, PAL[ed["color"]], 0.3), badge, 8)
        rrect(s, PAL[ed["color"]], badge, 8, 1)
        draw_text(s, "%s  %s" % (ed["tag"], ed["name"]), badge.centerx, badge.y + 5, 15, TEXT, True, "c")
        info = "Python %s | pygame %s | %dx%d | audio %s | wifi %s" % (
            sys.version.split()[0], pygame.version.ver, W, H, "ok" if self.s.player.audio else "no",
            "demo" if self.s.wifi.demo else "real")
        draw_text(s, ellipsize(info, 12, r.w - 200), r.x + 180, r.y + 128, 12, DIM)
        draw_text(s, "Usuario: " + self.s.user, r.x + 180, r.y + 148, 13, TEXT)
        y = r.y + 188
        cols = [r.x + 330, r.x + 402, r.x + 474]
        for x, k in zip(cols, core.EDITION_ORDER):
            e = core.EDITIONS[k]
            if k == ed["key"]:
                rrect(s, mix(PANEL, PAL[e["color"]], 0.18), (x - 30, y - 6, 60, 28 + len(self.ROWS) * 30), 8)
            draw_text(s, e["tag"], x, y, 16, PAL[e["color"]], True, "c")
        for i, (label, feat) in enumerate(self.ROWS):
            yy = y + 30 + i * 30
            draw_text(s, label, r.x + 24, yy, 14, TEXT)
            for x, k in zip(cols, core.EDITION_ORDER):
                has = feat is None or feat in core.EDITIONS[k]["features"]
                draw_text(s, "si" if has else "--", x, yy, 14, GREEN if has else RED, has, "c")


class SettingsApp(App):
    title, size, kind, single = "Ajustes", (520, 440), "settings", True

    def __init__(self, sysm, desk):
        super().__init__(sysm, desk)
        self.drag, self.vol_rect = False, pygame.Rect(0, 0, 1, 1)

    def event(self, e, r):
        if e.type != pygame.MOUSEBUTTONDOWN or e.button != 1:
            return
        i = self.hit(e.pos)
        if i == "vol":
            self.drag = True
            self.s.player.set_volume((e.pos[0] - self.vol_rect.x) / self.vol_rect.w)
        elif i == "logout":
            self.s.goto("login")
        elif isinstance(i, tuple) and i[0] == "accent":
            if self.s.feature("themes"):
                self.s.set_accent(i[1])
            else:
                self.s.toast("Los temas son exclusivos de Premium", RED)
        elif isinstance(i, tuple) and i[0] == "wall":
            if self.s.feature("wallpaper"):
                self.s.cfg["wallpaper"] = i[1]
                core.save_config(self.s.cfg)
            else:
                self.s.toast("El fondo animado es exclusivo de Premium", RED)

    def update(self, dt):
        if self.drag:
            if pygame.mouse.get_pressed()[0]:
                self.s.player.set_volume((pygame.mouse.get_pos()[0] - self.vol_rect.x) / self.vol_rect.w)
            else:
                self.drag = False
                self.s.cfg["volume"] = self.s.player.volume
                core.save_config(self.s.cfg)

    def draw(self, s, r):
        self.begin()
        s.fill(WIN, r)
        pl = self.s.player
        draw_text(s, "Volumen", r.x + 24, r.y + 20, 15, TEXT, True)
        self.vol_rect = pygame.Rect(r.x + 24, r.y + 54, r.w - 110, 8)
        rrect(s, LINE, self.vol_rect, 4)
        rrect(s, BLUE, (self.vol_rect.x, self.vol_rect.y, max(8, int(self.vol_rect.w * pl.volume)), 8), 4)
        pygame.draw.circle(s, TEXT, (self.vol_rect.x + int(self.vol_rect.w * pl.volume), self.vol_rect.centery), 8)
        draw_text(s, "%d%%" % round(pl.volume * 100), self.vol_rect.right + 14, r.y + 47, 14, DIM)
        self.add(self.vol_rect.inflate(0, 24), "vol")
        pro = self.s.feature("themes")
        draw_text(s, "Color de acento", r.x + 24, r.y + 96, 15, TEXT, True)
        draw_text(s, "" if pro else "PRO", r.x + 160, r.y + 98, 12, RED, True)
        for n, (name, col) in enumerate(PAL.items()):
            rect = pygame.Rect(r.x + 24 + n * 64, r.y + 124, 52, 36)
            rrect(s, col if pro else mix(PANEL, col, 0.3), rect, 8)
            if self.s.cfg.get("accent") == name and pro:
                rrect(s, TEXT, rect.inflate(6, 6), 10, 2)
            self.add(rect, ("accent", name))
        draw_text(s, "Fondo de escritorio", r.x + 24, r.y + 184, 15, TEXT, True)
        draw_text(s, "" if self.s.feature("wallpaper") else "PRO", r.x + 200, r.y + 186, 12, RED, True)
        for n, (key, lab) in enumerate((("auto", "Auto"), ("constellation", "Constelacion"), ("grid", "Cuadricula"), ("plain", "Simple"))):
            on = self.s.cfg.get("wallpaper") == key
            self.button(s, (r.x + 24 + n * 118, r.y + 212, 110, 30), lab, ("wall", key), T.accent if on else BLUE,
                        True, 13)
        draw_text(s, "Cuenta", r.x + 24, r.y + 270, 15, TEXT, True)
        draw_text(s, "Usuario: %s    Edicion: %s %s" % (self.s.user, self.s.ed["tag"], self.s.ed["name"]),
                  r.x + 24, r.y + 298, 14, DIM)
        self.button(s, (r.x + 24, r.y + 332, 150, 32), "Cerrar sesion", "logout", RED)


APP_CLASSES = {"terminal": TerminalApp, "files": FilesApp, "music": MusicApp, "wifi": WifiApp,
               "ide": IDEApp, "info": InfoApp, "settings": SettingsApp}
MENU = [("terminal", "Terminal", "terminal"), ("files", "Archivos", "files"), ("music", "Musica", "music"),
        ("wifi", "WiFi", "wifi"), ("ide", "Python IDE", "ide"), ("settings", "Ajustes", "settings"),
        ("info", "Acerca de", "info")]


class Window:
    def __init__(self, app, x, y):
        w, h = app.size
        self.app, self.rect = app, pygame.Rect(x, y, w, h + TH)
        self.minimized, self.maxed, self.saved = False, False, None

    def content(self):
        r = self.rect
        return pygame.Rect(r.x + 1, r.y + TH, r.w - 2, r.h - TH - 1)

    def buttons(self):
        r = self.rect
        return {"close": (r.right - 20, r.y + TH // 2), "max": (r.right - 44, r.y + TH // 2),
                "min": (r.right - 68, r.y + TH // 2)}


# ================================================================ Escritorio
class Desktop:
    def __init__(self, sysm):
        self.s, self.windows, self.menu, self.drag, self.last_click = sysm, [], False, None, 0.0
        self.nodes = [[random.uniform(0, W), random.uniform(0, H - TB), random.uniform(-14, 14), random.uniform(-14, 14),
                       random.choice((GREEN, GREEN, BLUE, RED))] for _ in range(44)]
        self.grid = None
        self.apps = [m for m in MENU if sysm.feature(m[0] if m[0] != "files" else "files")]
        self.icons = [m for m in self.apps if m[0] in ("terminal", "files", "music", "wifi", "ide", "settings", "info")]
        sysm.toast("Bienvenido, %s" % sysm.user, GREEN)
        self.open("terminal")

    # ---- ventanas
    def open(self, kind, **kw):
        if not self.s.feature(kind):
            self.s.toast("No incluido en tu edicion (%s)" % self.s.ed["name"], RED)
            return None
        cls = APP_CLASSES[kind]
        if cls.single:
            for w in self.windows:
                if isinstance(w.app, cls):
                    w.minimized = False
                    self.focus(w)
                    return w
        n = len(self.windows)
        app = cls(self.s, self, **kw)
        w = Window(app, 130 + (n % 6) * 34, 36 + (n % 6) * 28)
        w.rect.right = min(w.rect.right, W - 6)
        w.rect.bottom = min(w.rect.bottom, H - TB - 6)
        self.windows.append(w)
        self.menu = False
        return w

    def focus(self, w):
        if w in self.windows:
            self.windows.remove(w)
            self.windows.append(w)

    def close(self, w):
        w.app.on_close()
        if w in self.windows:
            self.windows.remove(w)

    def close_app(self, app):
        for w in list(self.windows):
            if w.app is app:
                self.close(w)

    def toggle_max(self, w):
        if w.maxed:
            w.rect, w.maxed = w.saved, False
        else:
            w.saved, w.maxed = w.rect.copy(), True
            w.rect = pygame.Rect(0, 0, W, H - TB)

    def open_file(self, path):
        low = path.lower()
        if os.path.isdir(path):
            w = self.open("files")
            w.app.go(path)
        elif low.endswith(core.MUSIC_EXT):
            self.s.player.add(path, play=True)
            self.open("music")
            self.s.toast("Reproduciendo " + os.path.basename(path), RED)
        elif low.endswith((".py", ".txt", ".md", ".json", ".cfg", ".csv")):
            if self.s.feature("ide"):
                self.open("ide", path=path)
            else:
                self.s.toast("Editar archivos: edicion </> Programmer o Premium", RED)
        else:
            self.s.toast("Tipo de archivo no soportado", BLUE)

    # ---- eventos
    def window_at(self, pos):
        for w in reversed(self.windows):
            if not w.minimized and w.rect.collidepoint(pos):
                return w
        return None

    def event(self, e):
        if e.type == pygame.DROPFILE:
            self.open_file(e.file)
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_t and e.mod & pygame.KMOD_CTRL and e.mod & pygame.KMOD_ALT:
                self.open("terminal")
            elif self.windows and not self.windows[-1].minimized:
                w = self.windows[-1]
                w.app.event(e, w.content())
        elif e.type == pygame.MOUSEWHEEL:
            w = self.window_at(pygame.mouse.get_pos())
            if w:
                w.app.event(e, w.content())
        elif e.type == pygame.MOUSEMOTION and self.drag:
            w, dx, dy = self.drag
            w.rect.x = max(-w.rect.w + 120, min(W - 60, e.pos[0] - dx))
            w.rect.y = max(0, min(H - TB - TH, e.pos[1] - dy))
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.drag = None
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.click(e)

    def start_rect(self):
        return pygame.Rect(8, H - TB + 7, 112, 34)

    def menu_rect(self):
        n = len(self.apps) + 3
        return pygame.Rect(8, H - TB - 12 - n * 34 - 14, 250, n * 34 + 14)

    def click(self, e):
        pos = e.pos
        if self.menu:
            mr = self.menu_rect()
            if mr.collidepoint(pos):
                y = mr.y + 8
                for kind, label, _ in self.apps:
                    if pygame.Rect(mr.x, y, mr.w, 34).collidepoint(pos):
                        self.open(kind)
                        return
                    y += 34
                y += 6
                for act in ("logout", "reboot", "shutdown"):
                    if pygame.Rect(mr.x, y, mr.w, 34).collidepoint(pos):
                        if act == "shutdown":
                            self.s.quit = True
                        else:
                            self.s.goto("login" if act == "logout" else "boot")
                        return
                    y += 34
                return
            self.menu = False
            if self.start_rect().collidepoint(pos):
                return
        if pos[1] >= H - TB:
            return self.click_taskbar(pos)
        w = self.window_at(pos)
        if w:
            if w is not self.windows[-1]:
                self.focus(w)
            for name, (bx, by) in w.buttons().items():
                if (pos[0] - bx) ** 2 + (pos[1] - by) ** 2 <= 100:
                    if name == "close":
                        self.close(w)
                    elif name == "max":
                        self.toggle_max(w)
                    else:
                        w.minimized = True
                    return
            if pos[1] < w.rect.y + TH:
                now = time.time()
                if now - self.last_click < 0.35:
                    self.toggle_max(w)
                else:
                    self.drag = None if w.maxed else (w, pos[0] - w.rect.x, pos[1] - w.rect.y)
                self.last_click = now
            else:
                w.app.event(e, w.content())
            return
        # iconos del escritorio
        for i, (kind, label, _) in enumerate(self.icons):
            if pygame.Rect(18, 18 + i * 92, 84, 84).collidepoint(pos):
                self.open(kind)
                return

    def click_taskbar(self, pos):
        if self.start_rect().collidepoint(pos):
            self.menu = True
            return
        x = 136
        for w in self.windows:
            if pygame.Rect(x, H - TB + 7, 150, 34).collidepoint(pos):
                if w.minimized or w is not self.windows[-1]:
                    w.minimized = False
                    self.focus(w)
                else:
                    w.minimized = True
                return
            x += 156
        if pygame.Rect(W - 230, H - TB + 4, 36, 40).collidepoint(pos):
            self.open("wifi")
        elif pygame.Rect(W - 188, H - TB + 4, 36, 40).collidepoint(pos):
            self.open("music")

    # ---- actualizacion
    def update(self, dt):
        for w in self.windows:
            w.app.update(dt)
        self.s.player.update()
        if self.s.wallpaper() == "constellation":
            for n in self.nodes:
                n[0] += n[2] * dt
                n[1] += n[3] * dt
                if n[0] < 0 or n[0] > W:
                    n[2] = -n[2]
                if n[1] < 0 or n[1] > H - TB:
                    n[3] = -n[3]

    # ---- dibujo
    def draw_wallpaper(self, s):
        s.fill(BLACK)
        mode = self.s.wallpaper()
        if mode == "grid":
            if self.grid is None:
                self.grid = pygame.Surface((W, H))
                self.grid.fill(BLACK)
                for x in range(0, W, 48):
                    pygame.draw.line(self.grid, (12, 24, 34), (x, 0), (x, H))
                for y in range(0, H, 48):
                    pygame.draw.line(self.grid, (12, 24, 34), (0, y), (W, y))
            s.blit(self.grid, (0, 0))
        elif mode == "constellation":
            for i, a in enumerate(self.nodes):
                for b in self.nodes[i + 1:]:
                    d = math.hypot(a[0] - b[0], a[1] - b[1])
                    if d < 170:
                        pygame.draw.line(s, mix(BLACK, a[4], 0.35 * (1 - d / 170)), (a[0], a[1]), (b[0], b[1]))
            for n in self.nodes:
                pygame.draw.circle(s, mix(BLACK, n[4], 0.6), (n[0], n[1]), 3)
        blit_logo(s, 360, W - 230, H - TB - 190, 0.22)

    def draw_window(self, s, w, focused):
        r, acc = w.rect, T.accent
        if not w.maxed:
            s.blit(shadow(r.w, r.h), (r.x - 20, r.y - 14))
        pygame.draw.rect(s, WIN, r, border_radius=0 if w.maxed else 10)
        pygame.draw.rect(s, (19, 26, 34) if focused else (14, 18, 23), (r.x, r.y, r.w, TH),
                         border_top_left_radius=0 if w.maxed else 10, border_top_right_radius=0 if w.maxed else 10)
        draw_icon(s, w.app.kind, r.x + 18, r.y + TH // 2, 18, APP_ICON_COLOR.get(w.app.kind, acc))
        draw_text(s, ellipsize(w.app.window_title(), 14, r.w - 140, True), r.x + 36, r.y + 7, 14,
                  TEXT if focused else DIM, True)
        for name, (bx, by) in w.buttons().items():
            col = {"close": RED, "max": GREEN, "min": BLUE}[name]
            pygame.draw.circle(s, col if focused else mix(col, BLACK, 0.55), (bx, by), 7)
        pygame.draw.line(s, acc if focused else LINE, (r.x + 1, r.y + TH - 1), (r.right - 2, r.y + TH - 1), 1)
        pygame.draw.rect(s, acc if focused else LINE, r, 1, border_radius=0 if w.maxed else 10)
        old = s.get_clip()
        c = w.content()
        s.set_clip(c)
        w.app.draw(s, c)
        s.set_clip(old)

    def draw(self, s):
        self.draw_wallpaper(s)
        mouse = pygame.mouse.get_pos()
        for i, (kind, label, _) in enumerate(self.icons):
            rect = pygame.Rect(18, 18 + i * 92, 84, 84)
            if rect.collidepoint(mouse):
                rrect(s, mix(BLACK, T.accent, 0.18), rect, 12)
            col = APP_ICON_COLOR.get(kind, T.accent)
            rrect(s, mix(PANEL, col, 0.2), (rect.centerx - 25, rect.y + 6, 50, 50), 12)
            rrect(s, col, (rect.centerx - 25, rect.y + 6, 50, 50), 12, 2)
            draw_icon(s, kind, rect.centerx, rect.y + 31, 30, col)
            draw_text(s, label, rect.centerx, rect.y + 62, 13, TEXT, False, "c")
        for w in self.windows:
            if not w.minimized:
                self.draw_window(s, w, w is self.windows[-1])
        self.draw_taskbar(s)
        if self.menu:
            self.draw_menu(s)
        self.s.draw_toasts(s)

    def draw_taskbar(self, s):
        acc, t = T.accent, self.s.wifi
        s.fill(PANEL, (0, H - TB, W, TB))
        pygame.draw.line(s, acc, (0, H - TB), (W, H - TB), 2)
        sb = self.start_rect()
        rrect(s, mix(RAISED, acc, 0.3 if self.menu else 0.12), sb, 8)
        rrect(s, acc, sb, 8, 1)
        blit_logo(s, 40, sb.x + 20, sb.centery)
        draw_text(s, "SpOS2", sb.x + 40, sb.y + 8, 15, TEXT, True)
        x = 136
        for w in self.windows:
            rect = pygame.Rect(x, H - TB + 7, 150, 34)
            top = w is self.windows[-1] and not w.minimized
            rrect(s, RAISED if top else (16, 21, 27), rect, 8)
            if top:
                pygame.draw.rect(s, acc, (rect.x + 8, rect.bottom - 3, rect.w - 16, 3), border_radius=2)
            draw_icon(s, w.app.kind, rect.x + 16, rect.centery, 14, APP_ICON_COLOR.get(w.app.kind, acc))
            draw_text(s, ellipsize(w.app.window_title(), 12, 110), rect.x + 30, rect.y + 9, 12, DIM if w.minimized else TEXT)
            x += 156
        # bandeja
        ed = self.s.ed
        eb = pygame.Rect(W - 150, H - TB + 11, 46, 26)
        rrect(s, mix(PANEL, PAL[ed["color"]], 0.3), eb, 6)
        rrect(s, PAL[ed["color"]], eb, 6, 1)
        draw_text(s, ed["tag"], eb.centerx, eb.y + 4, 13, TEXT, True, "c")
        wx = W - 230
        wifi_bars(s, wx + 4, H - TB + 14, 100 if t.current else 0, GREEN if t.current else RED)
        pl = self.s.player
        mx = W - 188
        for i in range(4):
            hh = 4 + int(10 * abs(math.sin(time.time() * 6 + i * 1.3))) if pl.state == "play" else 4
            pygame.draw.rect(s, RED if pl.state == "play" else DIM, (mx + 6 + i * 6, H - TB + 32 - hh, 4, hh))
        draw_text(s, time.strftime("%H:%M"), W - 12, H - TB + 6, 17, TEXT, True, "r")
        draw_text(s, self.s.user, W - 12, H - TB + 27, 11, DIM, False, "r")

    def draw_menu(self, s):
        mr = self.menu_rect()
        s.blit(shadow(mr.w, mr.h), (mr.x - 20, mr.y - 14))
        rrect(s, PANEL, mr, 12)
        rrect(s, T.accent, mr, 12, 1)
        mouse = pygame.mouse.get_pos()
        y = mr.y + 8
        for kind, label, _ in self.apps:
            rect = pygame.Rect(mr.x + 6, y, mr.w - 12, 32)
            if rect.collidepoint(mouse):
                rrect(s, RAISED, rect, 8)
            draw_icon(s, kind, rect.x + 22, rect.centery, 18, APP_ICON_COLOR.get(kind, T.accent))
            draw_text(s, label, rect.x + 48, rect.y + 7, 15, TEXT)
            y += 34
        pygame.draw.line(s, LINE, (mr.x + 12, y + 2), (mr.right - 12, y + 2))
        y += 6
        for label, col in (("Cerrar sesion", BLUE), ("Reiniciar", BLUE), ("Apagar", RED)):
            rect = pygame.Rect(mr.x + 6, y, mr.w - 12, 32)
            if rect.collidepoint(mouse):
                rrect(s, RAISED, rect, 8)
            draw_text(s, label, rect.x + 48, rect.y + 7, 15, col)
            pygame.draw.circle(s, col, (rect.x + 22, rect.centery), 5)
            y += 34


# ================================================================ Pantallas: arranque, edicion, login
class BootScene:
    DURATION = 11.5
    LOG = [(0.4, "SpOS2 nucleo %s (x86_64)" % VERSION, "ok"), (1.4, "Montando sistema de archivos virtual", "ok"),
           (2.5, "Iniciando audio (SDL_mixer)", "audio"), (3.6, "Generando sonidos del sistema", "ok"),
           (4.7, "Buscando interfaces de red", "net"), (5.9, "Cargando interprete Python " + sys.version.split()[0], "py"),
           (7.0, "Cargando logo.png - constelacion verde", "ok"), (8.2, "Preparando cuentas de usuario", "ok"),
           (9.4, "Iniciando gestor de ventanas", "ok"), (10.6, "SpOS2 listo", "ok")]

    def __init__(self, sysm):
        self.s, self.t0, self.done_assets = sysm, time.time(), False
        threading.Thread(target=self._assets, daemon=True).start()

    def _assets(self):
        try:
            self.s.assets = core.ensure_assets()
        except Exception:
            self.s.assets = {}
        self.done_assets = True

    def event(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_SPACE) and time.time() - self.t0 > 1.5:
            self.t0 = min(self.t0, time.time() - self.DURATION)

    def update(self, dt):
        if time.time() - self.t0 >= self.DURATION and self.done_assets:
            self.s.goto("edition" if self.s.ed is None else "login")

    def status(self, kind):
        s = self.s
        if kind == "audio":
            return ("ok", "") if pygame.mixer.get_init() else ("fail", " (sin dispositivo de audio)")
        if kind == "net":
            return ("info", " (modo demostracion)") if s.wifi.demo else ("ok", " (NetworkManager)")
        if kind == "py":
            return ("ok", "") if s.ed is None or s.feature("python") else ("info", " (solo en Programmer/Premium)")
        return ("ok", "")

    def draw(self, s):
        t = time.time() - self.t0
        s.fill(BLACK)
        fade = max(0.0, min(1.0, (t - 0.5) / 2.6))
        cx, cy = W // 2, 270
        blit_logo(s, 340, cx, cy, fade * (0.93 + 0.07 * math.sin(t * 2.2)))
        for rad, col, sp in ((215, GREEN, 0.9), (228, BLUE, -1.3), (241, RED, 1.7)):
            a = t * sp
            f = int(255 * fade)
            c = (col[0] * f // 255, col[1] * f // 255, col[2] * f // 255)
            for k in range(3):
                pygame.draw.arc(s, c, (cx - rad, cy - rad, rad * 2, rad * 2), a + k * 2.09, a + k * 2.09 + 0.9, 3)
        prog = min(1.0, t / self.DURATION)
        prog = prog * prog * (3 - 2 * prog)                     # suave
        bar = pygame.Rect(W // 2 - 300, 560, 600, 10)
        rrect(s, (24, 30, 36), bar, 5)
        rrect(s, GREEN, (bar.x, bar.y, max(10, int(bar.w * prog)), 10), 5)
        draw_text(s, "%d%%" % int(prog * 100), bar.right, bar.y + 16, 13, DIM, False, "r")
        y = 590
        shown = [m for m in self.LOG if t >= m[0]][-5:]
        for _, msg, kind in shown:
            st, extra = self.status(kind)
            tag, col = {"ok": ("[ OK ]", GREEN), "info": ("[INFO]", BLUE), "fail": ("[FAIL]", RED)}[st]
            draw_text(s, tag, bar.x, y, 13, col, True)
            draw_text(s, msg + extra, bar.x + 62, y, 13, TEXT if st == "ok" else col)
            y += 18
        if t > 1.5:
            draw_text(s, "Esc / Espacio: saltar", W - 14, H - 24, 12, (60, 70, 76), False, "r")


class EditionScene:
    def __init__(self, sysm):
        self.s = sysm

    def cards(self):
        return [(k, pygame.Rect(90 + i * 365, 170, 335, 400)) for i, k in enumerate(core.EDITION_ORDER)]

    def pick(self, k):
        self.s.set_edition(k)
        self.s.goto("login")

    def event(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.pick(core.EDITION_ORDER[e.key - pygame.K_1])
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for k, r in self.cards():
                if r.collidepoint(e.pos):
                    self.pick(k)

    def update(self, dt): pass

    def draw(self, s):
        s.fill(BLACK)
        blit_logo(s, 110, W // 2, 70)
        draw_text(s, "Elige la version de SpOS2", W // 2, 118, 22, TEXT, True, "c")
        mouse = pygame.mouse.get_pos()
        feats = {"normal": ["Escritorio y ventanas", "Terminal y archivos", "Musica mp3 / ogg / wav", "Redes WiFi y login"],
                 "programmer": ["Todo lo de Normal", "Consola Python en la terminal", "IDE con resaltado y ejecucion", "Ejecuta scripts .py"],
                 "premium": ["Todo lo de Programmer", "Temas rojo / verde / azul", "Visualizador de musica", "Fondo animado"]}
        for i, (k, r) in enumerate(self.cards()):
            e = core.EDITIONS[k]
            col = PAL[e["color"]]
            over = r.collidepoint(mouse)
            rrect(s, mix(PANEL, col, 0.14 if over else 0.05), r, 16)
            rrect(s, col, r, 16, 3 if over else 1)
            draw_text(s, e["tag"], r.centerx, r.y + 34, 46, col, True, "c")
            draw_text(s, "Version " + e["name"], r.centerx, r.y + 104, 20, TEXT, True, "c")
            for j, f in enumerate(feats[k]):
                pygame.draw.circle(s, col, (r.x + 34, r.y + 176 + j * 36 + 8), 4)
                draw_text(s, f, r.x + 50, r.y + 176 + j * 36, 14, TEXT)
            draw_text(s, "Pulsa %d" % (i + 1), r.centerx, r.bottom - 40, 14, col, False, "c")


class LoginScene:
    def __init__(self, sysm):
        self.s = sysm
        self.register = not core.has_users()
        self.user, self.pw, self.pw2 = TextInput("Usuario", False, 16), TextInput("Clave", True, 40), TextInput("Repite la clave", True, 40)
        self.user.text = sysm.cfg.get("last_user", "") if not self.register else ""
        self.focus, self.msg, self.msg_col, self.t0 = 1 if self.user.text else 0, "", RED, time.time()

    def fields(self):
        return [self.user, self.pw] + ([self.pw2] if self.register else [])

    def card(self):
        return pygame.Rect(W // 2 - 220, 250, 440, 330 if self.register else 280)

    def submit(self):
        u, p = self.user.text.strip(), self.pw.text
        if self.register:
            if p != self.pw2.text:
                self.msg, self.msg_col = "Las claves no coinciden", RED
                return
            ok, m = core.create_user(u, p)
            if not ok:
                self.msg, self.msg_col = m, RED
                return
        ok, name = core.check_user(u, p)
        if ok:
            self.s.login(name)
        else:
            self.msg, self.msg_col, self.pw.text = "Usuario o clave incorrectos", RED, ""

    def event(self, e):
        c = self.card()
        if e.type == pygame.KEYDOWN:
            fs = self.fields()
            self.focus = min(self.focus, len(fs) - 1)
            if e.key == pygame.K_TAB:
                self.focus = (self.focus + 1) % len(fs)
            elif e.key == pygame.K_F2 and core.has_users():
                self.register, self.msg = not self.register, ""
            elif fs[self.focus].key(e) == "enter":
                if self.focus < len(fs) - 1:
                    self.focus += 1
                else:
                    self.submit()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i in range(len(self.fields())):
                if pygame.Rect(c.x + 30, c.y + 100 + i * 52, c.w - 60, 40).collidepoint(e.pos):
                    self.focus = i
            if pygame.Rect(c.x + 30, c.bottom - 62, 190, 42).collidepoint(e.pos):
                self.submit()
            if core.has_users() and pygame.Rect(c.x + 236, c.bottom - 62, 174, 42).collidepoint(e.pos):
                self.register, self.msg = not self.register, ""
            if pygame.Rect(W - 190, H - 40, 180, 30).collidepoint(e.pos) and FIXED_EDITION is None:
                self.s.goto("edition")

    def update(self, dt): pass

    def draw(self, s):
        s.fill(BLACK)
        t = time.time()
        for i in range(0, W, 64):
            pygame.draw.line(s, (9, 15, 21), (i, 0), (i, H))
        for j in range(0, H, 64):
            pygame.draw.line(s, (9, 15, 21), (0, j), (W, j))
        blit_logo(s, 190, W // 2, 140, 0.95)
        c, ed = self.card(), self.s.ed
        col = PAL[ed["color"]]
        rrect(s, PANEL, c, 16)
        rrect(s, col, c, 16, 2)
        draw_text(s, "Crear cuenta" if self.register else "Iniciar sesion", c.x + 30, c.y + 24, 20, TEXT, True)
        badge = pygame.Rect(c.right - 100, c.y + 22, 70, 26)
        rrect(s, mix(PANEL, col, 0.3), badge, 7)
        rrect(s, col, badge, 7, 1)
        draw_text(s, ed["tag"], badge.centerx, badge.y + 4, 14, TEXT, True, "c")
        draw_text(s, ("Primera vez: crea tu usuario" if not core.has_users() else "Version " + ed["name"]),
                  c.x + 30, c.y + 62, 13, DIM)
        for i, f in enumerate(self.fields()):
            f.draw(s, (c.x + 30, c.y + 100 + i * 52, c.w - 60, 40), i == self.focus)
        by = c.bottom - 62
        b1 = pygame.Rect(c.x + 30, by, 190, 42)
        over = b1.collidepoint(pygame.mouse.get_pos())
        rrect(s, mix(PANEL, GREEN, 0.5 if over else 0.3), b1, 10)
        rrect(s, GREEN, b1, 10, 1)
        draw_text(s, "Crear y entrar" if self.register else "Entrar", b1.centerx, b1.y + 11, 16, TEXT, True, "c")
        if core.has_users():
            b2 = pygame.Rect(c.x + 236, by, 174, 42)
            rrect(s, mix(PANEL, BLUE, 0.4 if b2.collidepoint(pygame.mouse.get_pos()) else 0.18), b2, 10)
            rrect(s, BLUE, b2, 10, 1)
            draw_text(s, "Volver" if self.register else "Nueva cuenta", b2.centerx, b2.y + 12, 14, TEXT, False, "c")
        if self.msg:
            draw_text(s, self.msg, c.centerx, c.bottom + 16, 15, self.msg_col, False, "c")
        draw_text(s, "Tab: siguiente campo   Enter: aceptar", c.centerx, c.bottom + 44, 12, DIM, False, "c")
        if FIXED_EDITION is None:
            draw_text(s, "Cambiar version", W - 12, H - 32, 13, BLUE, False, "r")


# ================================================================ Sistema
class System:
    def __init__(self, screen):
        self.screen, self.cfg, self.quit = screen, core.load_config(), False
        self.ed, self.user, self.home = None, "invitado", ""
        self.assets, self.wifi, self.player = {}, core.WifiService(), None
        self.toasts, self.scene, self.desk = [], None, None
        if FIXED_EDITION:
            self.set_edition(FIXED_EDITION)
        self.goto("boot")

    def feature(self, f):
        return self.ed is not None and f in self.ed["features"]

    def set_edition(self, key):
        self.ed = core.EDITIONS[key]
        self.apply_theme()

    def apply_theme(self):
        T.accent = PAL.get(self.cfg.get("accent"), GREEN) if self.feature("themes") else GREEN

    def set_accent(self, name):
        self.cfg["accent"] = name
        core.save_config(self.cfg)
        self.apply_theme()

    def wallpaper(self):
        w = self.cfg.get("wallpaper", "auto")
        if not self.feature("wallpaper") or w == "auto":
            return {"premium": "constellation", "programmer": "grid"}.get(self.ed["key"], "plain")
        return w

    def toast(self, msg, color=GREEN, secs=3.2):
        self.toasts.append([msg, color, time.time() + secs])
        del self.toasts[:-4]

    def draw_toasts(self, s):
        now = time.time()
        self.toasts = [t for t in self.toasts if t[2] > now]
        y = 14
        for msg, col, _ in self.toasts:
            w = text_w(msg, 14) + 44
            rect = pygame.Rect(W - w - 14, y, w, 38)
            s.blit(shadow(rect.w, rect.h), (rect.x - 20, rect.y - 14))
            rrect(s, PANEL, rect, 10)
            rrect(s, col, rect, 10, 1)
            pygame.draw.circle(s, col, (rect.x + 16, rect.centery), 5)
            draw_text(s, msg, rect.x + 32, rect.y + 9, 14, TEXT)
            y += 46

    def play_sound(self, key):
        if pygame.mixer.get_init() and self.assets.get(key):
            try:
                pygame.mixer.Sound(self.assets[key]).play()
            except pygame.error:
                pass

    def login(self, name):
        self.user, self.home = name, core.user_home(name)
        self.cfg["last_user"] = name
        core.save_config(self.cfg)
        if self.player is None:
            self.player = Player(self)
        self.goto("desktop")
        self.play_sound("chime")

    def goto(self, name):
        if self.desk is not None and name != "desktop":
            for w in list(self.desk.windows):
                w.app.on_close()
            self.desk = None
            if self.player:
                self.player.stop()
        if name == "boot":
            self.scene = BootScene(self)
        elif name == "edition":
            self.scene = EditionScene(self)
        elif name == "login":
            self.scene = LoginScene(self)
        elif name == "desktop":
            self.desk = Desktop(self)
            self.scene = self.desk


def main():
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
    core.ensure_dirs()
    fs = "--fullscreen" in sys.argv or os.environ.get("SPOS2_FULLSCREEN") == "1"
    flags = (pygame.SCALED | pygame.FULLSCREEN) if fs else (pygame.SCALED | pygame.RESIZABLE)
    screen = pygame.display.set_mode((W, H), flags)
    pygame.display.set_caption("SpOS2 Operating System")
    load_logo()
    try:
        pygame.display.set_icon(logo_img(64))
    except Exception:
        pass
    pygame.key.set_repeat(350, 32)
    sysm = System(screen)
    clock = pygame.time.Clock()
    while not sysm.quit:
        dt = clock.tick(60) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                sysm.quit = True
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            else:
                sysm.scene.event(e)
        sysm.scene.update(dt)
        sysm.scene.draw(screen)
        pygame.display.flip()
    if sysm.desk:
        for w in list(sysm.desk.windows):
            w.app.on_close()
    if sysm.player:
        sysm.player.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
