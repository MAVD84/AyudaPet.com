import hmac
import logging
import os
import re
import secrets
import time
import uuid
from functools import wraps

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from jinja2 import DictLoader
from werkzeug.security import check_password_hash, generate_password_hash


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", "16777216"))

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
SHOW_OTP_IN_DEV = os.getenv("SHOW_OTP_IN_DEV", "").lower() in {"1", "true", "yes"}
OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))

PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")
MX_PHONE_RE = re.compile(r"^[2-9][0-9]{9}$")


class AppError(RuntimeError):
    pass


class ConfigError(AppError):
    pass


class DatabaseError(AppError):
    pass


def require_config():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ConfigError("Faltan SUPABASE_URL y/o SUPABASE_SERVICE_ROLE_KEY.")


def supabase_headers(prefer="return=representation"):
    require_config()
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def db_request(table, method="GET", payload=None, params=None, prefer="return=representation"):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        response = requests.request(
            method,
            url,
            json=payload,
            params=params,
            headers=supabase_headers(prefer),
            timeout=12,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) else ""
        logger.exception("Supabase request failed: %s", detail)
        raise DatabaseError("No se pudo completar la operacion en la base de datos.") from exc

    if response.status_code == 204 or not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:
        raise DatabaseError("Supabase respondio con un formato inesperado.") from exc


def select_rows(table, params=None):
    rows = db_request(table, params=params or {})
    return rows if isinstance(rows, list) else []


def upsert_row(table, payload, on_conflict):
    params = {"on_conflict": on_conflict}
    prefer = "resolution=merge-duplicates,return=representation"
    rows = db_request(table, method="POST", payload=payload, params=params, prefer=prefer)
    return rows[0] if isinstance(rows, list) and rows else None


def delete_rows(table, params):
    return db_request(table, method="DELETE", params=params, prefer="return=minimal")


def normalize_phone(raw_phone):
    phone = re.sub(r"\D", "", raw_phone or "")
    if phone.startswith("52") and len(phone) == 12:
        phone = phone[2:]
    if not MX_PHONE_RE.match(phone):
        return None
    return phone


def phone_for_sms(phone):
    digits = re.sub(r"\D", "", phone or "")
    default_country = os.getenv("LABSMOBILE_DEFAULT_COUNTRY_CODE", "52")
    if len(digits) == 10 and default_country:
        digits = f"{default_country}{digits}"
    return digits


def current_user_phone():
    return session.get("tel")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user_phone():
            flash("Inicia sesion para continuar.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def send_sms(phone, code):
    api_url = os.getenv("LABSMOBILE_API")
    user = os.getenv("LABSMOBILE_USER")
    token = os.getenv("LABSMOBILE_TOKEN")
    sender = os.getenv("LABSMOBILE_SENDER", "UBICANID")

    if not all([api_url, user, token]):
        logger.warning("SMS no enviado: faltan variables de LabsMobile.")
        return False

    sms_phone = phone_for_sms(phone)
    if not sms_phone:
        logger.warning("SMS no enviado: telefono invalido para LabsMobile.")
        return False

    payload = {
        "message": f"Tu codigo UBICAN ID es {code}. Expira en 5 minutos.",
        "tpoa": sender,
        "recipient": [{"msisdn": sms_phone}],
    }
    try:
        response = requests.post(api_url, json=payload, auth=(user, token), timeout=12)
        response.raise_for_status()
        result = response.json() if response.content else {}
        provider_code = str(result.get("code", ""))
        if provider_code and provider_code not in {"0", "200", "201"}:
            logger.error("LabsMobile rechazo el SMS a %s. Respuesta: %s", sms_phone, response.text[:500])
            return False
        logger.info("SMS enviado a %s via LabsMobile. Respuesta: %s", sms_phone, response.text[:500])
        return True
    except ValueError:
        logger.exception("LabsMobile respondio con JSON invalido: %s", response.text[:500])
        return False
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) else ""
        logger.exception("No se pudo enviar el SMS. Respuesta LabsMobile: %s", detail)
        return False


