import os
import time
import random
import requests
from flask import Flask, request, render_template_string, redirect, url_for, session
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Cargar variables de entorno
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
    payload = {
        "telefono": telefono,
        "creado": int(time.time()),
        "password_hash": password_hash
    }
    headers = {**SUPABASE_HEADERS, "Prefer": "resolution=merge-duplicates"}
    try:
        requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"⚠️ Error db_save_usuario: {e}")

def db_get_mascotas():
    url = f"{SUPABASE_URL}/rest/v1/mascotas?order=id.desc"
    try:
        r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10)
        return r.json() if isinstance(r.json(), list) else []
    except Exception as e:
        print(f"⚠️ Error db_get_mascotas: {e}")
        return []

def db_save_mascota(datos):
    url = f"{SUPABASE_URL}/rest/v1/mascotas"
    try:
        requests.post(url, json=datos, headers=SUPABASE_HEADERS, timeout=10)
    except Exception as e:
        print(f"⚠️ Error db_save_mascota: {e}")

# ─── MANEJO DE OTP EN BASE DE DATOS ───────────────────────────────────────────
def db_guardar_otp(telefono, codigo):
    url = f"{SUPABASE_URL}/rest/v1/otps"
    payload = {
        "telefono": telefono,
        "code": codigo,
        "expires": time.time() + 300
    }
    headers = {**SUPABASE_HEADERS, "Prefer": "resolution=merge-duplicates"}
    try:
        requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"⚠️ Error db_guardar_otp: {e}")

def db_verificar_otp(telefono, codigo):
    url = f"{SUPABASE_URL}/rest/v1/otps?telefono=eq.{telefono}"
    try:
        r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10).json()
        if not r or not isinstance(r, list):
            return False, "No se solicitó un código para este número."
        
        entry = r[0]
        if time.time() > entry["expires"]:
            requests.delete(url, headers=SUPABASE_HEADERS, timeout=10)
            return False, "El código expiró. Solicita uno nuevo."
            
        if entry["code"] != codigo.strip():
            return False, "Código incorrecto."
            
        requests.delete(url, headers=SUPABASE_HEADERS, timeout=10)
        return True, "OK"
    except Exception as e:
        return False, f"Error de verificación: {e}"

# ─── MANEJO DE STORAGE (SUBIDA DE IMÁGENES) ───────────────────────────────────
def upload_to_supabase_storage(file_field):
    if not file_field or file_field.filename == '':
        return ""
    try:
        nombre_archivo = f"{int(time.time()*1000)}_{file_field.filename}"
        upload_url = f"{SUPABASE_URL}/storage/v1/object/imagenes_mascotas/{nombre_archivo}"
        
        archivo_bytes = file_field.read()
        headers_storage = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": file_field.content_type
        }
        
        res = requests.post(upload_url, data=archivo_bytes, headers=headers_storage, timeout=15)
        if res.status_code == 200:
            return f"{SUPABASE_URL}/storage/v1/object/public/imagenes_mascotas/{nombre_archivo}"
        else:
            print(f"❌ Error Storage HTTP {res.status_code}: {res.text}")
            return ""
    except Exception as e:
        print(f"⚠️ Excepción al subir imagen: {e}")
        return ""

# ─── SEGURIDAD DE CONTRASEÑAS ─────────────────────────────────────────────────
def hash_password(password):
    return generate_password_hash(password, method='scrypt')

def verify_password(password, hashed):
    return check_password_hash(hashed, password)

def user_has_password(telefono):
    u = db_get_usuario(telefono)
    return u is not None and bool(u.get("password_hash"))

def generar_otp():
    return str(random.randint(100000, 999999))

def enviar_sms_otp(telefono, codigo):
    payload = {
        "message": f"Tu código de verificación Ubican ID es: {codigo}. Válido 5 minutos.",
        "recipient": [{"msisdn": telefono}],
    }
    if LABSMOBILE_SENDER:
        payload["tpoa"] = LABSMOBILE_SENDER
    try:
        r = requests.post(
            LABSMOBILE_API,
            json=payload,
            auth=(LABSMOBILE_USER, LABSMOBILE_TOKEN),
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
            timeout=10,
        )
        return r.status_code == 200, r.text
    except Exception as e:
        return False, str(e)

