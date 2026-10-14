"""SpOS2 - logica del sistema (sin pygame): usuarios, WiFi, Python, ediciones, audio sintetizado."""
import os, sys, json, hashlib, hmac, secrets, subprocess, threading, queue, shutil
import re, io, code, math, wave, time, keyword, builtins
from array import array

FROZEN = getattr(sys, "frozen", False)
BASE = os.path.join(os.path.expanduser("~"), "SpOS2")
USERS_FILE = os.path.join(BASE, "users.json")
CONFIG_FILE = os.path.join(BASE, "config.json")
CACHE = os.path.join(BASE, "cache")
MUSIC_EXT = (".mp3", ".ogg", ".wav", ".flac")


def resource_path(name):
    root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, name)


# ------------------------------------------------------------------ ediciones
_NORMAL = {"terminal", "files", "music", "wifi", "info", "settings"}
_DEV = _NORMAL | {"python", "ide"}
_PRO = _DEV | {"themes", "visualizer", "wallpaper"}

EDITIONS = {
    "normal": dict(key="normal", tag="N", name="Normal", color="green", features=_NORMAL,
                   blurb="Escritorio, terminal, archivos, musica y WiFi"),
    "programmer": dict(key="programmer", tag="</>", name="Programmer", color="blue", features=_DEV,
                       blurb="Todo lo Normal + IDE de Python y consola python"),
    "premium": dict(key="premium", tag="PRO", name="Premium", color="red", features=_PRO,
                    blurb="Todo + temas, visualizador y fondo animado"),
}
EDITION_ORDER = ["normal", "programmer", "premium"]


# ------------------------------------------------------------------ config
DEFAULT_CONFIG = {"volume": 0.7, "accent": "green", "wallpaper": "auto", "playlist": [], "last_user": ""}


def ensure_dirs():
    os.makedirs(BASE, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        ensure_dirs()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=1)
    except Exception:
        pass


# ------------------------------------------------------------------ usuarios
def _load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _hash(pw, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt_hex), 150000).hex()


def has_users():
    return bool(_load_users())


def create_user(name, pw):
    name = name.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,16}", name):
        return False, "Usuario: 3-16 letras, numeros, _ o -"
    if len(pw) < 4:
        return False, "La clave debe tener al menos 4 caracteres"
    users = _load_users()
    if name.lower() in {u.lower() for u in users}:
        return False, "Ese usuario ya existe"
    salt = secrets.token_hex(16)
    users[name] = {"salt": salt, "hash": _hash(pw, salt)}
    try:
        ensure_dirs()
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f)
        try:
            os.chmod(USERS_FILE, 0o600)
        except OSError:
            pass
    except OSError as e:
        return False, "No se pudo guardar: %s" % e
    return True, "Cuenta creada"


def check_user(name, pw):
    users = _load_users()
    for u, rec in users.items():
        if u.lower() == name.strip().lower():
            return hmac.compare_digest(_hash(pw, rec["salt"]), rec["hash"]), u
    _hash(pw, "00" * 16)  # tiempo similar si el usuario no existe
    return False, name


def user_home(name):
    home = os.path.join(BASE, "home", name)
    for sub in ("Musica", "Proyectos", "Documentos"):
        os.makedirs(os.path.join(home, sub), exist_ok=True)
    demo = os.path.join(home, "Proyectos", "hola.py")
    if not os.path.exists(demo):
        with open(demo, "w", encoding="utf-8") as f:
            f.write('# Mi primer programa en SpOS2\n'
                    'nombre = "SpOS2"\n\n'
                    'def saludo(n):\n'
                    '    return "Hola desde " + n\n\n'
                    'for i in range(3):\n'
                    '    print(i, saludo(nombre))\n')
    return home


# ------------------------------------------------------------------ archivos
def list_dir(path):
    try:
        names = os.listdir(path)
    except OSError:
        return None
    out = []
    for n in names:
        if n.startswith("."):
            continue
        p = os.path.join(path, n)
        isdir = os.path.isdir(p)
        try:
            size = 0 if isdir else os.path.getsize(p)
        except OSError:
            size = 0
        out.append((n, isdir, size))
    out.sort(key=lambda e: (not e[1], e[0].lower()))
    return out


