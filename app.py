import os
import time
import random
import requests
from flask import Flask, request, render_template_string, redirect, url_for, session
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia_esto_en_produccion_segura_12345")
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin_default_token")

# ─── CONFIGURACIÓN DE SUPABASE ────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://db-reportes.srvr.site")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc4MjUzODgwMCwiZXhwIjo0OTM4MjEyNDAwLCJyb2xlIjoiYW5vbiJ9.4Cuw0ST380Zj--VD0HD49i5lt7pThaFRGIY63tsSQr8")

SUPABASE_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ─── LABSMOBILE CONFIG ────────────────────────────────────────────────────────
LABSMOBILE_USER   = os.getenv("LABSMOBILE_USER", "")
LABSMOBILE_TOKEN  = os.getenv("LABSMOBILE_TOKEN", "")
LABSMOBILE_SENDER = os.getenv("LABSMOBILE_SENDER") or None
LABSMOBILE_API    = os.getenv("LABSMOBILE_API", "https://api.labsmobile.com/json/send")

# ─── HELPERS DE BASE DE DATOS (SUPABASE) ──────────────────────────────────────
def db_get_usuario(telefono):
    url = f"{SUPABASE_URL}/rest/v1/usuarios?telefono=eq.{telefono}"
    try:
        r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10)
        res = r.json()
        return res[0] if isinstance(res, list) and len(res) > 0 else None
    except Exception as e:
        print(f"⚠️ Error db_get_usuario: {e}")
        return None

def db_save_usuario(telefono, password_hash):
    url = f"{SUPABASE_URL}/rest/v1/usuarios"
    payload = {"telefono": telefono, "creado": int(time.time()), "password_hash": password_hash}
    headers = {**SUPABASE_HEADERS, "Prefer": "resolution=merge-duplicates"}
    try: requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e: print(f"⚠️ Error db_save_usuario: {e}")

def db_get_mascotas():
    url = f"{SUPABASE_URL}/rest/v1/mascotas?order=id.desc"
    try:
        r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10)
        return r.json() if isinstance(r.json(), list) else []
    except Exception as e:
        print(f"⚠️ Error db_get_mascotas: {e}")
        return []

def db_get_mascota_por_id(id_mascota):
    url = f"{SUPABASE_URL}/rest/v1/mascotas?id=eq.{id_mascota}"
    try:
        r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10).json()
        return r[0] if r and isinstance(r, list) else None
    except: return None

def db_save_mascota(datos):
    url = f"{SUPABASE_URL}/rest/v1/mascotas"
    try: requests.post(url, json=datos, headers=SUPABASE_HEADERS, timeout=10)
    except Exception as e: print(f"⚠️ Error db_save_mascota: {e}")

def db_update_mascota(id_mascota, datos):
    url = f"{SUPABASE_URL}/rest/v1/mascotas?id=eq.{id_mascota}"
    try: requests.patch(url, json=datos, headers=SUPABASE_HEADERS, timeout=10)
    except Exception as e: print(f"⚠️ Error db_update_mascota: {e}")

def db_delete_mascota(id_mascota):
    url = f"{SUPABASE_URL}/rest/v1/mascotas?id=eq.{id_mascota}"
    try: requests.delete(url, headers=SUPABASE_HEADERS, timeout=10)
    except Exception as e: print(f"⚠️ Error db_delete_mascota: {e}")

# ─── MANEJO DE OTP ────────────────────────────────────────────────────────────
def db_guardar_otp(telefono, codigo):
    url = f"{SUPABASE_URL}/rest/v1/otps"
    payload = {"telefono": telefono, "code": codigo, "expires": time.time() + 300}
    headers = {**SUPABASE_HEADERS, "Prefer": "resolution=merge-duplicates"}
    try: requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e: print(f"⚠️ Error db_guardar_otp: {e}")

def db_verificar_otp(telefono, codigo):
    url = f"{SUPABASE_URL}/rest/v1/otps?telefono=eq.{telefono}"
    try:
        r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10).json()
        if not r or not isinstance(r, list): return False, "No se solicitó un código."
        entry = r[0]
        if time.time() > entry["expires"]:
            requests.delete(url, headers=SUPABASE_HEADERS, timeout=10)
            return False, "El código expiró."
        if entry["code"] != codigo.strip(): return False, "Código incorrecto."
        requests.delete(url, headers=SUPABASE_HEADERS, timeout=10)
        return True, "OK"
    except Exception as e: return False, str(e)