# ─── ERROR HANDLER SEGURO ─────────────────────────────────────────────────────
@app.errorhandler(500)
def handle_500(e):
    return """<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'><title>Error</title></head>
    <body style='font-family:system-ui;padding:20px;text-align:center;'>
    <h2 style='color:#ef4444'>⚠️ Error interno en el servidor</h2>
    <p style='color:#64748b'>Por favor, inténtalo de nuevo más tarde.</p></body></html>""", 500

# ─── VISTAS DE AUTENTICACIÓN ──────────────────────────────────────────────────
BASE_CSS = """
<meta name='viewport' content='width=device-width, initial-scale=1, maximum-scale=1'>
<style>
:root {
  --grad: linear-gradient(135deg,#ff6b4a,#ff9f43);
  --dark: #1e293b; --bg: #f8fafc; --card: #ffffff; --gray: #64748b;
  --success: #10b981; --danger: #ef4444;
}
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:system-ui,-apple-system,sans-serif; background:var(--bg); color:var(--dark); }
.navbar { background:rgba(255,255,255,.85); backdrop-filter:blur(12px); position:sticky; top:0; z-index:90; padding:16px 24px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; }
.navbar-brand { font-size:1.2em; font-weight:800; text-decoration:none; color:inherit; }
.navbar-brand span { background:var(--grad); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.nav-user { font-size:0.85em; color:var(--gray); display:flex; align-items:center; gap:12px; }
.nav-user a { color:var(--danger); font-weight:600; text-decoration:none; }
.auth-wrap { min-height:100vh; display:flex; align-items:center; justify-content:center; padding:24px 16px; }
.auth-box { background:var(--card); border-radius:28px; border:1px solid #e2e8f0; padding:36px 32px; width:100%; max-width:420px; box-shadow:0 8px 24px -8px rgba(0,0,0,.08); }
.auth-box h1 { font-size:1.6em; font-weight:800; margin-bottom:6px; }
.auth-box p.sub { color:var(--gray); font-size:0.9em; margin-bottom:28px; }
.form-group { margin-bottom:18px; }
.form-group label { display:block; font-size:0.82em; font-weight:700; margin-bottom:6px; color:#475569; }
.form-group input, .form-group textarea { width:100%; padding:13px 14px; border:1px solid #cbd5e1; border-radius:12px; font-size:1em; background:#f8fafc; outline:none; }
.form-group input:focus { border-color:#ff9f43; }
.btn-primary { background:var(--grad); color:white; border:none; width:100%; padding:14px; border-radius:12px; font-weight:700; font-size:1em; cursor:pointer; min-height:48px; }
.btn-secondary { background:#f1f5f9; color:var(--dark); border:none; width:100%; padding:13px; border-radius:12px; font-weight:600; cursor:pointer; margin-top:10px; min-height:46px; }
.alert { padding:12px 16px; border-radius:12px; font-size:0.9em; margin-bottom:18px; }
.alert-error { background:#fef2f2; color:#991b1b; border:1px solid #fecaca; }
.alert-success { background:#f0fdf4; color:#166534; border:1px solid #bbf7d0; }
.link-row { text-align:center; margin-top:20px; font-size:0.88em; color:var(--gray); }
.link-row a { color:#ff6b4a; font-weight:600; text-decoration:none; }
.otp-inputs { display:flex; gap:8px; justify-content:center; }
.otp-inputs input { width:45px; height:45px; text-align:center; font-size:1.4em; font-weight:700; border:2px solid #cbd5e1; border-radius:12px; }
.main-container { max-width:1100px; margin:40px auto; padding:0 24px; }
.grid-feed { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:24px; margin-top:24px; }
.card-minimal { background:var(--card); border-radius:20px; border:1px solid #e2e8f0; overflow:hidden; display:flex; flex-direction:column; height:100%; position:relative; }
.card-img-box { width:100%; aspect-ratio:4/3; background:#f1f5f9; position:relative; }
.card-img-box img { width:100%; height:100%; object-fit:cover; }
.card-badge { position:absolute; top:12px; right:12px; background:#ef4444; color:white; font-size:.7em; font-weight:800; padding:4px 10px; border-radius:99px; }
.card-info { padding:16px; display:flex; flex-direction:column; gap:4px; }
.form-report { background:#fff; padding:24px; border-radius:20px; border:1px solid #e2e8f0; margin-bottom:32px; }
</style>
"""