def human_size(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return ("%d %s" % (n, u)) if u == "B" else ("%.1f %s" % (n, u))
        n /= 1024.0


def fmt_time(sec):
    sec = int(max(0, sec))
    return "%d:%02d" % (sec // 60, sec % 60)


# ------------------------------------------------------------------ WiFi
DEMO_NETS = [("SpOS2_Lab", 92, "WPA2"), ("Casa_Fibra", 74, "WPA2"), ("Cafe_Libre", 58, ""),
             ("Vecino_5G", 41, "WPA3"), ("HotSpot_Movil", 33, "WPA2")]


def _split_terse(line):
    parts = re.split(r"(?<!\\):", line)
    return [p.replace("\\:", ":").replace("\\\\", "\\") for p in parts]


def parse_nmcli_list(text):
    """Parsea 'nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY dev wifi list' -> (redes, ssid_actual)."""
    best, current = {}, None
    for line in text.splitlines():
        f = _split_terse(line)
        if len(f) < 4:
            continue
        inuse, ssid, sig, sec = f[0], f[1], f[2], f[3]
        if not ssid:
            continue
        try:
            sig = int(sig)
        except ValueError:
            sig = 0
        if inuse.strip() == "*":
            current = ssid
        if ssid not in best or sig > best[ssid][1]:
            best[ssid] = (ssid, sig, sec.strip() if sec.strip() != "--" else "")
    nets = sorted(best.values(), key=lambda n: -n[1])
    return nets, current


def _run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 127, "", str(e)


class WifiService:
    def __init__(self):
        self.networks, self.current = [], None
        self.busy, self.message, self.ok = False, "", True
        self.demo = True
        self.nmcli = shutil.which("nmcli")
        if self.nmcli:
            rc, out, _ = _run([self.nmcli, "-t", "-f", "TYPE", "dev"], 5)
            self.demo = not (rc == 0 and "wifi" in out)
        if self.demo:
            self.networks = list(DEMO_NETS)

    def _start(self, fn, *a):
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._wrap, args=(fn,) + a, daemon=True).start()

    def _wrap(self, fn, *a):
        try:
            fn(*a)
        finally:
            self.busy = False

    def refresh(self):
        self._start(self._scan)

    def _scan(self):
        self.message, self.ok = "Buscando redes...", True
        if self.demo:
            time.sleep(0.8)
            self.networks = list(DEMO_NETS)
        else:
            rc, out, err = _run([self.nmcli, "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY",
                                 "dev", "wifi", "list", "--rescan", "yes"], 25)
            if rc != 0:
                self.message, self.ok = "Error: " + (err.strip().splitlines() or ["sin datos"])[-1], False
                return
            self.networks, self.current = parse_nmcli_list(out)
        self.message = "%d redes encontradas" % len(self.networks)

    def connect(self, ssid, password=None):
        self._start(self._connect, ssid, password)

    def _connect(self, ssid, password):
        self.message, self.ok = "Conectando a %s..." % ssid, True
        if self.demo:
            time.sleep(1.6)
            sec = [n[2] for n in self.networks if n[0] == ssid]
            if sec and sec[0] and len(password or "") < 8:
                self.message, self.ok = "Clave incorrecta (demo: minimo 8 caracteres)", False
                return
            self.current = ssid
        else:
            cmd = [self.nmcli, "dev", "wifi", "connect", ssid]
            if password:
                cmd += ["password", password]
            rc, out, err = _run(cmd, 45)
            if rc != 0:
                last = (err.strip().splitlines() or ["no se pudo conectar"])[-1]
                self.message, self.ok = "Error: " + last, False
                return
            self.current = ssid
        self.message, self.ok = "Conectado a %s" % ssid, True

    def disconnect(self):
        self._start(self._disconnect)

    def _disconnect(self):
        if self.current and not self.demo:
            _run([self.nmcli, "connection", "down", "id", self.current], 15)
        self.message, self.ok = "Desconectado", True
        self.current = None


# ------------------------------------------------------------------ Python
def run_script_main(path):
    """Modo --run-script: ejecuta un .py en este proceso (usado por el IDE y la terminal)."""
    import runpy, traceback
    path = os.path.abspath(path)
    sys.argv = [path]
    sys.path.insert(0, os.path.dirname(path))
    try:
        runpy.run_path(path, run_name="__main__")
    except SystemExit as e:
        sys.exit(e.code)
    except BaseException as e:
        tb = e.__traceback__
        while tb and tb.tb_frame.f_code.co_filename != path:
            tb = tb.tb_next
        traceback.print_exception(type(e), e, tb if tb else e.__traceback__)
        sys.exit(1)


class ScriptRunner:
    def __init__(self, path):
        self.path, self.q, self.proc = path, queue.Queue(), None
        self.finished, self.returncode, self.t0 = False, None, time.time()

    def start(self):
        if FROZEN:
            cmd = [sys.executable, "--run-script", self.path]
        else:
            cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py"),
                   "--run-script", self.path]
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, cwd=os.path.dirname(self.path) or None,
                                     text=True, errors="replace", bufsize=1, env=env)
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        try:
            for line in self.proc.stdout:
                self.q.put(line.rstrip("\r\n"))
        finally:
            self.returncode = self.proc.wait()
            self.finished = True

    def drain(self):
        out = []
        while True:
            try:
                out.append(self.q.get_nowait())
            except queue.Empty:
                return out

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()


