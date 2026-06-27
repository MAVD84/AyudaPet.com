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

# ─── CSS BASE ─────────────────────────────────────────────────────────────────
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
.form-group { margin-bottom:18px; }
.form-group label { display:block; font-size:0.82em; font-weight:700; margin-bottom:6px; color:#475569; }
.form-group input, .form-group textarea { width:100%; padding:13px 14px; border:1px solid #cbd5e1; border-radius:12px; font-size:1em; background:#f8fafc; outline:none; }
.form-group input:focus { border-color:#ff9f43; }
.btn-primary { background:var(--grad); color:white; border:none; width:100%; padding:14px; border-radius:12px; font-weight:700; font-size:1em; cursor:pointer; min-height:48px; text-decoration:none; display:inline-block; text-align:center;}
.alert-error { background:#fef2f2; color:#991b1b; border:1px solid #fecaca; padding:12px; border-radius:12px; margin-bottom:15px;}
.otp-inputs { display:flex; gap:8px; justify-content:center; }
.otp-inputs input { width:45px; height:45px; text-align:center; font-size:1.4em; font-weight:700; border:2px solid #cbd5e1; border-radius:12px; }
.main-container { max-width:1100px; margin:40px auto; padding:0 24px; }
.grid-feed { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:24px; margin-top:24px; }

/* Tarjetas como Enlaces */
.card-link { text-decoration: none; color: inherit; display: block; height: 100%; transition: transform 0.2s, box-shadow 0.2s; }
.card-link:hover { transform: translateY(-4px); }
.card-minimal { background:var(--card); border-radius:20px; border:1px solid #e2e8f0; overflow:hidden; display:flex; flex-direction:column; height:100%; position:relative; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); }
.card-img-box { width:100%; aspect-ratio:4/3; background:#f1f5f9; position:relative; }
.card-img-box img { width:100%; height:100%; object-fit:cover; }
.card-badge { position:absolute; top:12px; right:12px; background:#ef4444; color:white; font-size:.7em; font-weight:800; padding:4px 10px; border-radius:99px; }
.card-info { padding:16px; display:flex; flex-direction:column; gap:4px; flex-grow:1; }
.card-info h3 { font-size:1.15em; margin-bottom:4px; color:var(--dark); }
.card-info p { font-size:0.9em; color:var(--gray); line-height:1.4; }

.card-actions { padding:12px 16px; border-top:1px solid #f1f5f9; background:#f8fafc; display:flex; gap:8px; position: relative; z-index: 10; }
.btn-action { flex:1; text-align:center; padding:8px; border-radius:8px; font-size:0.85em; font-weight:600; text-decoration:none; border:none; cursor:pointer; }
.btn-edit { background:#e0f2fe; color:#0369a1; }
.btn-delete { background:#fee2e2; color:#b91c1c; }
.form-report { background:#fff; padding:24px; border-radius:20px; border:1px solid #e2e8f0; margin-bottom:32px; }

/* Estilos de Vista Detalle */
.detail-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 20px; }
@media (max-width: 768px) { .detail-layout { grid-template-columns: 1fr; gap: 24px; } }
.detail-img { width: 100%; border-radius: 24px; border: 1px solid #e2e8f0; aspect-ratio: 4/3; object-fit: cover; background: #f1f5f9; }
.detail-content { display: flex; flex-direction: column; gap: 16px; }
.detail-title { font-size: 2.2em; font-weight: 800; }
.meta-badge { display: inline-block; background: #fee2e2; color: #b91c1c; font-weight: 700; padding: 6px 14px; border-radius: 99px; font-size: 0.85em; width: max-content; }
.info-row { display: flex; padding: 12px 0; border-bottom: 1px solid #e2e8f0; font-size: 1.05em; }
.info-label { width: 130px; font-weight: 700; color: #475569; }
.info-val { color: var(--dark); flex: 1; }
</style>
"""

# ─── VISTAS DE AUTENTICACIÓN ──────────────────────────────────────────────────
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

# ─── NÚCLEO CRUD DE MASCOTAS ──────────────────────────────────────────────────

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
                "nombre": nombre,
                "descripcion": request.form.get("descripcion"),
                "zona": request.form.get("zona"),
                "contacto": request.form.get("contacto"),
                "principal": url_p,
                "secundarias": []
            }
            db_save_mascota(nuevo)
        return redirect(url_for('index', admin=ADMIN_TOKEN if es_admin else None))

    html_index = BASE_CSS + """
    <div class='navbar'>
      <a href='/' class='navbar-brand'>🐾 Ubican<span>ID</span></a>
      <div class='nav-user'>
        {% if usuario %}<span>📱 {{ usuario }}</span> | <a href='/logout'>Salir</a>{% else %}<a href='/login'>Entrar</a>{% endif %}
      </div>
    </div>
    <div class='main-container'>
      {% if usuario %}
      <div class='form-report'>
        <h3>📢 Publicar nueva mascota extraviada</h3><br>
        <form method='POST' enctype='multipart/form-data'>
          <div class='form-group'><label>Nombre</label><input type='text' name='nombre' required></div>
          <div class='form-group'><label>Descripción</label><textarea name='descripcion'></textarea></div>
          <div class='form-group'><label>Zona o Colonia</label><input type='text' name='zona' required></div>
          <div class='form-group'><label>Teléfono de Contacto</label><input type='text' name='contacto' required></div>
          <div class='form-group'><label>Foto de la Mascota</label><input type='file' name='imagen_principal' accept='image/*'></div>
          <button type='submit' class='btn-primary'>Publicar Reporte</button>
        </form>
      </div>
      {% endif %}
      
      <h2>Reportes Activos</h2>
      <div class='grid-feed'>
        {% for m in mascotas %}
        <div style='display: flex; flex-direction: column; height: 100%; position: relative;'>
          <a href='/mascota/{{ m.id }}' class='card-link'>
            <div class='card-minimal'>
              <div class='card-img-box'>
                {% if m.principal %}<img src='{{ m.principal }}'>{% else %}<div style='padding:40px;text-align:center;color:var(--gray);'>Sin foto</div>{% endif %}
                <span class='card-badge'>PERDIDO</span>
              </div>
              <div class='card-info'>
                <h3>{{ m.nombre }}</h3>
                <p>{{ m.descripcion if m.descripcion|length < 80 else m.descripcion[:80] ~ '...' }}</p>
                <p style='font-size:0.85em; margin-top:auto; font-weight: 600;'>📍 {{ m.zona }}</p>
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


# ─── NUEVA VISTA DETALLADA DE LA MASCOTA ──────────────────────────────────────
@app.route('/mascota/<id_mascota>')
def ver_mascota(id_mascota):
    mascota = db_get_mascota_por_id(id_mascota)
    if not mascota:
        return "<h3>Mascota no encontrada</h3><a href='/'>Regresar</a>", 404

    html_detail = BASE_CSS + """
    <div class='navbar'>
      <a href='/' class='navbar-brand'>🐾 Ubican<span>ID</span></a>
      <div class='nav-user'><a href='/' style='color:var(--blue); text-decoration:none; font-weight:700;'>← Volver al inicio</a></div>
    </div>
    
    <div class='main-container'>
      <div class='detail-layout'>
        <div>
          {% if m.principal %}
            <img class='detail-img' src='{{ m.principal }}' alt='{{ m.nombre }}'>
          {% else %}
            <div class='detail-img' style='display:flex; align-items:center; justify-content:center; color:var(--gray);'>Sin Imagen Adjunta</div>
          {% endif %}
        </div>
        
        <div class='detail-content'>
          <span class='meta-badge'>🚨 SE BUSCA</span>
          <h1 class='detail-title'>{{ m.nombre }}</h1>
          
          <div style='background: white; padding: 20px; border-radius: 20px; border: 1px solid #e2e8f0; margin-top: 10px;'>
            <div class='info-row'>
              <div class='info-label'>📍 Zona:</div>
              <div class='info-val'>{{ m.zona }}</div>
            </div>
            <div class='info-row'>
              <div class='info-label'>📞 Contacto:</div>
              <div class='info-val'>
                <a href='tel:{{ m.contacto }}' style='color:var(--blue); text-decoration:none; font-weight:600;'>{{ m.contacto }}</a>
              </div>
            </div>
            <div class='info-row' style='border-bottom:none; flex-direction:column; gap:8px;'>
              <div class='info-label' style='width:100%;'>📝 Descripción Completa:</div>
              <div class='info-val' style='line-height:1.6;'>{{ m.descripcion if m.descripcion else 'Sin descripción adicional proporcionada.' }}</div>
            </div>
          </div>
          
          <a href='https://wa.me/{{ m.contacto }}' target='_blank' class='btn-primary' style='background:#25d366; margin-top:10px;'>
            💬 Contactar por WhatsApp
          </a>
        </div>
      </div>
    </div>"""
    return render_template_string(html_detail, m=mascota)


@app.route('/mascota/editar/<id_mascota>', methods=['GET', 'POST'])
def editar_mascota(id_mascota):
    usuario = session.get("telefono")
    if not usuario: return redirect(url_for('login'))
    
    mascota = db_get_mascota_por_id(id_mascota)
    if not mascota or (mascota['reportado_por'] != usuario and request.args.get('admin') != ADMIN_TOKEN):
        return "No autorizado", 403

    if request.method == 'POST':
        update_data = {
            "nombre": request.form.get("nombre"),
            "descripcion": request.form.get("descripcion"),
            "zona": request.form.get("zona"),
            "contacto": request.form.get("contacto")
        }
        nueva_foto = request.files.get("imagen_principal")
        if nueva_foto and nueva_foto.filename != '':
            delete_from_supabase_storage(mascota.get("principal"))
            update_data["principal"] = upload_to_supabase_storage(nueva_foto)

        db_update_mascota(id_mascota, update_data)
        return redirect(url_for('index'))

    html_edit = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box' style='max-width:500px;'>
        <h1>✏️ Editar Perfil</h1><br>
        <form method='POST' enctype='multipart/form-data'>
          <div class='form-group'><label>Nombre</label><input type='text' name='nombre' value='{{ m.nombre }}' required></div>
          <div class='form-group'><label>Descripción</label><textarea name='descripcion'>{{ m.descripcion }}</textarea></div>
          <div class='form-group'><label>Zona</label><input type='text' name='zona' value='{{ m.zona }}' required></div>
          <div class='form-group'><label>Contacto</label><input type='text' name='contacto' value='{{ m.contacto }}' required></div>
          <div class='form-group'><label>Cambiar Foto</label><input type='file' name='imagen_principal' accept='image/*'></div>
          <button type='submit' class='btn-primary'>Guardar Cambios</button>
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
