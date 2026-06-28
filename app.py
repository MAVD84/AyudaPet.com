import hmac
import logging
import mimetypes
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
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "mascotas")
SHOW_OTP_IN_DEV = os.getenv("SHOW_OTP_IN_DEV", "").lower() in {"1", "true", "yes"}
OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))

PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")
MX_PHONE_RE = re.compile(r"^[2-9][0-9]{9}$")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


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


def storage_url(path):
    return f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{path}"


def public_storage_url(path):
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{path}"


def upload_image(file_storage, report_id, label):
    if not file_storage or not file_storage.filename:
        return None

    content_type = file_storage.mimetype or mimetypes.guess_type(file_storage.filename)[0]
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise AppError("Solo puedes subir imagenes JPG, PNG, WEBP o GIF.")

    extension = mimetypes.guess_extension(content_type) or ".jpg"
    path = f"reportes/{report_id}/{label}-{uuid.uuid4().hex}{extension}"
    headers = supabase_headers("return=minimal")
    headers["Content-Type"] = content_type
    headers["x-upsert"] = "true"

    try:
        response = requests.post(storage_url(path), data=file_storage.stream, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) else ""
        logger.exception("No se pudo subir imagen a Supabase Storage: %s", detail)
        raise AppError("No se pudo subir la imagen. Intenta de nuevo.") from exc

    return public_storage_url(path)


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


def phone_digits(raw_phone):
    digits = re.sub(r"\D", "", raw_phone or "")
    if len(digits) == 10:
        return digits
    if digits.startswith("52") and len(digits) == 12:
        return digits[2:]
    return digits


def whatsapp_digits(raw_phone):
    digits = phone_digits(raw_phone)
    return phone_for_sms(digits) if len(digits) == 10 else digits


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
    existing = get_user(phone)
    if existing:
        update_user_password(phone, password)
        if nombre:
            update_user_profile(phone, nombre=nombre)
        return get_user(phone)

    payload = {
        "telefono": phone,
        "password_hash": generate_password_hash(password),
        "activo": True,
        "creado": int(time.time()),
    }
    if nombre:
        payload["nombre"] = nombre
    return upsert_row("usuarios", payload, "telefono")


def update_user_profile(phone, nombre=None, foto=None):
    payload = {"nombre": nombre}
    if foto:
        payload["foto"] = foto
    rows = db_request(
        "usuarios",
        method="PATCH",
        payload=payload,
        params={"telefono": f"eq.{phone}"},
    )
    return rows[0] if isinstance(rows, list) and rows else None


def update_user_password(phone, password):
    rows = db_request(
        "usuarios",
        method="PATCH",
        payload={"password_hash": generate_password_hash(password)},
        params={"telefono": f"eq.{phone}"},
    )
    updated = rows[0] if isinstance(rows, list) and rows else None
    if not updated:
        raise AppError("No se pudo actualizar la contrasena.")
    return updated


def list_mascotas():
    return select_rows(
        "mascotas",
        {
            "select": "*",
            "order": "creado_at.desc",
            "limit": "80",
        },
    )


def list_user_reports(phone):
    return select_rows(
        "mascotas",
        {
            "reportado_por": f"eq.{phone}",
            "select": "*",
            "order": "creado_at.desc",
        },
    )