class PyRepl:
    """Consola interactiva de Python dentro de la terminal."""
    def __init__(self):
        self.ns = {"__name__": "__console__"}
        self.interp = code.InteractiveInterpreter(self.ns)
        self.buf = []

    def push(self, line):
        self.buf.append(line)
        out, old = io.StringIO(), (sys.stdout, sys.stderr)
        sys.stdout = sys.stderr = out
        try:
            more = self.interp.runsource("\n".join(self.buf), "<spos2>")
        except BaseException as e:  # SystemExit etc.
            more = False
            out.write("%s\n" % e)
        finally:
            sys.stdout, sys.stderr = old
        if not more:
            self.buf = []
        return out.getvalue(), more


_BUILTINS = set(dir(builtins))
_TOK = re.compile(r"""(?P<comment>\#.*)|(?P<string>"(?:\\.|[^"\\])*"?|'(?:\\.|[^'\\])*'?)"""
                  r"""|(?P<number>\b\d+(?:\.\d+)?\b)|(?P<word>[A-Za-z_]\w*)""")


def highlight(line):
    """Devuelve [(texto, tipo)] con tipo: plain/comment/string/number/keyword/builtin/def."""
    out, pos, prev = [], 0, ""
    for m in _TOK.finditer(line):
        if m.start() > pos:
            out.append((line[pos:m.start()], "plain"))
        kind, txt = m.lastgroup, m.group()
        if kind == "word":
            if txt in keyword.kwlist:
                kind = "keyword"
            elif prev in ("def", "class"):
                kind = "def"
            elif txt in _BUILTINS:
                kind = "builtin"
            else:
                kind = "plain"
            prev = txt
        out.append((txt, kind))
        pos = m.end()
    if pos < len(line):
        out.append((line[pos:], "plain"))
    return out


# ------------------------------------------------------------------ audio sintetizado
_N = {"C3": 130.81, "G3": 196.0, "A3": 220.0, "B3": 246.94, "C4": 261.63, "D4": 293.66, "E4": 329.63,
      "F3": 174.61, "F4": 349.23, "G4": 392.0, "A4": 440.0, "C5": 523.25, "E5": 659.25, "G5": 783.99}


def synth_wav(path, notes, rate=22050, vol=0.35):
    data = array("h")
    for freq, ms in notes:
        n = int(rate * ms / 1000.0)
        for i in range(n):
            if freq <= 0:
                data.append(0)
                continue
            t = i / rate
            env = min(1.0, i / (0.01 * rate)) * math.exp(-2.2 * t / (ms / 1000.0)) if ms < 500 else \
                min(1.0, i / (0.01 * rate)) * min(1.0, (n - i) / (0.06 * rate))
            s = math.sin(2 * math.pi * freq * t) + 0.35 * math.sin(4 * math.pi * freq * t) \
                + 0.12 * math.sin(6 * math.pi * freq * t)
            data.append(int(32767 * vol * env * s / 1.47))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def ensure_assets():
    """Crea (si faltan) los sonidos y canciones de SpOS2. Devuelve dict nombre->ruta."""
    ensure_dirs()
    q = 300
    ode = [("E4", q), ("E4", q), ("F4", q), ("G4", q), ("G4", q), ("F4", q), ("E4", q), ("D4", q),
           ("C4", q), ("C4", q), ("D4", q), ("E4", q), ("E4", q * 3 // 2), ("D4", q // 2), ("D4", q * 2),
           ("E4", q), ("E4", q), ("F4", q), ("G4", q), ("G4", q), ("F4", q), ("E4", q), ("D4", q),
           ("C4", q), ("C4", q), ("D4", q), ("E4", q), ("D4", q * 3 // 2), ("C4", q // 2), ("C4", q * 2)]
    chords = [("A3", "C4", "E4"), ("F3", "A3", "C4"), ("C4", "E4", "G4"), ("G3", "B3", "D4")]
    theme = []
    for _ in range(2):
        for a, b, c in chords:
            for n in (a, b, c, b, a, b, c, b):
                theme.append((n, 230))
    chime = [("C5", 110), ("E5", 110), ("G5", 260)]
    items = {"chime": (chime, 0.4), "ode": (ode, 0.35), "theme": (theme, 0.35)}
    paths = {}
    for key, (notes, vol) in items.items():
        p = os.path.join(CACHE, key + ".wav")
        if not os.path.exists(p):
            synth_wav(p, [(_N.get(n, 0), ms) for n, ms in notes], vol=vol)
        paths[key] = p
    return paths


TITLES = {"chime": "Inicio SpOS2", "ode": "Oda a la Alegria (SpOS2)", "theme": "SpOS2 Theme"}