@app.route('/registro', methods=['GET','POST'])
def registro():
    error = ""
    if request.method == 'POST':
        telefono = request.form.get("telefono","").strip()
        if not telefono:
            error = "Ingresa tu número de WhatsApp."
        elif db_get_usuario(telefono):
            error = "Este número ya está registrado."
        else:
            codigo = generar_otp()
            db_guardar_otp(telefono, codigo)
            ok, _ = enviar_sms_otp(telefono, codigo)
            if ok:
                return redirect(url_for('verificar_registro', tel=telefono))
            error = "No se pudo enviar el SMS. Intenta de nuevo."

    html = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box'>
        <h1>🐾 Crear cuenta</h1>
        <p class='sub'>Ingresa tu número de WhatsApp con código de país.</p>
        {% if error %}<div class='alert alert-error'>{{ error }}</div>{% endif %}
        <form method='POST'>
          <div class='form-group'>
            <label>Número de WhatsApp</label>
            <input type='tel' name='telefono' placeholder='Ej. 526561234567' autofocus>
          </div>
          <button class='btn-primary' type='submit'>Enviar código SMS →</button>
        </form>
        <div class='link-row'>¿Ya tienes cuenta? <a href='/login'>Inicia sesión</a></div>
      </div>
    </div>"""
    return render_template_string(html, error=error)

@app.route('/registro/verificar', methods=['GET','POST'])
def verificar_registro():
    telefono = request.args.get("tel","")
    reenvio  = request.args.get("reenvio","")
    error = ""
    if not telefono:
        return redirect(url_for('registro'))

    if request.method == 'POST':
        digits = [request.form.get(f"d{i}","") for i in range(1,7)]
        codigo = "".join(digits)
        ok, msg = db_verificar_otp(telefono, codigo)
        if ok:
            db_save_usuario(telefono, "") # Guardar temporalmente sin clave
            session["pending_password_phone"] = telefono
            return redirect(url_for('crear_password'))
        error = msg

    html = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box'>
        <h1>✅ Verifica tu número</h1>
        <p class='sub'>Ingresa el código enviado al <strong>{{ tel }}</strong>.</p>
        {% if error %}<div class='alert alert-error'>{{ error }}</div>{% endif %}
        <form method='POST'>
          <div class='otp-inputs'>
            {% for i in range(1, 7) %}
            <input type='text' name='d{{i}}' maxlength='1' inputmode='numeric'>
            {% endfor %}
          </div>
          <button class='btn-primary' type='submit' style='margin-top:20px'>Verificar →</button>
        </form>
      </div>
    </div>"""
    return render_template_string(html, tel=telefono, error=error, reenvio=reenvio)