def get_mascota(report_id):
    rows = select_rows(
        "mascotas",
        {
            "id": f"eq.{report_id}",
            "select": "*",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


def get_form_value(name):
    value = request.form.get(name)
    return value.strip() if isinstance(value, str) and value.strip() else None


def get_checkbox_value(name):
    return request.form.get(name) == "on"


def report_payload(report_id, existing=None):
    required_name = get_form_value("nombre")
    if not required_name:
        raise AppError("El nombre de la mascota es obligatorio.")

    existing = existing or {}
    remove_principal = request.form.get("remove_principal") == "on"
    remove_secondary = set(request.form.getlist("remove_secundarias"))
    principal = None if remove_principal else existing.get("principal")
    principal = upload_image(request.files.get("principal"), report_id, "principal") or principal
    secundarias = [image for image in list(existing.get("secundarias") or []) if image not in remove_secondary]
    for index, image in enumerate(request.files.getlist("secundarias"), start=1):
        uploaded = upload_image(image, report_id, f"secundaria-{index}")
        if uploaded:
            secundarias.append(uploaded)

    return {
        "nombre": required_name,
        "descripcion": get_form_value("descripcion"),
        "contacto": get_form_value("contacto"),
        "principal": principal,
        "secundarias": secundarias,
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
        "encontrado": get_checkbox_value("encontrado"),
    }


def create_report():
    report_id = uuid.uuid4().hex
    payload = report_payload(report_id)
    payload["id"] = report_id
    payload["reportado_por"] = current_user_phone()
    rows = db_request("mascotas", method="POST", payload=payload)
    return rows[0] if isinstance(rows, list) and rows else None


def update_report(report_id, mascota):
    payload = report_payload(report_id, mascota)
    rows = db_request(
        "mascotas",
        method="PATCH",
        payload=payload,
        params={"id": f"eq.{report_id}", "reportado_por": f"eq.{current_user_phone()}"},
    )
    return rows[0] if isinstance(rows, list) and rows else None


def user_owns_report(mascota):
    return bool(mascota and current_user_phone() and mascota.get("reportado_por") == current_user_phone())


@app.context_processor
def inject_globals():
    def is_active(endpoint):
        return request.endpoint == endpoint

    return {
        "current_user": current_user_phone(),
        "year": time.localtime().tm_year,
        "phone_digits": phone_digits,
        "whatsapp_digits": whatsapp_digits,
        "is_active": is_active,
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


@app.route("/mascotas/<report_id>")
def detalle_mascota(report_id):
    mascota = get_mascota(report_id)
    if not mascota:
        return render_template("error.html", title="Reporte no encontrado", message="El reporte solicitado no existe."), 404
    return render_template("detalle.html", mascota=mascota, is_owner=user_owns_report(mascota))


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


@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        phone = normalize_phone(request.form.get("tel"))
        user = get_user(phone) if phone else None
        if not user:
            flash("No encontramos una cuenta con ese telefono.", "error")
            return redirect(url_for("recuperar"))

        sent, dev_code = create_otp(phone)
        session["pending_tel"] = phone
        if dev_code:
            flash(f"Codigo de prueba: {dev_code}", "info")
        elif sent:
            flash("Te enviamos un codigo por SMS.", "success")
        else:
            flash("No se pudo enviar el SMS. Revisa los logs de Coolify para ver la respuesta de LabsMobile.", "error")
            return redirect(url_for("recuperar"))
        return redirect(url_for("verificar"))

    return render_template("recuperar.html")


@app.route("/set_password", methods=["GET", "POST"])
def set_password():
    verified_tel = session.get("verified_tel")
    if not verified_tel:
        flash("Verifica tu telefono antes de crear la cuenta.", "warning")
        return redirect(url_for("registro"))

    existing_user = get_user(verified_tel)
    if request.method == "POST":
        password = request.form.get("pwd") or ""
        nombre = get_form_value("nombre") if not existing_user else None
        if len(password) < 8:
            flash("La contrasena debe tener al menos 8 caracteres.", "error")
            return redirect(url_for("set_password"))

        try:
            save_user(verified_tel, password, nombre)
        except AppError as exc:
            flash(str(exc), "error")
            return redirect(url_for("set_password"))
        session.pop("pending_tel", None)
        session.pop("verified_tel", None)
        if existing_user:
            session.clear()
            flash("Contrasena restablecida. Inicia sesion con tu nueva contrasena.", "success")
            return redirect(url_for("login"))
        session["tel"] = verified_tel
        flash("Cuenta lista. Ya puedes publicar reportes.", "success")
        return redirect(url_for("reportar"))

    return render_template("set_password.html", phone=verified_tel, recovering=bool(existing_user))


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


@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    phone = current_user_phone()
    user = get_user(phone)
    if not user:
        session.clear()
        flash("Tu sesion expiro. Inicia sesion de nuevo.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            foto = upload_image(request.files.get("foto"), phone, "perfil") if request.files.get("foto") else None
            update_user_profile(phone, nombre=get_form_value("nombre"), foto=foto)
        except AppError as exc:
            flash(str(exc), "error")
            return redirect(url_for("perfil"))
        flash("Perfil actualizado.", "success")
        return redirect(url_for("perfil"))

    reportes = list_user_reports(phone)
    return render_template("perfil.html", user=user, reportes=reportes)


@app.route("/perfil/password", methods=["POST"])
@login_required
def cambiar_password():
    phone = current_user_phone()
    user = get_user(phone)
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not user or not check_password_hash(user.get("password_hash", ""), current_password):
        flash("La contrasena actual no es correcta.", "error")
        return redirect(url_for("perfil"))
    if len(new_password) < 8:
        flash("La nueva contrasena debe tener al menos 8 caracteres.", "error")
        return redirect(url_for("perfil"))
    if new_password != confirm_password:
        flash("La confirmacion no coincide.", "error")
        return redirect(url_for("perfil"))

    try:
        update_user_password(phone, new_password)
    except AppError as exc:
        flash(str(exc), "error")
        return redirect(url_for("perfil"))
    session.clear()
    flash("Contrasena actualizada. Inicia sesion de nuevo.", "success")
    return redirect(url_for("login"))


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

    return render_template("reportar.html", mascota={}, editing=False)


@app.route("/mascotas/<report_id>/editar", methods=["GET", "POST"])
@login_required
def editar_mascota(report_id):
    mascota = get_mascota(report_id)
    if not mascota:
        return render_template("error.html", title="Reporte no encontrado", message="El reporte solicitado no existe."), 404
    if not user_owns_report(mascota):
        return render_template("error.html", title="Sin permiso", message="Solo puedes editar tus propios reportes."), 403

    if request.method == "POST":
        try:
            update_report(report_id, mascota)
        except AppError as exc:
            flash(str(exc), "error")
            return redirect(url_for("editar_mascota", report_id=report_id))
        flash("Reporte actualizado correctamente.", "success")
        return redirect(url_for("detalle_mascota", report_id=report_id))

    return render_template("reportar.html", mascota=mascota, editing=True)


@app.route("/mascotas/<report_id>/eliminar", methods=["POST"])
@login_required
def eliminar_mascota(report_id):
    mascota = get_mascota(report_id)
    if not mascota:
        return render_template("error.html", title="Reporte no encontrado", message="El reporte solicitado no existe."), 404
    if not user_owns_report(mascota):
        return render_template("error.html", title="Sin permiso", message="Solo puedes eliminar tus propios reportes."), 403

    delete_rows("mascotas", {"id": f"eq.{report_id}", "reportado_por": f"eq.{current_user_phone()}"})
    flash("Reporte eliminado.", "success")
    return redirect(url_for("index"))


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
      padding: 0 clamp(12px, 4vw, 22px);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      min-width: 0;
    }
    .menu-toggle {
      width: 42px;
      height: 42px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      display: inline-grid;
      place-items: center;
      cursor: pointer;
    }
    .menu-toggle span,
    .menu-toggle span::before,
    .menu-toggle span::after {
      width: 19px;
      height: 2px;
      display: block;
      background: var(--ink);
      content: "";
      border-radius: 99px;
    }
    .menu-toggle span::before { transform: translateY(-6px); }
    .menu-toggle span::after { transform: translateY(4px); }
    .brand { display: flex; align-items: center; gap: 12px; font-weight: 900; letter-spacing: .02em; }
    .brand span { min-width: 0; overflow-wrap: anywhere; }
    .mark {
      width: 44px;
      height: 44px;
      border-radius: 999px;
      display: block;
      object-fit: cover;
      border: 2px solid #fff;
      box-shadow: 0 10px 24px rgba(20,32,48,.18);
    }
    .nav-spacer { width: 42px; }
    .menu-backdrop {
      position: fixed;
      inset: 0;
      z-index: 30;
      background: rgba(10, 16, 24, .42);
      opacity: 0;
      pointer-events: none;
      transition: opacity .18s ease;
    }
    .side-menu {
      position: fixed;
      inset: 0 auto 0 0;
      z-index: 40;
      width: min(330px, 88vw);
      background: #fff;
      border-right: 1px solid var(--line);
      box-shadow: var(--shadow);
      transform: translateX(-100%);
      transition: transform .2s ease;
      display: flex;
      flex-direction: column;
    }
    body.menu-open .menu-backdrop { opacity: 1; pointer-events: auto; }
    body.menu-open .side-menu { transform: translateX(0); }
    .menu-head {
      min-height: 72px;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .menu-close {
      width: 38px;
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      font-size: 1.4rem;
      cursor: pointer;
    }
    .menu-links {
      padding: 14px;
      display: grid;
      gap: 8px;
    }
    .menu-links .btn {
      width: 100%;
      justify-content: flex-start;
      min-height: 48px;
    }
    .menu-links .btn.active {
      background: var(--brand);
      color: #fff;
      border-color: var(--brand);
    }
    .menu-foot {
      margin-top: auto;
      padding: 16px 18px;
      color: var(--muted);
      border-top: 1px solid var(--line);
      font-size: .9rem;
    }
    .shell { max-width: 1180px; margin: 0 auto; padding: clamp(16px, 4vw, 28px) clamp(12px, 4vw, 22px) 48px; min-width: 0; }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(min(260px, 100%), .85fr);
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
      text-align: center;
      max-width: 100%;
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
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr)); gap: 18px; }
    .pet-card {
      overflow: hidden;
      display: grid;
      grid-template-columns: 120px minmax(0, 1fr);
      min-height: 120px;
      color: inherit;
    }
    .pet-card:hover { transform: translateY(-2px); transition: transform .16s ease; }
    .pet-media {
      position: relative;
      width: 100%;
      height: 100%;
      min-height: 120px;
      aspect-ratio: 1;
      background:
        linear-gradient(135deg, rgba(232,80,53,.20), rgba(23,107,135,.20)),
        #edf3f7;
      display: grid;
      place-items: center;
      font-size: 2rem;
      font-weight: 900;
      color: var(--blue);
    }
    .pet-media img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .pet-body {
      padding: 16px;
      border-left: 1px solid var(--line);
      display: grid;
      gap: 10px;
      align-content: start;
      min-width: 0;
    }
    .pet-body h3 { margin: 0; font-size: 1.15rem; }
    .pet-summary {
      margin: 0;
      color: var(--muted);
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
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
    .badge.lost { background: #fff2ef; color: var(--brand-dark); }
    .badge.found { background: #e9f7f0; color: var(--green); }
    .photo-badge {
      position: absolute;
      top: 10px;
      right: 10px;
      box-shadow: 0 10px 24px rgba(20,32,48,.16);
    }
    .form-wrap { max-width: 900px; margin: 0 auto; }
    .detail-wrap { display: grid; grid-template-columns: minmax(0, .9fr) minmax(min(320px, 100%), 1.1fr); gap: 18px; align-items: start; }
    .detail-photo {
      overflow: hidden;
      padding: 0;
      aspect-ratio: 1;
    }
    .detail-media {
      position: relative;
      height: 100%;
      aspect-ratio: 1;
      display: grid;
      place-items: center;
      color: var(--blue);
      font-size: 3rem;
      font-weight: 900;
      background:
        linear-gradient(135deg, rgba(232,80,53,.18), rgba(23,107,135,.18)),
        #edf3f7;
    }
    .detail-media img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .detail-info { padding: clamp(20px, 4vw, 32px); }
    .info-list { display: grid; gap: 10px; margin-top: 18px; }
    .info-row { padding: 12px 0; border-bottom: 1px solid var(--line); display: grid; gap: 3px; }
    .info-row strong { font-size: .82rem; text-transform: uppercase; color: var(--muted); }
    .contact-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 18px; }
    .btn.whatsapp { background: #25d366; color: #fff; }
    .wa-icon {
      width: 20px;
      height: 20px;
      display: inline-block;
      flex: 0 0 auto;
    }
    .gallery { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 16px; }
    .gallery img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 8px; border: 1px solid var(--line); }
    .profile-layout { display: grid; grid-template-columns: minmax(min(280px, 100%), .85fr) minmax(0, 1.15fr); gap: 18px; align-items: start; }
    .avatar {
      width: 112px;
      height: 112px;
      border-radius: 999px;
      object-fit: cover;
      border: 4px solid #fff;
      box-shadow: var(--shadow);
      background: #edf3f7;
      display: grid;
      place-items: center;
      color: var(--blue);
      font-size: 2.4rem;
      font-weight: 900;
      overflow: hidden;
    }
    .avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .profile-card { padding: clamp(20px, 4vw, 32px); }
    .mini-list { display: grid; gap: 10px; margin-top: 16px; }
    .mini-report {
      display: grid;
      grid-template-columns: 72px 1fr;
      gap: 12px;
      align-items: center;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .mini-report img, .mini-thumb {
      width: 72px;
      height: 72px;
      object-fit: cover;
      border-radius: 8px;
      background: #edf3f7;
      display: grid;
      place-items: center;
      color: var(--blue);
      font-weight: 900;
    }
    .edit-images { display: grid; gap: 12px; }
    .edit-image-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }
    .edit-image-item {
      position: relative;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0;
      background: #fbfdff;
      display: grid;
      overflow: hidden;
    }
    .edit-image-item img {
      width: 100%;
      aspect-ratio: 1;
      object-fit: cover;
      display: block;
    }
    .remove-image-check {
      position: absolute;
      top: 8px;
      right: 8px;
      width: 34px;
      height: 34px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      background: rgba(184,56,36,.95);
      color: #fff;
      font-weight: 900;
      box-shadow: 0 10px 24px rgba(20,32,48,.20);
      cursor: pointer;
    }
    .remove-image-check input { position: absolute; opacity: 0; pointer-events: none; }
    .remove-image-check span { transform: translateY(-1px); }
    .remove-image-check:has(input:checked) { background: var(--ink); outline: 3px solid rgba(232,80,53,.25); }
    .zoomable { cursor: zoom-in; }
    .lightbox {
      position: fixed;
      inset: 0;
      z-index: 80;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 24px;
      background: rgba(6, 10, 16, .88);
    }
    .lightbox.open { display: flex; }
    .lightbox img {
      max-width: min(1100px, 94vw);
      max-height: 88vh;
      object-fit: contain;
      border-radius: 8px;
      box-shadow: 0 24px 80px rgba(0,0,0,.42);
      background: #111;
    }
    .lightbox-close {
      position: absolute;
      top: 16px;
      right: 16px;
      width: 42px;
      height: 42px;
      border: 1px solid rgba(255,255,255,.25);
      border-radius: 8px;
      background: rgba(255,255,255,.12);
      color: #fff;
      font-size: 1.6rem;
      cursor: pointer;
    }
    .form-panel { padding: clamp(20px, 4vw, 34px); }
    .form-panel h1 { color: var(--ink); font-size: clamp(1.8rem, 4vw, 2.7rem); }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr));
      gap: 16px;
      margin-top: 20px;
    }
    .field { display: grid; gap: 7px; min-width: 0; }
    .field.full { grid-column: 1 / -1; }
    label { font-weight: 800; font-size: .92rem; }
    .hint { color: var(--muted); font-size: .84rem; line-height: 1.4; }
    input, textarea, select {
      width: 100%;
      min-width: 0;
      max-width: 100%;
      border: 1px solid #cfd9e4;
      border-radius: 8px;
      min-height: 44px;
      padding: 10px 12px;
      background: #fff;
      color: var(--ink);
      font: inherit;
    }
    input[type="file"] { overflow: hidden; text-overflow: ellipsis; }
    textarea { min-height: 118px; resize: vertical; }
    input[type="date"] {
      -webkit-appearance: none;
      appearance: none;
      min-width: 0;
      max-width: 100%;
      padding-right: 8px;
      line-height: 1.2;
    }
    input[type="date"]::-webkit-datetime-edit {
      min-width: 0;
      padding: 0;
    }
    input[type="date"]::-webkit-calendar-picker-indicator {
      margin: 0;
      padding: 0;
      flex: 0 0 auto;
    }
    input:focus, textarea:focus, select:focus {
      outline: 3px solid rgba(23,107,135,.16);
      border-color: var(--blue);
    }
    .phone-box {
      display: grid;
      grid-template-columns: auto 1fr;
      align-items: center;
      border: 1px solid #cfd9e4;
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }
    .phone-prefix {
      min-height: 44px;
      padding: 0 12px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-right: 1px solid var(--line);
      background: #f8fafc;
      font-weight: 900;
      white-space: nowrap;
    }
    .phone-box input {
      border: 0;
      border-radius: 0;
    }
    .phone-box:focus-within {
      outline: 3px solid rgba(23,107,135,.16);
      border-color: var(--blue);
    }
    .checks { display: flex; flex-wrap: wrap; gap: 10px; }
    .checks input { min-width: min(260px, 100%); }
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
      .detail-wrap { grid-template-columns: 1fr; }
      .profile-layout { grid-template-columns: 1fr; }
      .contact-actions { grid-template-columns: 1fr; }
      .stats { grid-template-columns: 1fr; }
      .nav { padding: 0 16px; }
    }
    @media (max-width: 420px) {
      .brand { gap: 8px; font-size: .95rem; }
      .mark { width: 38px; height: 38px; }
      .menu-toggle, .nav-spacer { width: 38px; height: 38px; }
      .pet-card { grid-template-columns: 104px minmax(0, 1fr); min-height: 104px; }
      .pet-media { min-height: 104px; font-size: 1.55rem; }
      .pet-body { padding: 12px; gap: 7px; }
      .pet-body h3 { font-size: 1rem; }
      .pet-summary { -webkit-line-clamp: 1; }
      .photo-badge { top: 7px; right: 7px; min-height: 24px; padding: 0 8px; font-size: .68rem; }
      .hero-main { min-height: 260px; }
      .actions .btn, .contact-actions .btn { width: 100%; }
      .form-panel, .profile-card, .panel { padding: 16px; }
    }
    @media (min-width: 1024px) {
      .nav, .shell { max-width: 1440px; }
      .shell { padding-top: 34px; }
      .hero {
        grid-template-columns: minmax(0, 1.7fr) 340px;
        gap: 20px;
        margin-bottom: 30px;
      }
      .hero-main {
        min-height: 300px;
        padding: 42px;
      }
      .hero-main h1 { max-width: 760px; font-size: clamp(2.8rem, 4vw, 4.1rem); }
      .hero-main p { max-width: 620px; }
      .panel { padding: 24px; }
      .grid {
        grid-template-columns: repeat(auto-fill, minmax(520px, 1fr));
        gap: 20px;
      }
      .pet-card {
        grid-template-columns: 220px minmax(0, 1fr);
        min-height: 220px;
      }
      .pet-media {
        min-height: 220px;
      }
      .pet-body {
        min-height: 220px;
        padding: 20px;
      }
      .form-wrap { max-width: 1040px; }
      .form-panel { padding: 34px; }
      .form-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        column-gap: 18px;
        row-gap: 16px;
      }
      .detail-wrap {
        grid-template-columns: minmax(380px, 500px) minmax(0, 1fr);
        gap: 22px;
      }
      .detail-info { padding: 34px; }
      .profile-layout {
        grid-template-columns: 420px minmax(0, 1fr);
        gap: 22px;
      }
      .contact-actions { max-width: 460px; }
    }
    @media (min-width: 1024px) and (max-width: 1180px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <nav class="nav">
      <button class="menu-toggle" type="button" data-menu-open aria-label="Abrir menu"><span></span></button>
      <a class="brand" href="{{ url_for('index') }}"><img class="mark" src="{{ url_for('static', filename='logo.jpg') }}" alt="UBICAN ID"><span>UBICAN ID</span></a>
      <span class="nav-spacer" aria-hidden="true"></span>
    </nav>
  </header>
  <div class="menu-backdrop" data-menu-close></div>
  <aside class="side-menu" aria-label="Menu principal">
    <div class="menu-head">
      <a class="brand" href="{{ url_for('index') }}"><img class="mark" src="{{ url_for('static', filename='logo.jpg') }}" alt="UBICAN ID"><span>UBICAN ID</span></a>
      <button class="menu-close" type="button" data-menu-close aria-label="Cerrar menu">&times;</button>
    </div>
    <div class="menu-links">
      {% if current_user %}
        <a class="btn ghost {% if is_active('perfil') %}active{% endif %}" href="{{ url_for('perfil') }}">Mi perfil</a>
        <a class="btn ghost {% if is_active('reportar') %}active{% endif %}" href="{{ url_for('reportar') }}">Reportar mascota</a>
        <a class="btn ghost {% if is_active('index') %}active{% endif %}" href="{{ url_for('index') }}">Reportes</a>
        <a class="btn ghost" href="{{ url_for('logout') }}">Cerrar sesion</a>
      {% else %}
        <a class="btn ghost {% if is_active('login') %}active{% endif %}" href="{{ url_for('login') }}">Entrar</a>
        <a class="btn ghost {% if is_active('registro') %}active{% endif %}" href="{{ url_for('registro') }}">Crear cuenta</a>
        <a class="btn ghost {% if is_active('index') %}active{% endif %}" href="{{ url_for('index') }}">Reportes</a>
      {% endif %}
    </div>
    <div class="menu-foot">Registro exclusivo con telefono mexicano.</div>
  </aside>
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
  <div class="lightbox" data-lightbox aria-hidden="true">
    <button class="lightbox-close" type="button" data-lightbox-close aria-label="Cerrar imagen">&times;</button>
    <img src="" alt="">
  </div>
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

    document.querySelectorAll("[data-menu-open]").forEach((button) => {
      button.addEventListener("click", () => document.body.classList.add("menu-open"));
    });
    document.querySelectorAll("[data-menu-close]").forEach((button) => {
      button.addEventListener("click", () => document.body.classList.remove("menu-open"));
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") document.body.classList.remove("menu-open");
    });

    const lightbox = document.querySelector("[data-lightbox]");
    const lightboxImage = lightbox?.querySelector("img");
    function closeLightbox() {
      if (!lightbox || !lightboxImage) return;
      lightbox.classList.remove("open");
      lightbox.setAttribute("aria-hidden", "true");
      lightboxImage.src = "";
      lightboxImage.alt = "";
    }
    document.querySelectorAll("[data-zoom-src]").forEach((image) => {
      image.addEventListener("click", (event) => {
        if (!lightbox || !lightboxImage) return;
        event.preventDefault();
        event.stopPropagation();
        lightboxImage.src = image.dataset.zoomSrc;
        lightboxImage.alt = image.alt || "Imagen ampliada";
        lightbox.classList.add("open");
        lightbox.setAttribute("aria-hidden", "false");
      });
    });
    document.querySelectorAll("[data-lightbox-close]").forEach((button) => {
      button.addEventListener("click", closeLightbox);
    });
    lightbox?.addEventListener("click", (event) => {
      if (event.target === lightbox) closeLightbox();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeLightbox();
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
      <p class="meta" style="margin-top:18px;">Los reportes mas recientes aparecen primero para facilitar busquedas por direccion, ciudad y contacto.</p>
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
        <a class="pet-card" href="{{ url_for('detalle_mascota', report_id=pet.id) }}">
          <div class="pet-media">
            {% if pet.principal %}
              <img class="zoomable" src="{{ pet.principal }}" alt="{{ pet.nombre }}" data-zoom-src="{{ pet.principal }}">
            {% else %}
              {{ (pet.nombre or "?")[:1].upper() }}
            {% endif %}
            <span class="badge photo-badge {% if pet.encontrado %}found{% else %}lost{% endif %}">{{ "Localizado" if pet.encontrado else "Perdido" }}</span>
          </div>
          <div class="pet-body">
            <h3>{{ pet.nombre }}</h3>
            <p class="meta">
              {% if pet.direccion %}<strong>Direccion:</strong> {{ pet.direccion }}<br>{% endif %}
              {% if pet.ciudad or pet.estado %}<strong>Ubicacion:</strong> {{ pet.ciudad or "" }}{% if pet.ciudad and pet.estado %}, {% endif %}{{ pet.estado or "" }}{% endif %}
            </p>
            {% if pet.descripcion %}<p class="pet-summary">{{ pet.descripcion }}</p>{% endif %}
          </div>
        </a>
      {% endfor %}
    </section>
  {% else %}
    <div class="empty">Todavia no hay reportes publicados.</div>
  {% endif %}
{% endblock %}
""",
    "detalle.html": """
{% extends "base.html" %}
{% block content %}
  <section class="detail-wrap">
    <div class="panel detail-photo">
      <div class="detail-media">
        {% if mascota.principal %}
          <img class="zoomable" src="{{ mascota.principal }}" alt="{{ mascota.nombre }}" data-zoom-src="{{ mascota.principal }}">
        {% else %}
          {{ (mascota.nombre or "?")[:1].upper() }}
        {% endif %}
        <span class="badge photo-badge {% if mascota.encontrado %}found{% else %}lost{% endif %}">{{ "Localizado" if mascota.encontrado else "Perdido" }}</span>
      </div>
    </div>
    <article class="panel detail-info">
      <h1>{{ mascota.nombre }}</h1>
      {% if mascota.descripcion %}<p class="meta">{{ mascota.descripcion }}</p>{% endif %}
      {% if is_owner %}
        <div class="actions">
          <a class="btn primary" href="{{ url_for('editar_mascota', report_id=mascota.id) }}">Editar</a>
          <form method="post" action="{{ url_for('eliminar_mascota', report_id=mascota.id) }}" onsubmit="return confirm('Eliminar este reporte?');">
            <button class="btn" type="submit">Eliminar</button>
          </form>
        </div>
      {% endif %}

      {% if mascota.secundarias %}
        <div class="gallery">
          {% for image in mascota.secundarias %}
            <img class="zoomable" src="{{ image }}" alt="Foto de {{ mascota.nombre }}" data-zoom-src="{{ image }}">
          {% endfor %}
        </div>
      {% endif %}

      <div class="info-list">
        {% for label, value in [
          ("Fecha de extravio", mascota.fecha),
          ("Direccion de extravio", mascota.direccion),
          ("Entre calles", mascota.calles),
          ("Ciudad", mascota.ciudad),
          ("Estado", mascota.estado),
          ("Codigo postal", mascota.cp),
          ("Edad", mascota.edad),
          ("Raza", mascota.raza),
          ("Genero", mascota.genero),
          ("Color", mascota.color),
          ("Collar", mascota.collar),
          ("Docil", mascota.docil),
          ("Dueño", mascota.dueno),
          ("Recompensa", mascota.recompensa)
        ] %}
          {% if value %}
            <div class="info-row"><strong>{{ label }}</strong><span>{{ value }}</span></div>
          {% endif %}
        {% endfor %}
      </div>
      {% set call_phone = phone_digits(mascota.contacto) %}
      {% set wa_phone = whatsapp_digits(mascota.contacto) %}
      {% if call_phone %}
        <div class="contact-actions">
          <a class="btn primary" href="tel:{{ call_phone }}">Llamar</a>
          <a class="btn whatsapp" href="https://wa.me/{{ wa_phone }}" target="_blank" rel="noopener">
            <svg class="wa-icon" viewBox="0 0 32 32" aria-hidden="true">
              <path fill="currentColor" d="M16.04 3.2c-7.02 0-12.72 5.7-12.72 12.72 0 2.24.58 4.43 1.69 6.36L3.2 28.8l6.68-1.75a12.7 12.7 0 0 0 6.16 1.57c7.02 0 12.72-5.7 12.72-12.72S23.06 3.2 16.04 3.2Zm0 23.26c-1.93 0-3.82-.52-5.47-1.5l-.39-.23-3.96 1.04 1.06-3.86-.25-.4a10.48 10.48 0 0 1-1.6-5.6c0-5.86 4.76-10.62 10.61-10.62 2.84 0 5.5 1.1 7.5 3.11a10.55 10.55 0 0 1 3.11 7.5c0 5.85-4.76 10.56-10.61 10.56Zm5.82-7.94c-.32-.16-1.88-.93-2.17-1.03-.29-.11-.5-.16-.71.16-.21.32-.82 1.03-1 1.24-.18.21-.37.24-.69.08-.32-.16-1.35-.5-2.57-1.59-.95-.85-1.6-1.9-1.79-2.22-.18-.32-.02-.49.14-.65.14-.14.32-.37.48-.55.16-.18.21-.32.32-.53.11-.21.05-.4-.03-.55-.08-.16-.71-1.72-.97-2.35-.26-.62-.52-.53-.71-.54h-.61c-.21 0-.55.08-.84.4-.29.32-1.1 1.08-1.1 2.64s1.13 3.06 1.29 3.27c.16.21 2.23 3.41 5.4 4.78.75.32 1.34.52 1.8.66.76.24 1.45.21 1.99.13.61-.09 1.88-.77 2.14-1.51.26-.74.26-1.37.18-1.51-.08-.13-.29-.21-.61-.37Z"/>
            </svg>
            WhatsApp
          </a>
        </div>
      {% endif %}
      <div class="actions"><a class="btn" href="{{ url_for('index') }}">Volver a reportes</a></div>
    </article>
  </section>
{% endblock %}
""",
    "registro.html": """
{% extends "base.html" %}
{% block content %}
  <section class="form-wrap">
    <form class="form-panel" method="post" enctype="multipart/form-data">
      <p class="eyebrow" style="color: var(--brand);">Registro seguro</p>
      <h1>Crea tu cuenta</h1>
      <p class="meta">Solo aceptamos numeros mexicanos de 10 digitos.</p>
      <div class="form-grid">
        <div class="field full">
          <label for="tel">Telefono mexicano</label>
          <div class="phone-box">
            <span class="phone-prefix"><span aria-hidden="true">🇲🇽</span><span>+52</span></span>
            <input id="tel" name="tel" inputmode="numeric" autocomplete="tel" placeholder="(656) 778-7712" maxlength="14" pattern="\\(?[0-9]{3}\\)?[\\s-]?[0-9]{3}-?[0-9]{4}" data-phone-input required>
          </div>
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
      <h1>{{ "Restablecer contrasena" if recovering else "Protege tu acceso" }}</h1>
      <p class="meta">Telefono verificado: {{ phone }}</p>
      <div class="form-grid">
        {% if not recovering %}
          <div class="field">
            <label for="nombre">Nombre</label>
            <input id="nombre" name="nombre" autocomplete="name" placeholder="Tu nombre">
          </div>
        {% endif %}
        <div class="field">
          <label for="pwd">{{ "Nueva contrasena" if recovering else "Contrasena" }}</label>
          <input id="pwd" name="pwd" type="password" autocomplete="new-password" minlength="8" required>
        </div>
      </div>
      <div class="actions"><button class="btn primary" type="submit">{{ "Guardar contrasena" if recovering else "Guardar cuenta" }}</button></div>
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
          <div class="phone-box">
            <span class="phone-prefix"><span aria-hidden="true">🇲🇽</span><span>+52</span></span>
            <input id="tel" name="tel" inputmode="numeric" autocomplete="tel" placeholder="(656) 778-7712" maxlength="14" pattern="\\(?[0-9]{3}\\)?[\\s-]?[0-9]{3}-?[0-9]{4}" data-phone-input required>
          </div>
          <span class="hint">Usa el numero mexicano con el que creaste tu cuenta.</span>
        </div>
        <div class="field">
          <label for="pwd">Contrasena</label>
          <input id="pwd" name="pwd" type="password" autocomplete="current-password" required>
        </div>
      </div>
      <div class="actions">
        <button class="btn primary" type="submit">Entrar</button>
        <a class="btn" href="{{ url_for('registro') }}">Crear cuenta</a>
        <a class="btn ghost" href="{{ url_for('recuperar') }}">Restablecer contrasena</a>
      </div>
    </form>
  </section>
{% endblock %}
""",
    "recuperar.html": """
{% extends "base.html" %}
{% block content %}
  <section class="form-wrap">
    <form class="form-panel" method="post">
      <p class="eyebrow" style="color: var(--brand);">Recuperacion</p>
      <h1>Restablecer contrasena</h1>
      <p class="meta">Enviaremos un codigo al telefono registrado.</p>
      <div class="form-grid">
        <div class="field full">
          <label for="tel">Telefono mexicano</label>
          <div class="phone-box">
            <span class="phone-prefix"><span aria-hidden="true">🇲🇽</span><span>+52</span></span>
            <input id="tel" name="tel" inputmode="numeric" autocomplete="tel" placeholder="(656) 778-7712" maxlength="14" pattern="\\(?[0-9]{3}\\)?[\\s-]?[0-9]{3}-?[0-9]{4}" data-phone-input required>
          </div>
        </div>
      </div>
      <div class="actions"><button class="btn primary" type="submit">Enviar codigo</button></div>
    </form>
  </section>
{% endblock %}
""",
    "perfil.html": """
{% extends "base.html" %}
{% block content %}
  <section class="profile-layout">
    <div class="panel profile-card">
      <p class="eyebrow" style="color: var(--brand);">Cuenta</p>
      <div class="avatar">
        {% if user.foto %}
          <img src="{{ user.foto }}" alt="{{ user.nombre or 'Perfil' }}">
        {% else %}
          {{ (user.nombre or user.telefono or "U")[:1].upper() }}
        {% endif %}
      </div>
      <h1>{{ user.nombre or "Mi perfil" }}</h1>
      <p class="meta"><strong>Telefono registrado:</strong><br>{{ user.telefono }}</p>

      <form method="post" enctype="multipart/form-data" class="form-grid">
        <div class="field full">
          <label for="nombre">Nombre</label>
          <input id="nombre" name="nombre" value="{{ user.nombre or '' }}">
        </div>
        <div class="field full">
          <label for="foto">Foto de perfil</label>
          <input id="foto" name="foto" type="file" accept="image/*">
        </div>
        <div class="actions"><button class="btn primary" type="submit">Guardar perfil</button></div>
      </form>
    </div>

    <div class="panel profile-card">
      <p class="eyebrow" style="color: var(--brand);">Seguridad</p>
      <h1>Cambiar contrasena</h1>
      <form method="post" action="{{ url_for('cambiar_password') }}" class="form-grid">
        <div class="field full">
          <label for="current_password">Contrasena actual</label>
          <input id="current_password" name="current_password" type="password" autocomplete="current-password" required>
        </div>
        <div class="field">
          <label for="new_password">Nueva contrasena</label>
          <input id="new_password" name="new_password" type="password" autocomplete="new-password" minlength="8" required>
        </div>
        <div class="field">
          <label for="confirm_password">Confirmar contrasena</label>
          <input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" minlength="8" required>
        </div>
        <div class="actions"><button class="btn primary" type="submit">Actualizar contrasena</button></div>
      </form>
    </div>
  </section>

  <section class="panel profile-card" style="margin-top:18px;">
    <div class="section-head" style="margin-top:0;">
      <div>
        <h2>Mis reportes</h2>
        <p>Reportes publicados con tu numero registrado.</p>
      </div>
      <a class="btn primary" href="{{ url_for('reportar') }}">Nuevo reporte</a>
    </div>
    {% if reportes %}
      <div class="mini-list">
        {% for pet in reportes %}
          <a class="mini-report" href="{{ url_for('detalle_mascota', report_id=pet.id) }}">
            {% if pet.principal %}
              <img src="{{ pet.principal }}" alt="{{ pet.nombre }}">
            {% else %}
              <span class="mini-thumb">{{ (pet.nombre or "?")[:1].upper() }}</span>
            {% endif %}
            <span>
              <strong>{{ pet.nombre }}</strong><br>
              <span class="meta">{{ "Localizado" if pet.encontrado else "Perdido" }}{% if pet.ciudad %} · {{ pet.ciudad }}{% endif %}</span>
            </span>
          </a>
        {% endfor %}
      </div>
    {% else %}
      <div class="empty">Todavia no tienes reportes publicados.</div>
    {% endif %}
  </section>
{% endblock %}
""",
    "reportar.html": """
{% extends "base.html" %}
{% block content %}
  <section class="form-wrap">
    <form class="form-panel" method="post" enctype="multipart/form-data">
      <p class="eyebrow" style="color: var(--brand);">Nuevo reporte</p>
      <h1>{{ "Editar reporte" if editing else "Datos de la mascota" }}</h1>
      <div class="form-grid">
        <div class="field">
          <label for="nombre">Nombre o identificador</label>
          <input id="nombre" name="nombre" value="{{ mascota.nombre or '' }}" required>
        </div>
        <div class="field">
          <label for="contacto">Contacto publico</label>
          <input id="contacto" name="contacto" value="{{ mascota.contacto or '' }}" placeholder="Telefono, WhatsApp o correo">
        </div>
        <div class="field full">
          <label for="descripcion">Descripcion</label>
          <textarea id="descripcion" name="descripcion" placeholder="Senales particulares, temperamento, ultima vez visto">{{ mascota.descripcion or '' }}</textarea>
        </div>
        <div class="field"><label for="fecha">Fecha</label><input id="fecha" name="fecha" type="date" value="{{ mascota.fecha or '' }}"></div>
        <div class="field"><label for="edad">Edad</label><input id="edad" name="edad" value="{{ mascota.edad or '' }}"></div>
        <div class="field"><label for="raza">Raza</label><input id="raza" name="raza" value="{{ mascota.raza or '' }}"></div>
        <div class="field"><label for="genero">Genero</label><select id="genero" name="genero"><option value="">Seleccionar</option><option {% if mascota.genero == "Macho" %}selected{% endif %}>Macho</option><option {% if mascota.genero == "Hembra" %}selected{% endif %}>Hembra</option><option {% if mascota.genero == "No se sabe" %}selected{% endif %}>No se sabe</option></select></div>
        <div class="field"><label for="color">Color</label><input id="color" name="color" value="{{ mascota.color or '' }}"></div>
        <div class="field"><label for="collar">Collar</label><input id="collar" name="collar" value="{{ mascota.collar or '' }}"></div>
        <div class="field"><label for="docil">Comportamiento</label><input id="docil" name="docil" value="{{ mascota.docil or '' }}" placeholder="Docil, nervioso, asustado"></div>
        <div class="field">
          <label>Estado del reporte</label>
          <label class="check"><input type="checkbox" name="encontrado" {% if mascota.encontrado %}checked{% endif %}> Localizado</label>
        </div>
        <div class="field full">
          <label for="principal">Foto principal</label>
          {% if editing and mascota.principal %}
            <div class="edit-images">
              <div class="edit-image-item" style="max-width:180px;">
                <img src="{{ mascota.principal }}" alt="Foto principal actual">
                <label class="remove-image-check" title="Quitar"><input type="checkbox" name="remove_principal"><span>&times;</span></label>
              </div>
            </div>
          {% endif %}
          <input id="principal" name="principal" type="file" accept="image/*">
        </div>
        <div class="field full">
          <label>Fotos secundarias</label>
          {% if editing and mascota.secundarias %}
            <div class="edit-image-grid">
              {% for image in mascota.secundarias %}
                <div class="edit-image-item">
                  <img src="{{ image }}" alt="Foto secundaria actual">
                  <label class="remove-image-check" title="Quitar"><input type="checkbox" name="remove_secundarias" value="{{ image }}"><span>&times;</span></label>
                </div>
              {% endfor %}
            </div>
          {% endif %}
          <div class="checks">
            <input name="secundarias" type="file" accept="image/*" multiple>
          </div>
        </div>
        <div class="field full"><label for="direccion">Direccion de extravio</label><input id="direccion" name="direccion" value="{{ mascota.direccion or '' }}"></div>
        <div class="field"><label for="ciudad">Ciudad</label><input id="ciudad" name="ciudad" value="{{ mascota.ciudad or '' }}"></div>
        <div class="field"><label for="estado">Estado</label><input id="estado" name="estado" value="{{ mascota.estado or '' }}"></div>
        <div class="field"><label for="cp">Codigo postal</label><input id="cp" name="cp" inputmode="numeric" value="{{ mascota.cp or '' }}"></div>
        <div class="field"><label for="calles">Entre calles</label><input id="calles" name="calles" value="{{ mascota.calles or '' }}"></div>
        <div class="field"><label for="dueno">Dueno</label><input id="dueno" name="dueno" value="{{ mascota.dueno or '' }}"></div>
        <div class="field"><label for="recompensa">Recompensa</label><input id="recompensa" name="recompensa" value="{{ mascota.recompensa or '' }}"></div>
      </div>
      <div class="actions">
        <button class="btn primary" type="submit">{{ "Guardar cambios" if editing else "Publicar reporte" }}</button>
        {% if editing %}
          <a class="btn" href="{{ url_for('detalle_mascota', report_id=mascota.id) }}">Cancelar</a>
        {% else %}
          <a class="btn" href="{{ url_for('index') }}">Cancelar</a>
        {% endif %}
      </div>
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