# ─── MANEJO DE STORAGE (SUBIDA Y BORRADO) ─────────────────────────────────────
def upload_to_supabase_storage(file_field):
    if not file_field or file_field.filename == '': return ""
    try:
        nombre_archivo = f"{int(time.time()*1000)}_{file_field.filename}"
        upload_url = f"{SUPABASE_URL}/storage/v1/object/imagenes_mascotas/{nombre_archivo}"
        headers_storage = {"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {SUPABASE_ANON_KEY}", "Content-Type": file_field.content_type}
        res = requests.post(upload_url, data=file_field.read(), headers=headers_storage, timeout=15)
        if res.status_code == 200:
            return f"{SUPABASE_URL}/storage/v1/object/public/imagenes_mascotas/{nombre_archivo}"
        return ""
    except: return ""

def delete_from_supabase_storage(public_url):
    if not public_url: return
    try:
        nombre_archivo = public_url.split("/imagenes_mascotas/")[-1]
        delete_url = f"{SUPABASE_URL}/storage/v1/object/imagenes_mascotas/{nombre_archivo}"
        headers_storage = {"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
        requests.delete(delete_url, headers=headers_storage, timeout=10)
    except: pass

# ─── HELPERS AUXILIARES ────────────────────────────────────────────────────────
def hash_password(password): return generate_password_hash(password, method='scrypt')
def verify_password(password, hashed): return check_password_hash(hashed, password)
def user_has_password(telefono):
    u = db_get_usuario(telefono)
    return u is not None and bool(u.get("password_hash"))
def generar_otp(): return str(random.randint(100000, 999999))
def enviar_sms_otp(telefono, codigo):
    payload = {"message": f"Tu código Ubican ID es: {codigo}.", "recipient": [{"msisdn": telefono}]}
    if LABSMOBILE_SENDER: payload["tpoa"] = LABSMOBILE_SENDER
    try:
        r = requests.post(LABSMOBILE_API, json=payload, auth=(LABSMOBILE_USER, LABSMOBILE_TOKEN), headers={"Content-Type": "application/json"}, timeout=10)
        return r.status_code == 200, r.text
    except Exception as e: return False, str(e)

# ─── CSS ESTILIZADO COMPLETO ──────────────────────────────────────────────────
BASE_CSS = """
<meta name='viewport' content='width=device-width, initial-scale=1, maximum-scale=1'>
<style>
:root {
  --grad: linear-gradient(135deg,#ff6b4a,#ff9f43);
  --dark: #1e293b; --bg: #f8fafc; --card: #ffffff; --gray: #64748b;
  --success: #10b981; --danger: #ef4444; --blue: #3b82f6;
}
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:system-ui,-apple-system,sans-serif; background:var(--bg); color:var(--dark); padding-bottom: 60px;}
.navbar { background:rgba(255,255,255,.85); backdrop-filter:blur(12px); position:sticky; top:0; z-index:90; padding:16px 24px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; }
.navbar-brand { font-size:1.2em; font-weight:800; text-decoration:none; color:inherit; }
.navbar-brand span { background:var(--grad); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.nav-user { font-size:0.85em; color:var(--gray); display:flex; align-items:center; gap:12px; }
.nav-user a { color:var(--danger); font-weight:600; text-decoration:none; }
.auth-wrap { min-height:100vh; display:flex; align-items:center; justify-content:center; padding:24px 16px; }
.auth-box { background:var(--card); border-radius:28px; border:1px solid #e2e8f0; padding:36px 32px; width:100%; max-width:520px; box-shadow:0 8px 24px -8px rgba(0,0,0,.08); }

/* Grid de Formulario Modular */
.form-section { border-bottom: 1px dashed #e2e8f0; padding-bottom: 15px; margin-bottom: 20px; }
.form-section h4 { color: #475569; margin-bottom: 12px; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; }
.form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 500px) { .form-grid-2 { grid-template-columns: 1fr; } }

.form-group { margin-bottom: 14px; }
.form-group label { display:block; font-size:0.82em; font-weight:700; margin-bottom:6px; color:#475569; }
.form-group input, .form-group textarea, .form-group select { width:100%; padding:11px 14px; border:1px solid #cbd5e1; border-radius:10px; font-size:0.95em; background:#f8fafc; outline:none; font-family: inherit;}
.form-group input:focus, .form-group select:focus { border-color:#ff9f43; background:#fff; }

.btn-primary { background:var(--grad); color:white; border:none; width:100%; padding:14px; border-radius:12px; font-weight:700; font-size:1em; cursor:pointer; min-height:48px; text-decoration:none; display:inline-block; text-align:center;}
.alert-error { background:#fef2f2; color:#991b1b; border:1px solid #fecaca; padding:12px; border-radius:12px; margin-bottom:15px;}
.otp-inputs { display:flex; gap:8px; justify-content:center; }
.otp-inputs input { width:45px; height:45px; text-align:center; font-size:1.4em; font-weight:700; border:2px solid #cbd5e1; border-radius:12px; }
.main-container { max-width:1100px; margin:40px auto; padding:0 24px; }
.grid-feed { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:24px; margin-top:24px; }

/* Tarjetas */
.card-link { text-decoration: none; color: inherit; display: block; height: 100%; }
.card-minimal { background:var(--card); border-radius:20px; border:1px solid #e2e8f0; overflow:hidden; display:flex; flex-direction:column; height:100%; position:relative; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); transition: transform 0.2s; }
.card-minimal:hover { transform: translateY(-4px); }
.card-img-box { width:100%; aspect-ratio:4/3; background:#f1f5f9; position:relative; }
.card-img-box img { width:100%; height:100%; object-fit:cover; }
.card-badge { position:absolute; top:12px; right:12px; background:#ef4444; color:white; font-size:.7em; font-weight:800; padding:4px 10px; border-radius:99px; }
.card-reward-badge { position:absolute; top:12px; left:12px; background:#10b981; color:white; font-size:.7em; font-weight:800; padding:4px 10px; border-radius:99px; }
.card-info { padding:16px; display:flex; flex-direction:column; gap:4px; flex-grow:1; }
.card-info h3 { font-size:1.15em; margin-bottom:4px; color:var(--dark); }
.card-info p { font-size:0.9em; color:var(--gray); line-height:1.4; }

.card-actions { padding:12px 16px; border-top:1px solid #f1f5f9; background:#f8fafc; display:flex; gap:8px; }
.btn-action { flex:1; text-align:center; padding:8px; border-radius:8px; font-size:0.85em; font-weight:600; text-decoration:none; border:none; cursor:pointer; }
.btn-edit { background:#e0f2fe; color:#0369a1; }
.btn-delete { background:#fee2e2; color:#b91c1c; }
.form-report { background:#fff; padding:28px; border-radius:24px; border:1px solid #e2e8f0; margin-bottom:32px; box-shadow:0 10px 15px -3px rgba(0,0,0,0.02); }

/* Perfil Detallado */
.detail-layout { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 40px; margin-top: 20px; }
@media (max-width: 768px) { .detail-layout { grid-template-columns: 1fr; gap: 24px; } }
.detail-img { width: 100%; border-radius: 24px; border: 1px solid #e2e8f0; aspect-ratio: 4/3; object-fit: cover; background: #f1f5f9; }
.detail-content { display: flex; flex-direction: column; gap: 16px; }
.detail-title { font-size: 2.5em; font-weight: 800; }
.badge-row { display: flex; gap: 8px; flex-wrap: wrap; }
.meta-badge { display: inline-block; background: #fee2e2; color: #b91c1c; font-weight: 700; padding: 6px 14px; border-radius: 99px; font-size: 0.85em; }
.meta-badge.reward { background: #d1fae5; color: #065f46; }
.info-block { background: white; padding: 24px; border-radius: 24px; border: 1px solid #e2e8f0; }
.info-row { display: flex; padding: 12px 0; border-bottom: 1px solid #f1f5f9; font-size: 1em; align-items: baseline; }
.info-row:last-child { border-bottom: none; }
.info-label { width: 140px; font-weight: 700; color: #64748b; font-size: 0.9em; text-transform: uppercase; }
.info-val { color: var(--dark); flex: 1; line-height: 1.5; }
</style>
"""

# ─── RUTAS DE AUTENTICACIÓN (LÓGICA INTERNA) ──────────────────────────────────
@app.route('/registro', methods=['GET','POST'])
def registro():
    error = ""
    if request.method == 'POST':
        telefono = request.form.get("telefono","").strip()
        if not telefono: error = "Ingresa tu número de WhatsApp."
        elif db_get_usuario(telefono): error = "Este número ya está registrado."
        else:
            codigo = generar_otp()
            db_guardar_otp(telefono, codigo)
            ok, _ = enviar_sms_otp(telefono, codigo)
            if ok: return redirect(url_for('verificar_registro', tel=telefono))
            error = "No se pudo enviar el SMS."
    return render_template_string(BASE_CSS + "<div class='auth-wrap'><div class='auth-box'><h1>🐾 Crear cuenta</h1>{% if error %}<div class='alert-error'>{{ error }}</div>{% endif %}<form method='POST'><div class='form-group'><label>WhatsApp</label><input type='tel' name='telefono' placeholder='Ej. 526561234567'></div><button class='btn-primary' type='submit'>Enviar SMS →</button></form></div></div>", error=error)

@app.route('/registro/verificar', methods=['GET','POST'])
def verificar_registro():
    telefono = request.args.get("tel","")
    error = ""
    if request.method == 'POST':
        codigo = "".join([request.form.get(f"d{i}","") for i in range(1,7)])
        ok, msg = db_verificar_otp(telefono, codigo)
        if ok:
            db_save_usuario(telefono, "")
            session["pending_password_phone"] = telefono
            return redirect(url_for('crear_password'))
        error = msg
    return render_template_string(BASE_CSS + "<div class='auth-wrap'><div class='auth-box'><h1>✅ Verifica</h1>{% if error %}<div class='alert-error'>{{ error }}</div>{% endif %}<form method='POST'><div class='otp-inputs'>{% for i in range(1, 7) %}<input type='text' name='d{{i}}' maxlength='1'>{% endfor %}</div><button class='btn-primary' type='submit' style='margin-top:20px'>Verificar →</button></form></div></div>", error=error)

@app.route('/crear-password', methods=['GET','POST'])
def crear_password():
    telefono = session.get("pending_password_phone")
    if not telefono: return redirect(url_for('registro'))
    error = ""
    if request.method == 'POST':
        pwd1 = request.form.get("password","")
        if len(pwd1) < 6: error = "Mínimo 6 caracteres."
        else:
            db_save_usuario(telefono, hash_password(pwd1))
            session.pop("pending_password_phone", None)
            session["telefono"] = telefono
            return redirect(url_for('index'))
    return render_template_string(BASE_CSS + "<div class='auth-wrap'><div class='auth-box'><h1>🔑 Contraseña</h1>{% if error %}<div class='alert-error'>{{ error }}</div>{% endif %}<form method='POST'><div class='form-group'><input type='password' name='password' placeholder='••••••••'></div><button class='btn-primary' type='submit'>Guardar →</button></form></div></div>", error=error)

@app.route('/login', methods=['GET','POST'])
def login():
    error = ""
    if request.method == 'POST':
        telefono = request.form.get("telefono","").strip()
        if db_get_usuario(telefono):
            if user_has_password(telefono): return redirect(url_for('login_password', tel=telefono))
            else:
                codigo = generar_otp()
                db_guardar_otp(telefono, codigo)
                enviar_sms_otp(telefono, codigo)
                return redirect(url_for('verificar_login_otp', tel=telefono))
        error = "No registrado."
    return render_template_string(BASE_CSS + "<div class='auth-wrap'><div class='auth-box'><h1>🔐 Entrar</h1>{% if error %}<div class='alert-error'>{{ error }}</div>{% endif %}<form method='POST'><div class='form-group'><input type='tel' name='telefono' placeholder='WhatsApp'></div><button class='btn-primary' type='submit'>Continuar</button></form></div></div>", error=error)

@app.route('/login/password', methods=['GET','POST'])
def login_password():
    telefono = request.args.get("tel","")
    error = ""
    if request.method == 'POST':
        password = request.form.get("password","")
        u = db_get_usuario(telefono)
        if u and verify_password(password, u.get("password_hash","")):
            session["telefono"] = telefono
            return redirect(url_for('index'))
        error = "Incorrecta."
    return render_template_string(BASE_CSS + "<div class='auth-wrap'><div class='auth-box'><h1>Contraseña</h1>{% if error %}<div class='alert-error'>{{ error }}</div>{% endif %}<form method='POST'><div class='form-group'><input type='password' name='password'></div><button class='btn-primary' type='submit'>Entrar</button></form></div></div>", error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ─── NÚCLEO CRUD DE MASCOTAS (CON TODOS LOS CAMPOS DE LA DB) ──────────────────

@app.route('/', methods=['GET', 'POST'])
def index():
    usuario = session.get("telefono")
    es_admin = (request.args.get('admin') == ADMIN_TOKEN)
    mascotas_perdidas = db_get_mascotas()

    if request.method == 'POST' and usuario:
        nombre = request.form.get("nombre","").strip()
        if nombre:
            url_p = upload_to_supabase_storage(request.files.get("imagen_principal"))
            nuevo = {
                "id": str(int(time.time() * 1000)),
                "reportado_por": usuario,
                "nombre":       nombre,
                "descripcion":  request.form.get("descripcion"),
                "zona":         request.form.get("zona"),
                "contacto":     request.form.get("contacto"),
                "principal":    url_p,
                "secundarias":  [],
                "fecha":        request.form.get("fecha"),
                "edad":         request.form.get("edad"),
                "raza":         request.form.get("raza"),
                "genero":       request.form.get("genero"),
                "color":        request.form.get("color"),
                "collar":       request.form.get("collar"),
                "docil":        request.form.get("docil"),
                "direccion":    request.form.get("direccion"),
                "ciudad":       request.form.get("ciudad"),
                "estado":       request.form.get("estado"),
                "cp":           request.form.get("cp"),
                "calles":       request.form.get("calles"),
                "dueno":        request.form.get("dueno"),
                "recompensa":   request.form.get("recompensa")
            }
            db_save_mascota(nuevo)
        return redirect(url_for('index', admin=ADMIN_TOKEN if es_admin else None))

    html_index = BASE_CSS + """
    <div class='navbar'>
      <a href='/' class='navbar-brand'>🐾 Ubican<span>ID</span></a>
      <div class='nav-user'>
        {% if usuario %}<span>📱 {{ usuario }}</span> | <a href='/logout'>Salir</a>{% else %}<a href='/login'>Entrar / Registrarse</a>{% endif %}
      </div>
    </div>
    <div class='main-container'>
      {% if usuario %}
      <div class='form-report'>
        <h3 style='font-size:1.4em; font-weight:800; margin-bottom:15px;'>📢 Publicar Reporte de Mascota Extraviada</h3>
        <form method='POST' enctype='multipart/form-data'>
          
          <div class='form-section'>
            <h4>1. Datos Básicos</h4>
            <div class='form-grid-2'>
              <div class='form-group'><label>Nombre de la mascota</label><input type='text' name='nombre' required></div>
              <div class='form-group'><label>Fecha de Extravío</label><input type='date' name='fecha'></div>
            </div>
            <div class='form-group'><label>Descripción / Señas Particulares</label><textarea name='descripcion' rows='2' placeholder='Ej: Mancha blanca en ojo derecho, cicatriz...'></textarea></div>
          </div>

          <div class='form-section'>
            <h4>2. Características Físicas</h4>
            <div class='form-grid-2'>
              <div class='form-group'><label>Raza</label><input type='text' name='raza' placeholder='Ej: Husky, Mestizo'></div>
              <div class='form-group'><label>Edad aproximada</label><input type='text' name='edad' placeholder='Ej: 2 años'></div>
            </div>
            <div class='form-grid-2'>
              <div class='form-group'>
                <label>Género</label>
                <select name='genero'>
                  <option value=''>Selecciona...</option>
                  <option value='Macho'>Macho</option>
                  <option value='Hembra'>Hembra</option>
                </select>
              </div>
              <div class='form-group'><label>Color de pelaje</label><input type='text' name='color' placeholder='Ej: Negro con blanco'></div>
            </div>
            <div class='form-grid-2'>
              <div class='form-group'><label>¿Lleva collar? (Color / Tipo)</label><input type='text' name='collar' placeholder='Ej: Rojo con placa'></div>
              <div class='form-group'>
                <label>¿Es dócil con extraños?</label>
                <select name='docil'>
                  <option value='Sí'>Sí, es muy dócil</option>
                  <option value='No'>No, es miedoso/agresivo</option>
                  <option value='Regular'>Regular / Desconfiado</option>
                </select>
              </div>
            </div>
          </div>

          <div class='form-section'>
            <h4>3. ¿Dónde se perdió?</h4>
            <div class='form-grid-2'>
              <div class='form-group'><label>Zona o Colonia (Obligatorio)</label><input type='text' name='zona' placeholder='Ej: Las Misiones' required></div>
              <div class='form-group'><label>Dirección aproximada</label><input type='text' name='direccion' placeholder='Ej: Av. Tecnológico 1230'></div>
            </div>
            <div class='form-grid-2'>
              <div class='form-group'><label>Entre qué calles</label><input type='text' name='calles' placeholder='Ej: Entre Calle 1 y Calle 2'></div>
              <div class='form-group'><label>Código Postal</label><input type='text' name='cp'></div>
            </div>
            <div class='form-grid-2'>
              <div class='form-group'><label>Ciudad</label><input type='text' name='ciudad' value='Ciudad Juárez'></div>
              <div class='form-group'><label>Estado</label><input type='text' name='estado' value='Chihuahua'></div>
            </div>
          </div>

          <div class='form-section'>
            <h4>4. Contacto y Recompensa</h4>
            <div class='form-grid-2'>
              <div class='form-group'><label>Nombre del Dueño</label><input type='text' name='dueno'></div>
              <div class='form-group'><label>Teléfono de Contacto (Obligatorio)</label><input type='tel' name='contacto' placeholder='Ej: 6561234567' required></div>
            </div>
            <div class='form-group'><label>Monto de Recompensa (Opcional)</label><input type='text' name='recompensa' placeholder='Ej: $5,000 MXN o Dejar en blanco'></div>
          </div>

          <div class='form-group'><label>Foto de la Mascota</label><input type='file' name='imagen_principal' accept='image/*'></div>
          
          <button type='submit' class='btn-primary' style='margin-top:10px;'>🚀 Publicar Reporte de Búsqueda</button>
        </form>
      </div>
      {% endif %}
      
      <h2 style='font-size:1.6em; font-weight:800; margin-bottom:15px;'>Mascotas Extraviadas Recientemente</h2>
      <div class='grid-feed'>
        {% for m in mascotas %}
        <div style='display: flex; flex-direction: column; height: 100%; position: relative;'>
          <a href='/mascota/{{ m.id }}' class='card-link'>
            <div class='card-minimal'>
              <div class='card-img-box'>
                {% if m.principal %}<img src='{{ m.principal }}'>{% else %}<div style='padding:40px;text-align:center;color:var(--gray);'>Sin foto</div>{% endif %}
                <span class='card-badge'>PERDIDO</span>
                {% if m.recompensa %}<span class='card-reward-badge'>💰 Recompensa</span>{% endif %}
              </div>
              <div class='card-info'>
                <h3>{{ m.nombre }}</h3>
                <p><strong>Raza:</strong> {{ m.raza if m.raza else 'No especificada' }}</p>
                <p style='font-size:0.85em; margin-top:auto; font-weight: 600; color:#ff6b4a;'>📍 {{ m.zona }}</p>
              </div>
            </div>
          </a>
          {% if usuario == m.reportado_por or es_admin %}
          <div class='card-actions'>
            <a href='/mascota/editar/{{ m.id }}' class='btn-action btn-edit'>Editar</a>
            <a href='/mascota/eliminar/{{ m.id }}' class='btn-action btn-delete' onclick='return confirm("¿Borrar reporte?")'>Eliminar</a>
          </div>
          {% endif %}
        </div>
        {% endfor %}
      </div>
    </div>"""
    return render_template_string(html_index, mascotas=mascotas_perdidas, usuario=usuario, es_admin=es_admin)


# ─── VISTA DETALLADA COMPLETA (MUESTRA ABSOLUTAMENTE TODO) ────────────────────
@app.route('/mascota/<id_mascota>')
def ver_mascota(id_mascota):
    mascota = db_get_mascota_por_id(id_mascota)
    if not mascota:
        return "<h3>Mascota no encontrada</h3><a href='/'>Regresar</a>", 404

    html_detail = BASE_CSS + """
    <div class='navbar'>
      <a href='/' class='navbar-brand'>🐾 Ubican<span>ID</span></a>
      <div class='nav-user'><a href='/' style='color:var(--blue); text-decoration:none; font-weight:700;'>← Volver a la Lista</a></div>
    </div>
    
    <div class='main-container'>
      <div class='detail-layout'>
        <div>
          {% if m.principal %}
            <img class='detail-img' src='{{ m.principal }}' alt='{{ m.nombre }}'>
          {% else %}
            <div class='detail-img' style='display:flex; align-items:center; justify-content:center; color:var(--gray); font-weight:bold;'>Sin foto disponible</div>
          {% endif %}
        </div>
        
        <div class='detail-content'>
          <div class='badge-row'>
            <span class='meta-badge'>🚨 SE BUSCA</span>
            {% if m.recompensa %}<span class='meta-badge reward'>💰 RECOMPENSA: {{ m.recompensa }}</span>{% endif %}
          </div>
          
          <h1 class='detail-title'>{{ m.nombre if m.nombre else 'Mascota Sin Nombre' }}</h1>
          
          <div class='info-block'>
            <h3 style='margin-bottom:10px; color:#475569; font-size:1em;'>📊 DESCRIPCIÓN Y DETALLES</h3>
            <div class='info-row'><div class='info-label'>Fecha Pérdida:</div><div class='info-val'>{{ m.fecha if m.fecha else 'No indicada' }}</div></div>
            <div class='info-row'><div class='info-label'>Raza:</div><div class='info-val'>{{ m.raza if m.raza else 'No especificada' }}</div></div>
            <div class='info-row'><div class='info-label'>Edad:</div><div class='info-val'>{{ m.edad if m.edad else 'No especificada' }}</div></div>
            <div class='info-row'><div class='info-label'>Género:</div><div class='info-val'>{{ m.genero if m.genero else 'No especificado' }}</div></div>
            <div class='info-row'><div class='info-label'>Color:</div><div class='info-val'>{{ m.color if m.color else 'No especificado' }}</div></div>
            <div class='info-row'><div class='info-label'>Collar:</div><div class='info-val'>{{ m.collar if m.collar else 'No' }}</div></div>
            <div class='info-row'><div class='info-label'>¿Es Dócil?:</div><div class='info-val'>{{ m.docil if m.docil else 'Desconocido' }}</div></div>
            
            <h3 style='margin:20px 0 10px 0; color:#475569; font-size:1em;'>📍 UBICACIÓN DEL EXTRAVÍO</h3>
            <div class='info-row'><div class='info-label'>Zona/Colonia:</div><div class='info-val' style='font-weight:700; color:#ff6b4a;'>{{ m.zona }}</div></div>
            <div class='info-row'><div class='info-label'>Dirección:</div><div class='info-val'>{{ m.direccion if m.direccion else 'No especificada' }}</div></div>
            <div class='info-row'><div class='info-label'>Entre Calles:</div><div class='info-val'>{{ m.calles if m.calles else 'No especificadas' }}</div></div>
            <div class='info-row'><div class='info-label'>Ciudad/Estado:</div><div class='info-val'>{{ m.ciudad }}, {{ m.estado }} {% if m.cp %}(CP: {{ m.cp }}){% endif %}</div></div>

            <h3 style='margin:20px 0 10px 0; color:#475569; font-size:1em;'>👤 DATOS DE CONTACTO</h3>
            <div class='info-row'><div class='info-label'>Dueño:</div><div class='info-val'>{{ m.dueno if m.dueno else 'Anónimo' }}</div></div>
            <div class='info-row' style='border-bottom:none;'><div class='info-label'>Teléfono:</div><div class='info-val' style='font-weight:bold; color:var(--blue);'>{{ m.contacto }}</div></div>
          </div>

          <div class='info-block' style='margin-top:-5px;'>
            <h4 style='font-size:0.85em; color:var(--gray); margin-bottom:4px;'>INFORMACIÓN ADICIONAL / COMENTARIOS</h4>
            <p style='line-height:1.5; font-size:0.95em;'>{{ m.descripcion if m.descripcion else 'Sin comentarios adicionales.' }}</p>
          </div>
          
          <a href='https://wa.me/{{ m.contacto }}' target='_blank' class='btn-primary' style='background:#25d366; font-size:1.1em;'>
            💬 Mandar WhatsApp al Dueño
          </a>
        </div>
      </div>
    </div>"""
    return render_template_string(html_detail, m=mascota)


# ─── FORMULARIO DE EDICIÓN (ACTUALIZADO CON TODOS LOS CAMPOS) ─────────────────
@app.route('/mascota/editar/<id_mascota>', methods=['GET', 'POST'])
def editar_mascota(id_mascota):
    usuario = session.get("telefono")
    if not usuario: return redirect(url_for('login'))
    
    mascota = db_get_mascota_por_id(id_mascota)
    if not mascota or (mascota['reportado_por'] != usuario and request.args.get('admin') != ADMIN_TOKEN):
        return "No autorizado", 403

    if request.method == 'POST':
        update_data = {
            "nombre":       request.form.get("nombre"),
            "descripcion":  request.form.get("descripcion"),
            "zona":         request.form.get("zona"),
            "contacto":     request.form.get("contacto"),
            "fecha":        request.form.get("fecha"),
            "edad":         request.form.get("edad"),
            "raza":         request.form.get("raza"),
            "genero":       request.form.get("genero"),
            "color":        request.form.get("color"),
            "collar":       request.form.get("collar"),
            "docil":        request.form.get("docil"),
            "direccion":    request.form.get("direccion"),
            "ciudad":       request.form.get("ciudad"),
            "estado":       request.form.get("estado"),
            "cp":           request.form.get("cp"),
            "calles":       request.form.get("calles"),
            "dueno":        request.form.get("dueno"),
            "recompensa":   request.form.get("recompensa")
        }
        nueva_foto = request.files.get("imagen_principal")
        if nueva_foto and nueva_foto.filename != '':
            delete_from_supabase_storage(mascota.get("principal"))
            update_data["principal"] = upload_to_supabase_storage(nueva_foto)

        db_update_mascota(id_mascota, update_data)
        return redirect(url_for('index'))

    html_edit = BASE_CSS + """
    <div class='auth-wrap' style='padding: 50px 16px;'>
      <div class='auth-box' style='max-width:600px; border-radius:24px;'>
        <h1 style='font-size:1.5em; margin-bottom:20px;'>✏️ Editar Reporte</h1>
        <form method='POST' enctype='multipart/form-data'>
          
          <div class='form-section'>
            <h4>1. Datos Básicos</h4>
            <div class='form-grid-2'>
              <div class='form-group'><label>Nombre</label><input type='text' name='nombre' value='{{ m.nombre }}' required></div>
              <div class='form-group'><label>Fecha</label><input type='date' name='fecha' value='{{ m.fecha }}'></div>
            </div>
            <div class='form-group'><label>Descripción</label><textarea name='descripcion' rows='2'>{{ m.descripcion }}</textarea></div>
          </div>

          <div class='form-section'>
            <h4>2. Características Físicas</h4>
            <div class='form-grid-2'>
              <div class='form-group'><label>Raza</label><input type='text' name='raza' value='{{ m.raza }}'></div>
              <div class='form-group'><label>Edad</label><input type='text' name='edad' value='{{ m.edad }}'></div>
            </div>
            <div class='form-grid-2'>
              <div class='form-group'>
                <label>Género</label>
                <select name='genero'>
                  <option value='Macho' {% if m.genero == 'Macho' %}selected{% endif %}>Macho</option>
                  <option value='Hembra' {% if m.genero == 'Hembra' %}selected{% endif %}>Hembra</option>
                </select>
              </div>
              <div class='form-group'><label>Color</label><input type='text' name='color' value='{{ m.color }}'></div>
            </div>
            <div class='form-grid-2'>
              <div class='form-group'><label>Collar</label><input type='text' name='collar' value='{{ m.collar }}'></div>
              <div class='form-group'><label>¿Es Dócil?</label><input type='text' name='docil' value='{{ m.docil }}'></div>
            </div>
          </div>

          <div class='form-section'>
            <h4>3. Ubicación</h4>
            <div class='form-grid-2'>
              <div class='form-group'><label>Zona/Colonia</label><input type='text' name='zona' value='{{ m.zona }}' required></div>
              <div class='form-group'><label>Dirección</label><input type='text' name='direccion' value='{{ m.direccion }}'></div>
            </div>
            <div class='form-group'><label>Entre Calles</label><input type='text' name='calles' value='{{ m.calles }}'></div>
            <div class='form-grid-2'>
              <div class='form-group'><label>Ciudad</label><input type='text' name='ciudad' value='{{ m.ciudad }}'></div>
              <div class='form-group'><label>Estado</label><input type='text' name='estado' value='{{ m.estado }}'></div>
            </div>
          </div>

          <div class='form-section'>
            <h4>4. Dueño y Recompensa</h4>
            <div class='form-grid-2'>
              <div class='form-group'><label>Dueño</label><input type='text' name='dueno' value='{{ m.dueno }}'></div>
              <div class='form-group'><label>Contacto</label><input type='tel' name='contacto' value='{{ m.contacto }}' required></div>
            </div>
            <div class='form-group'><label>Recompensa</label><input type='text' name='recompensa' value='{{ m.recompensa }}'></div>
          </div>

          <div class='form-group'><label>Actualizar Foto (Opcional)</label><input type='file' name='imagen_principal' accept='image/*'></div>
          
          <button type='submit' class='btn-primary'>💾 Guardar Todos los Cambios</button>
          <a href='/' style='display:block;text-align:center;margin-top:15px;color:var(--gray);text-decoration:none;'>Cancelar</a>
        </form>
      </div>
    </div>"""
    return render_template_string(html_edit, m=mascota)

@app.route('/mascota/eliminar/<id_mascota>')
def eliminar_mascota(id_mascota):
    usuario = session.get("telefono")
    if not usuario: return redirect(url_for('login'))

    mascota = db_get_mascota_por_id(id_mascota)
    if not mascota or (mascota['reportado_por'] != usuario and request.args.get('admin') != ADMIN_TOKEN):
        return "No autorizado", 403

    delete_from_supabase_storage(mascota.get("principal"))
    db_delete_mascota(id_mascota)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