@app.route('/crear-password', methods=['GET','POST'])
def crear_password():
    telefono = session.get("pending_password_phone")
    if not telefono:
        return redirect(url_for('registro'))

    error = ""
    if request.method == 'POST':
        pwd1 = request.form.get("password","")
        pwd2 = request.form.get("password2","")
        if len(pwd1) < 6:
            error = "La contraseña debe tener al menos 6 caracteres."
        elif pwd1 != pwd2:
            error = "Las contraseñas no coinciden."
        else:
            db_save_usuario(telefono, hash_password(pwd1))
            session.pop("pending_password_phone", None)
            session["telefono"] = telefono
            return redirect(url_for('index'))

    html = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box'>
        <h1>🔑 Crea tu contraseña</h1>
        {% if error %}<div class='alert alert-error'>{{ error }}</div>{% endif %}
        <form method='POST'>
          <div class='form-group'>
            <label>Contraseña (mínimo 6 caracteres)</label>
            <input type='password' name='password' placeholder='••••••••' autofocus>
          </div>
          <div class='form-group'>
            <label>Repetir contraseña</label>
            <input type='password' name='password2' placeholder='••••••••'>
          </div>
          <button class='btn-primary' type='submit'>Guardar y entrar →</button>
        </form>
      </div>
    </div>"""
    return render_template_string(html, error=error)

@app.route('/login', methods=['GET','POST'])
def login():
    error = ""
    if request.method == 'POST':
        telefono = request.form.get("telefono","").strip()
        if not telefono:
            error = "Ingresa tu número."
        elif not db_get_usuario(telefono):
            error = "Número no registrado."
        else:
            if user_has_password(telefono):
                return redirect(url_for('login_password', tel=telefono))
            else:
                codigo = generar_otp()
                db_guardar_otp(telefono, codigo)
                ok, _ = enviar_sms_otp(telefono, codigo)
                if ok:
                    return redirect(url_for('verificar_login_otp', tel=telefono))
                error = "No se pudo enviar el SMS."

    html = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box'>
        <h1>🔐 Iniciar sesión</h1>
        {% if error %}<div class='alert alert-error'>{{ error }}</div>{% endif %}
        <form method='POST'>
          <div class='form-group'>
            <label>Número de WhatsApp</label>
            <input type='tel' name='telefono' placeholder='Ej. 526561234567' autofocus>
          </div>
          <button class='btn-primary' type='submit'>Continuar →</button>
        </form>
        <div class='link-row'>¿No tienes cuenta? <a href='/registro'>Regístrate</a></div>
      </div>
    </div>"""
    return render_template_string(html, error=error)