def create_otp(phone):
    code = f"{secrets.randbelow(1_000_000):06d}"
    upsert_row(
        "otps",
        {"telefono": phone, "code": code, "expires": time.time() + OTP_TTL_SECONDS},
        "telefono",
    )
    sent = send_sms(phone, code)
    dev_code = code if SHOW_OTP_IN_DEV else None
    return sent, dev_code


def verify_otp(phone, code):
    rows = select_rows(
        "otps",
        {
            "telefono": f"eq.{phone}",
            "select": "telefono,code,expires",
            "limit": "1",
        },
    )
    if not rows:
        return False

    otp = rows[0]
    expires = float(otp.get("expires") or 0)
    is_valid = expires >= time.time() and hmac.compare_digest(str(otp.get("code")), str(code or ""))
    if is_valid:
        delete_rows("otps", {"telefono": f"eq.{phone}"})
    return is_valid


def get_user(phone):
    rows = select_rows(
        "usuarios",
        {
            "telefono": f"eq.{phone}",
            "select": "telefono,password_hash,nombre,foto,activo",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


def save_user(phone, password, nombre=None):
    payload = {
        "telefono": phone,
        "creado": int(time.time()),
        "password_hash": generate_password_hash(password),
        "nombre": nombre,
        "activo": True,
    }
    return upsert_row("usuarios", payload, "telefono")


def list_mascotas():
    return select_rows(
        "mascotas",
        {
            "select": "*",
            "order": "creado_at.desc",
            "limit": "80",
        },
    )


def get_form_value(name):
    value = request.form.get(name)
    return value.strip() if isinstance(value, str) and value.strip() else None


def create_report():
    required_name = get_form_value("nombre")
    if not required_name:
        raise AppError("El nombre de la mascota es obligatorio.")

    payload = {
        "id": uuid.uuid4().hex,
        "reportado_por": current_user_phone(),
        "nombre": required_name,
        "descripcion": get_form_value("descripcion"),
        "zona": get_form_value("zona"),
        "contacto": get_form_value("contacto"),
        "principal": get_form_value("principal"),
        "secundarias": [item for item in request.form.getlist("secundarias") if item],
        "fecha": get_form_value("fecha"),
        "edad": get_form_value("edad"),
        "raza": get_form_value("raza"),
        "genero": get_form_value("genero"),
        "color": get_form_value("color"),
        "collar": get_form_value("collar"),
        "docil": get_form_value("docil"),
        "direccion": get_form_value("direccion"),
        "ciudad": get_form_value("ciudad"),
        "estado": get_form_value("estado"),
        "cp": get_form_value("cp"),
        "calles": get_form_value("calles"),
        "dueno": get_form_value("dueno"),
        "recompensa": get_form_value("recompensa"),
    }
    rows = db_request("mascotas", method="POST", payload=payload)
    return rows[0] if isinstance(rows, list) and rows else None


@app.context_processor
def inject_globals():
    return {
        "current_user": current_user_phone(),
        "year": time.localtime().tm_year,
    }


@app.errorhandler(ConfigError)
def handle_config_error(error):
    return render_template("error.html", title="Configuracion incompleta", message=str(error)), 500


@app.errorhandler(DatabaseError)
def handle_database_error(error):
    return render_template("error.html", title="Base de datos no disponible", message=str(error)), 502


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", title="Pagina no encontrada", message="La ruta solicitada no existe."), 404


@app.route("/")
def index():
    mascotas = list_mascotas()
    stats = {
        "total": len(mascotas),
        "activos": len([m for m in mascotas if not m.get("encontrado")]),
        "encontrados": len([m for m in mascotas if m.get("encontrado")]),
    }
    return render_template("index.html", mascotas=mascotas, stats=stats)


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        phone = normalize_phone(request.form.get("tel"))
        if not phone:
            flash("Ingresa un numero celular mexicano valido de 10 digitos.", "error")
            return redirect(url_for("registro"))

        sent, dev_code = create_otp(phone)
        session["pending_tel"] = phone
        if dev_code:
            flash(f"Codigo de prueba: {dev_code}", "info")
        elif sent:
            flash("Te enviamos un codigo por SMS.", "success")
        else:
            flash("No se pudo enviar el SMS. Revisa los logs de Coolify para ver la respuesta de LabsMobile.", "error")
            return redirect(url_for("registro"))
        return redirect(url_for("verificar"))

    return render_template("registro.html")


@app.route("/verificar", methods=["GET", "POST"])
def verificar():
    pending_tel = session.get("pending_tel")
    if not pending_tel:
        flash("Primero registra tu telefono.", "warning")
        return redirect(url_for("registro"))

    if request.method == "POST":
        code = request.form.get("code")
        if verify_otp(pending_tel, code):
            session["verified_tel"] = pending_tel
            flash("Telefono verificado. Crea tu contrasena.", "success")
            return redirect(url_for("set_password"))
        flash("Codigo invalido o expirado.", "error")

    return render_template("verificar.html", phone=pending_tel)


@app.route("/set_password", methods=["GET", "POST"])
def set_password():
    verified_tel = session.get("verified_tel")
    if not verified_tel:
        flash("Verifica tu telefono antes de crear la cuenta.", "warning")
        return redirect(url_for("registro"))

    if request.method == "POST":
        password = request.form.get("pwd") or ""
        nombre = get_form_value("nombre")
        if len(password) < 8:
            flash("La contrasena debe tener al menos 8 caracteres.", "error")
            return redirect(url_for("set_password"))

        save_user(verified_tel, password, nombre)
        session.pop("pending_tel", None)
        session.pop("verified_tel", None)
        session["tel"] = verified_tel
        flash("Cuenta lista. Ya puedes publicar reportes.", "success")
        return redirect(url_for("reportar"))

    return render_template("set_password.html", phone=verified_tel)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = normalize_phone(request.form.get("tel"))
        password = request.form.get("pwd") or ""
        user = get_user(phone) if phone else None
        if user and user.get("activo") and check_password_hash(user.get("password_hash", ""), password):
            session.clear()
            session["tel"] = phone
            flash("Sesion iniciada.", "success")
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)
        flash("Telefono mexicano o contrasena incorrectos.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesion cerrada.", "info")
    return redirect(url_for("index"))


@app.route("/reportar", methods=["GET", "POST"])
@login_required
def reportar():
    if request.method == "POST":
        try:
            create_report()
        except AppError as exc:
            flash(str(exc), "error")
            return redirect(url_for("reportar"))
        flash("Reporte publicado correctamente.", "success")
        return redirect(url_for("index"))

    return render_template("reportar.html")


TEMPLATES = {
    "base.html": """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title or "UBICAN ID" }}</title>
  <style>
    :root {
      --ink: #18212f;
      --muted: #617084;
      --line: #dfe7ef;
      --paper: #ffffff;
      --wash: #f5f7fb;
      --brand: #e85035;
      --brand-dark: #b93824;
      --blue: #176b87;
      --green: #287c5a;
      --amber: #a46614;
      --shadow: 0 18px 48px rgba(20, 32, 48, .10);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--wash);
    }
    a { color: inherit; text-decoration: none; }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 10;
      background: rgba(255,255,255,.94);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(14px);
    }
    .nav {
      max-width: 1180px;
      margin: 0 auto;
      min-height: 70px;
      padding: 0 22px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }
    .brand { display: flex; align-items: center; gap: 12px; font-weight: 900; letter-spacing: .02em; }
    .mark {
      width: 38px;
      height: 38px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      color: #fff;
      background: var(--brand);
      font-weight: 900;
      box-shadow: 0 10px 24px rgba(232,80,53,.25);
    }
    .navlinks { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
    .shell { max-width: 1180px; margin: 0 auto; padding: 28px 22px 48px; }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(260px, .85fr);
      gap: 26px;
      align-items: stretch;
      margin-bottom: 24px;
    }
    .hero-main {
      min-height: 300px;
      padding: clamp(26px, 5vw, 54px);
      border-radius: 8px;
      color: #fff;
      background:
        linear-gradient(110deg, rgba(24,33,47,.94), rgba(23,107,135,.82)),
        url("https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=1600&q=80");
      background-size: cover;
      background-position: center;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
    }
    .eyebrow { margin: 0 0 12px; font-weight: 800; color: #ffd9c7; text-transform: uppercase; font-size: .78rem; }
    h1 { margin: 0; font-size: clamp(2rem, 5vw, 4.3rem); line-height: 1; letter-spacing: 0; }
    .hero-main p { max-width: 650px; color: rgba(255,255,255,.88); font-size: 1.08rem; line-height: 1.6; margin: 18px 0 0; }
    .panel, .pet-card, .form-panel {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 34px rgba(20,32,48,.06);
    }
    .panel { padding: 22px; }
    .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 18px; }
    .stat { padding: 16px; border: 1px solid var(--line); border-radius: 8px; background: #fbfdff; }
    .stat strong { display: block; font-size: 1.8rem; }
    .stat span { color: var(--muted); font-size: .9rem; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 22px; }
    .btn {
      border: 0;
      border-radius: 8px;
      min-height: 42px;
      padding: 0 16px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-weight: 800;
      cursor: pointer;
      background: #e8edf3;
      color: var(--ink);
    }
    .btn.primary { color: #fff; background: var(--brand); }
    .btn.primary:hover { background: var(--brand-dark); }
    .btn.ghost { background: transparent; border: 1px solid var(--line); }
    .section-head {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 18px;
      margin: 26px 0 14px;
    }
    .section-head h2 { margin: 0; font-size: 1.35rem; }
    .section-head p { margin: 5px 0 0; color: var(--muted); }
    .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
    .pet-card { overflow: hidden; }
    .pet-media {
      height: 150px;
      background:
        linear-gradient(135deg, rgba(232,80,53,.20), rgba(23,107,135,.20)),
        #edf3f7;
      display: grid;
      place-items: center;
      font-size: 2rem;
      font-weight: 900;
      color: var(--blue);
    }
    .pet-body { padding: 16px; }
    .pet-body h3 { margin: 0 0 8px; font-size: 1.1rem; }
    .meta { color: var(--muted); line-height: 1.45; font-size: .95rem; }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 0 10px;
      border-radius: 999px;
      background: #eef5f7;
      color: var(--blue);
      font-weight: 800;
      font-size: .78rem;
    }
    .badge.found { background: #e9f7f0; color: var(--green); }
    .form-wrap { max-width: 900px; margin: 0 auto; }
    .form-panel { padding: clamp(20px, 4vw, 34px); }
    .form-panel h1 { color: var(--ink); font-size: clamp(1.8rem, 4vw, 2.7rem); }
    .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 20px; }
    .field { display: grid; gap: 7px; }
    .field.full { grid-column: 1 / -1; }
    label { font-weight: 800; font-size: .92rem; }
    .hint { color: var(--muted); font-size: .84rem; line-height: 1.4; }
    input, textarea, select {
      width: 100%;
      border: 1px solid #cfd9e4;
      border-radius: 8px;
      min-height: 44px;
      padding: 10px 12px;
      background: #fff;
      color: var(--ink);
      font: inherit;
    }
    textarea { min-height: 118px; resize: vertical; }
    input:focus, textarea:focus, select:focus {
      outline: 3px solid rgba(23,107,135,.16);
      border-color: var(--blue);
    }
    .checks { display: flex; flex-wrap: wrap; gap: 10px; }
    .check {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
      font-weight: 700;
    }
    .check input { width: auto; min-height: auto; }
    .flash-stack { display: grid; gap: 10px; margin-bottom: 18px; }
    .flash {
      border-radius: 8px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      background: #fff;
      font-weight: 700;
    }
    .flash.success { border-color: #bde5d0; background: #effaf4; color: var(--green); }
    .flash.error { border-color: #f1b8aa; background: #fff2ef; color: var(--brand-dark); }
    .flash.warning { border-color: #edd398; background: #fff8e8; color: var(--amber); }
    .flash.info { border-color: #b8d8e5; background: #edf8fc; color: var(--blue); }
    .empty {
      padding: 34px;
      text-align: center;
      color: var(--muted);
      border: 1px dashed #c6d2de;
      border-radius: 8px;
      background: #fff;
    }
    footer { color: var(--muted); text-align: center; padding: 20px; }
    @media (max-width: 840px) {
      .hero, .grid, .form-grid { grid-template-columns: 1fr; }
      .stats { grid-template-columns: 1fr; }
      .nav { align-items: flex-start; flex-direction: column; padding: 16px 22px; }
      .navlinks { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <nav class="nav">
      <a class="brand" href="{{ url_for('index') }}"><span class="mark">U</span><span>UBICAN ID</span></a>
      <div class="navlinks">
        <a class="btn ghost" href="{{ url_for('index') }}">Reportes</a>
        {% if current_user %}
          <a class="btn primary" href="{{ url_for('reportar') }}">Reportar</a>
          <a class="btn ghost" href="{{ url_for('logout') }}">Salir</a>
        {% else %}
          <a class="btn ghost" href="{{ url_for('login') }}">Entrar</a>
          <a class="btn primary" href="{{ url_for('registro') }}">Crear cuenta</a>
        {% endif %}
      </div>
    </nav>
  </header>
  <main class="shell">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <div class="flash-stack">
          {% for category, message in messages %}
            <div class="flash {{ category }}">{{ message }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>
  <footer>UBICAN ID &copy; {{ year }}</footer>
  <script>
    function formatLocalPhone(value) {
      const digits = value.replace(/\\D/g, "").slice(0, 10);
      if (digits.length <= 3) return digits;
      if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
      return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
    }

    document.querySelectorAll("[data-phone-input]").forEach((input) => {
      input.addEventListener("input", () => {
        input.value = formatLocalPhone(input.value);
      });
      input.form?.addEventListener("submit", () => {
        input.value = input.value.replace(/\\D/g, "").slice(0, 10);
      });
    });
  </script>
</body>
</html>
""",
    "index.html": """
{% extends "base.html" %}
{% block content %}
  <section class="hero">
    <div class="hero-main">
      <p class="eyebrow">Red de reportes comunitarios</p>
      <h1>Mascotas perdidas y encontradas</h1>
      <p>Publica reportes completos, concentra datos de contacto y ayuda a que cada mascota vuelva a casa mas rapido.</p>
      <div class="actions">
        <a class="btn primary" href="{{ url_for('reportar') }}">Crear reporte</a>
        <a class="btn" href="{{ url_for('registro') }}">Unirme</a>
      </div>
    </div>
    <aside class="panel">
      <span class="badge">Panel activo</span>
      <div class="stats">
        <div class="stat"><strong>{{ stats.total }}</strong><span>reportes</span></div>
        <div class="stat"><strong>{{ stats.activos }}</strong><span>activos</span></div>
        <div class="stat"><strong>{{ stats.encontrados }}</strong><span>resueltos</span></div>
      </div>
      <p class="meta" style="margin-top:18px;">Los reportes mas recientes aparecen primero para facilitar busquedas por zona, ciudad y contacto.</p>
    </aside>
  </section>

  <div class="section-head">
    <div>
      <h2>Reportes recientes</h2>
      <p>Informacion publica enviada por la comunidad.</p>
    </div>
  </div>

  {% if mascotas %}
    <section class="grid">
      {% for pet in mascotas %}
        <article class="pet-card">
          <div class="pet-media">{{ (pet.nombre or "?")[:1].upper() }}</div>
          <div class="pet-body">
            <span class="badge {% if pet.encontrado %}found{% endif %}">{{ "Encontrado" if pet.encontrado else "En busqueda" }}</span>
            <h3>{{ pet.nombre }}</h3>
            <p class="meta">
              {% if pet.zona %}<strong>Zona:</strong> {{ pet.zona }}<br>{% endif %}
              {% if pet.ciudad or pet.estado %}<strong>Ubicacion:</strong> {{ pet.ciudad or "" }}{% if pet.ciudad and pet.estado %}, {% endif %}{{ pet.estado or "" }}<br>{% endif %}
              {% if pet.contacto %}<strong>Contacto:</strong> {{ pet.contacto }}{% endif %}
            </p>
            {% if pet.descripcion %}<p>{{ pet.descripcion }}</p>{% endif %}
          </div>
        </article>
      {% endfor %}
    </section>
  {% else %}
    <div class="empty">Todavia no hay reportes publicados.</div>
  {% endif %}
{% endblock %}
""",
    "registro.html": """
{% extends "base.html" %}
{% block content %}
  <section class="form-wrap">
    <form class="form-panel" method="post">
      <p class="eyebrow" style="color: var(--brand);">Registro seguro</p>
      <h1>Crea tu cuenta</h1>
      <p class="meta">Solo aceptamos numeros mexicanos de 10 digitos. No uses prefijo de Estados Unidos.</p>
      <div class="form-grid">
        <div class="field full">
          <label for="tel">Telefono mexicano</label>
          <input id="tel" name="tel" inputmode="numeric" autocomplete="tel" placeholder="(656) 778-7712" maxlength="14" pattern="\\(?[0-9]{3}\\)?[\\s-]?[0-9]{3}-?[0-9]{4}" data-phone-input required>
          <span class="hint">Ejemplo: (656) 778-7712. Se enviara como numero mexicano +52.</span>
        </div>
      </div>
      <div class="actions"><button class="btn primary" type="submit">Enviar codigo</button></div>
    </form>
  </section>
{% endblock %}
""",
    "verificar.html": """
{% extends "base.html" %}
{% block content %}
  <section class="form-wrap">
    <form class="form-panel" method="post">
      <p class="eyebrow" style="color: var(--brand);">Verificacion</p>
      <h1>Confirma tu telefono</h1>
      <p class="meta">Enviamos un codigo a {{ phone }}. Expira en pocos minutos.</p>
      <div class="form-grid">
        <div class="field full">
          <label for="code">Codigo</label>
          <input id="code" name="code" inputmode="numeric" maxlength="6" placeholder="000000" required>
        </div>
      </div>
      <div class="actions"><button class="btn primary" type="submit">Verificar</button></div>
    </form>
  </section>
{% endblock %}
""",
    "set_password.html": """
{% extends "base.html" %}
{% block content %}
  <section class="form-wrap">
    <form class="form-panel" method="post">
      <p class="eyebrow" style="color: var(--brand);">Cuenta</p>
      <h1>Protege tu acceso</h1>
      <p class="meta">Telefono verificado: {{ phone }}</p>
      <div class="form-grid">
        <div class="field">
          <label for="nombre">Nombre</label>
          <input id="nombre" name="nombre" autocomplete="name" placeholder="Tu nombre">
        </div>
        <div class="field">
          <label for="pwd">Contrasena</label>
          <input id="pwd" name="pwd" type="password" autocomplete="new-password" minlength="8" required>
        </div>
      </div>
      <div class="actions"><button class="btn primary" type="submit">Guardar cuenta</button></div>
    </form>
  </section>
{% endblock %}
""",
    "login.html": """
{% extends "base.html" %}
{% block content %}
  <section class="form-wrap">
    <form class="form-panel" method="post">
      <p class="eyebrow" style="color: var(--brand);">Acceso</p>
      <h1>Entra a UBICAN ID</h1>
      <div class="form-grid">
        <div class="field">
          <label for="tel">Telefono mexicano</label>
          <input id="tel" name="tel" inputmode="numeric" autocomplete="tel" placeholder="(656) 778-7712" maxlength="14" pattern="\\(?[0-9]{3}\\)?[\\s-]?[0-9]{3}-?[0-9]{4}" data-phone-input required>
          <span class="hint">Usa el numero mexicano registrado, sin +1.</span>
        </div>
        <div class="field">
          <label for="pwd">Contrasena</label>
          <input id="pwd" name="pwd" type="password" autocomplete="current-password" required>
        </div>
      </div>
      <div class="actions">
        <button class="btn primary" type="submit">Entrar</button>
        <a class="btn" href="{{ url_for('registro') }}">Crear cuenta</a>
      </div>
    </form>
  </section>
{% endblock %}
""",
    "reportar.html": """
{% extends "base.html" %}
{% block content %}
  <section class="form-wrap">
    <form class="form-panel" method="post">
      <p class="eyebrow" style="color: var(--brand);">Nuevo reporte</p>
      <h1>Datos de la mascota</h1>
      <div class="form-grid">
        <div class="field">
          <label for="nombre">Nombre o identificador</label>
          <input id="nombre" name="nombre" required>
        </div>
        <div class="field">
          <label for="contacto">Contacto publico</label>
          <input id="contacto" name="contacto" placeholder="Telefono, WhatsApp o correo">
        </div>
        <div class="field full">
          <label for="descripcion">Descripcion</label>
          <textarea id="descripcion" name="descripcion" placeholder="Senales particulares, temperamento, ultima vez visto"></textarea>
        </div>
        <div class="field"><label for="zona">Zona</label><input id="zona" name="zona"></div>
        <div class="field"><label for="fecha">Fecha</label><input id="fecha" name="fecha" type="date"></div>
        <div class="field"><label for="edad">Edad</label><input id="edad" name="edad"></div>
        <div class="field"><label for="raza">Raza</label><input id="raza" name="raza"></div>
        <div class="field"><label for="genero">Genero</label><select id="genero" name="genero"><option value="">Seleccionar</option><option>Macho</option><option>Hembra</option><option>No se sabe</option></select></div>
        <div class="field"><label for="color">Color</label><input id="color" name="color"></div>
        <div class="field"><label for="collar">Collar</label><input id="collar" name="collar"></div>
        <div class="field"><label for="docil">Comportamiento</label><input id="docil" name="docil" placeholder="Docil, nervioso, asustado"></div>
        <div class="field"><label for="principal">Foto principal</label><input id="principal" name="principal" placeholder="URL de imagen"></div>
        <div class="field full">
          <label>Fotos secundarias</label>
          <div class="checks">
            <input name="secundarias" placeholder="URL secundaria 1">
            <input name="secundarias" placeholder="URL secundaria 2">
          </div>
        </div>
        <div class="field full"><label for="direccion">Direccion o referencia</label><input id="direccion" name="direccion"></div>
        <div class="field"><label for="ciudad">Ciudad</label><input id="ciudad" name="ciudad"></div>
        <div class="field"><label for="estado">Estado</label><input id="estado" name="estado"></div>
        <div class="field"><label for="cp">Codigo postal</label><input id="cp" name="cp" inputmode="numeric"></div>
        <div class="field"><label for="calles">Entre calles</label><input id="calles" name="calles"></div>
        <div class="field"><label for="dueno">Dueno</label><input id="dueno" name="dueno"></div>
        <div class="field"><label for="recompensa">Recompensa</label><input id="recompensa" name="recompensa"></div>
      </div>
      <div class="actions"><button class="btn primary" type="submit">Publicar reporte</button></div>
    </form>
  </section>
{% endblock %}
""",
    "error.html": """
{% extends "base.html" %}
{% block content %}
  <section class="form-wrap">
    <div class="form-panel">
      <p class="eyebrow" style="color: var(--brand);">Aviso</p>
      <h1>{{ title }}</h1>
      <p class="meta">{{ message }}</p>
      <div class="actions"><a class="btn primary" href="{{ url_for('index') }}">Volver al inicio</a></div>
    </div>
  </section>
{% endblock %}
""",
}

app.jinja_loader = DictLoader(TEMPLATES)


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=int(os.getenv("PORT", "5000")))