@app.route('/login/password', methods=['GET','POST'])
def login_password():
    telefono = request.args.get("tel","")
    error = ""
    if not telefono:
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form.get("password","")
        usuario = db_get_usuario(telefono)
        if usuario and verify_password(password, usuario.get("password_hash","")):
            session["telefono"] = telefono
            return redirect(url_for('index'))
        error = "Contraseña incorrecta."

    html = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box'>
        <h1>🔑 Ingresa tu contraseña</h1>
        {% if error %}<div class='alert alert-error'>{{ error }}</div>{% endif %}
        <form method='POST'>
          <div class='form-group'>
            <label>Contraseña</label>
            <input type='password' name='password' placeholder='••••••••' autofocus>
          </div>
          <button class='btn-primary' type='submit'>Entrar →</button>
        </form>
      </div>
    </div>"""
    return render_template_string(html, error=error)

@app.route('/login/verificar', methods=['GET','POST'])
def verificar_login_otp():
    telefono = request.args.get("tel","")
    error = ""
    if not telefono:
        return redirect(url_for('login'))

    if request.method == 'POST':
        digits = [request.form.get(f"d{i}","") for i in range(1,7)]
        codigo = "".join(digits)
        ok, msg = db_verificar_otp(telefono, codigo)
        if ok:
            session["telefono"] = telefono
            session["pending_password_phone"] = telefono
            return redirect(url_for('crear_password'))
        error = msg

    html = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box'>
        <h1>✅ Código de acceso</h1>
        {% if error %}<div class='alert alert-error'>{{ error }}</div>{% endif %}
        <form method='POST'>
          <div class='otp-inputs'>
            {% for i in range(1, 7) %}
            <input type='text' name='d{{i}}' maxlength='1' inputmode='numeric'>
            {% endfor %}
          </div>
          <button class='btn-primary' type='submit' style='margin-top:20px'>Verificar →</button>
        </form>
      </div>
    </div>"""
    return render_template_string(html, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ─── FEED PRINCIPAL ───────────────────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
def index():
    token_ingresado = request.args.get('admin')
    es_admin  = (token_ingresado == ADMIN_TOKEN)
    usuario   = session.get("telefono")
    mascotas_perdidas = db_get_mascotas()

    if request.method == 'POST':
        if not usuario:
            return redirect(url_for('login'))

        nombre = request.form.get("nombre","").strip()
        if nombre:
            # Subir imágenes directamente al Storage Bucket de Supabase
            url_principal = upload_to_supabase_storage(request.files.get("imagen_principal"))
            
            lista_secundarias = []
            for archivo in request.files.getlist("imagenes_secundarias")[:4]:
                url_s = upload_to_supabase_storage(archivo)
                if url_s:
                    lista_secundarias.append(url_s)

            nuevo = {
                "id":           str(int(time.time() * 1000)),
                "reportado_por": usuario,
                "nombre":       nombre,
                "descripcion":  request.form.get("descripcion"),
                "zona":         request.form.get("zona"),
                "contacto":     request.form.get("contacto"),
                "principal":    url_principal,
                "secundarias":  lista_secundarias,
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
                "recompensa":   request.form.get("recompensa"),
            }
            db_save_mascota(nuevo)

        if es_admin:
            return redirect(url_for('index', admin=ADMIN_TOKEN))
        return redirect(url_for('index'))

    html_index = BASE_CSS + """
    <div class='navbar'>
      <a href='/' class='navbar-brand'>🐾 Ubican<span>ID</span></a>
      <div class='nav-user'>
        {% if usuario %}
          <span>📱 {{ usuario }}</span> | <a href='/logout'>Salir</a>
        {% else %}
          <a href='/login' style='color:#ff6b4a'>Entrar / Registrarse</a>
        {% endif %}
      </div>
    </div>

    <div class='main-container'>
      {% if usuario %}
      <div class='form-report'>
        <h3>📢 Reportar Mascota Perdida</h3><br>
        <form method='POST' enctype='multipart/form-data'>
          <div class='form-group'>
            <label>Nombre de la mascota</label>
            <input type='text' name='nombre' required>
          </div>
          <div class='form-group'>
            <label>Descripción / Señas particulares</label>
            <textarea name='descripcion' rows='2'></textarea>
          </div>
          <div class='form-group'>
            <label>Zona / Colonia donde se perdió</label>
            <input type='text' name='zona' required>
          </div>
          <div class='form-group'>
            <label>Teléfono de Contacto</label>
            <input type='text' name='contacto' required>
          </div>
          <div class='form-group'>
            <label>Foto Principal</label>
            <input type='file' name='imagen_principal' accept='image/*'>
          </div>
          <div class='form-group'>
            <label>Fotos Secundarias (Máx. 4)</label>
            <input type='file' name='imagenes_secundarias' accept='image/*' multiple>
          </div>
          <button type='submit' class='btn-primary'>Publicar Reporte</button>
        </form>
      </div>
      {% endif %}

      <h2>Mascotas Buscando su Hogar</h2>
      <div class='grid-feed'>
        {% for m in mascotas %}
        <div class='card-minimal'>
          <div class='card-img-box'>
            {% if m.principal %}
              <img src='{{ m.principal }}' alt='Mascota'>
            {% else %}
              <div style='padding:40px; text-align:center; color:#94a3b8;'>Sin foto</div>
            {% endif %}
            <span class='card-badge'>PERDIDO</span>
          </div>
          <div class='card-info'>
            <h3>{{ m.nombre }}</h3>
            <p>{{ m.descripcion }}</p>
            <p style='margin-top:6px;'>📍 <strong>Zona:</strong> {{ m.zona }}</p>
            <p>📞 <strong>Contacto:</strong> {{ m.contacto }}</p>
          </div>
        </div>
        {% else %}
        <p style='color:var(--gray)'>No hay reportes de mascotas perdidas por el momento.</p>
        {% endfor %}
      </div>
    </div>
    """
    return render_template_string(html_index, mascotas=mascotas_perdidas, usuario=usuario)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
