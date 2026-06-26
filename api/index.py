import os
import json
import time
import random
import base64
import traceback
import requests
from flask import Flask, request, render_template_string, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "ubican_secret_2024"

ADMIN_TOKEN   = "ubican123"
USERS_FILE    = "usuarios.json"
MASCOTAS_FILE = "mascotas.json"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ─── LabsMobile config ────────────────────────────────────────────────────────
LABSMOBILE_USER  = "hola@ubicanid.com"   # ← reemplaza
LABSMOBILE_PASS  = "zuK99as7kNvGDMJtfshF5UnYDEOJa1fA"  # ← reemplaza
LABSMOBILE_API   = "https://api.labsmobile.com/json/send"
# ─────────────────────────────────────────────────────────────────────────────

# Códigos OTP en memoria: { telefono: { "code": "1234", "expires": timestamp } }
otp_store = {}

# ══════════════════════════════════════════════════════════════════════════════
# Helpers JSON
# ══════════════════════════════════════════════════════════════════════════════
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_usuarios():  return load_json(USERS_FILE)
def get_mascotas():  return load_json(MASCOTAS_FILE)

def find_user(telefono):
    return next((u for u in get_usuarios() if u["telefono"] == telefono), None)

# ══════════════════════════════════════════════════════════════════════════════
# Helpers OTP
# ══════════════════════════════════════════════════════════════════════════════
def generar_otp():
    return str(random.randint(100000, 999999))

def enviar_sms_otp(telefono, codigo):
    """Envía el OTP via LabsMobile JSON API."""
    payload = {
        "username": LABSMOBILE_USER,
        "password": LABSMOBILE_PASS,
        "message":  f"Tu código de verificación Ubican ID es: {codigo}. Válido 5 minutos.",
        "tphone":   telefono,
    }
    try:
        r = requests.post(LABSMOBILE_API, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"⚠️ Error SMS: {e}")
        return False

def guardar_otp(telefono, codigo):
    otp_store[telefono] = {"code": codigo, "expires": time.time() + 300}  # 5 min

def verificar_otp(telefono, codigo):
    entry = otp_store.get(telefono)
    if not entry:
        return False, "No se solicitó un código para este número."
    if time.time() > entry["expires"]:
        otp_store.pop(telefono, None)
        return False, "El código expiró. Solicita uno nuevo."
    if entry["code"] != codigo.strip():
        return False, "Código incorrecto."
    otp_store.pop(telefono, None)
    return True, "OK"

# ══════════════════════════════════════════════════════════════════════════════
# Error handler
# ══════════════════════════════════════════════════════════════════════════════
@app.errorhandler(500)
def handle_500(e):
    tb = traceback.format_exc()
    return f"""<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'>
    <title>Error</title></head><body style='font-family:system-ui;padding:20px'>
    <h2 style='color:#ef4444'>⚠️ Error en servidor</h2>
    <pre style='background:#0f172a;color:#38bdf8;padding:16px;border-radius:12px;overflow:auto'>{tb}</pre>
    </body></html>""", 500

# ══════════════════════════════════════════════════════════════════════════════
# Plantillas base (CSS compartido)
# ══════════════════════════════════════════════════════════════════════════════
BASE_CSS = """
<meta name='viewport' content='width=device-width, initial-scale=1, maximum-scale=1'>
<style>
:root {
  --grad: linear-gradient(135deg,#ff6b4a,#ff9f43);
  --dark: #1e293b; --bg: #f8fafc; --card: #ffffff; --gray: #64748b;
  --success: #10b981; --danger: #ef4444;
}
* { box-sizing:border-box; margin:0; padding:0; -webkit-tap-highlight-color:transparent; }
html { -webkit-text-size-adjust:100%; }
body { font-family:system-ui,-apple-system,sans-serif; background:var(--bg); color:var(--dark); }
img { max-width:100%; display:block; }
.navbar { background:rgba(255,255,255,.85); backdrop-filter:blur(12px); position:sticky; top:0; z-index:90;
  padding:16px 24px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center;
  gap:12px; flex-wrap:wrap; }
.navbar-brand { font-size:1.2em; font-weight:800; white-space:nowrap; }
.navbar-brand span { background:var(--grad); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.nav-user { font-size:0.85em; color:var(--gray); display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
.nav-user a { color:var(--danger); font-weight:600; text-decoration:none; }

/* Auth pages */
.auth-wrap { min-height:100vh; display:flex; align-items:center; justify-content:center; padding:24px 16px; }
.auth-box { background:var(--card); border-radius:28px; border:1px solid #e2e8f0;
  padding:36px 32px; width:100%; max-width:420px; box-shadow:0 8px 24px -8px rgba(0,0,0,.08); }
.auth-box h1 { font-size:1.6em; font-weight:800; margin-bottom:6px; }
.auth-box p.sub { color:var(--gray); font-size:0.9em; margin-bottom:28px; }
.form-group { margin-bottom:18px; }
.form-group label { display:block; font-size:0.82em; font-weight:700; margin-bottom:6px; color:#475569; }
.form-group input { width:100%; padding:13px 14px; border:1px solid #cbd5e1; border-radius:12px;
  font-size:1em; font-family:inherit; outline:none; background:#f8fafc; transition:border-color .2s; }
.form-group input:focus { border-color:#ff9f43; }
.btn-primary { background:var(--grad); color:white; border:none; width:100%; padding:14px;
  border-radius:12px; font-weight:700; font-size:1em; cursor:pointer; margin-top:4px; min-height:48px; }
.btn-secondary { background:#f1f5f9; color:var(--dark); border:none; width:100%; padding:13px;
  border-radius:12px; font-weight:600; font-size:0.95em; cursor:pointer; margin-top:10px; min-height:46px; }
.alert { padding:12px 16px; border-radius:12px; font-size:0.9em; margin-bottom:18px; }
.alert-error   { background:#fef2f2; color:#991b1b; border:1px solid #fecaca; }
.alert-success { background:#f0fdf4; color:#166534; border:1px solid #bbf7d0; }
.link-row { text-align:center; margin-top:20px; font-size:0.88em; color:var(--gray); }
.link-row a { color:#ff6b4a; font-weight:600; text-decoration:none; }

/* OTP inputs */
.otp-inputs { display:flex; gap:8px; justify-content:center; margin-bottom:8px; }
.otp-inputs input { width:100%; max-width:48px; aspect-ratio:1/1; height:auto; text-align:center;
  font-size:1.4em; font-weight:700; border:2px solid #cbd5e1; border-radius:14px; background:#f8fafc;
  outline:none; transition:border-color .2s; min-width:0; }
.otp-inputs input:focus { border-color:#ff9f43; }

@media (max-width:480px) {
  .auth-box { padding:28px 20px; border-radius:22px; }
  .auth-box h1 { font-size:1.4em; }
  .otp-inputs { gap:6px; }
  .otp-inputs input { font-size:1.2em; border-radius:12px; }
}
</style>
"""

# ══════════════════════════════════════════════════════════════════════════════
# REGISTRO — paso 1: ingresar teléfono
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/registro', methods=['GET','POST'])
def registro():
    error = ""; success = ""
    if request.method == 'POST':
        telefono = request.form.get("telefono","").strip()
        if not telefono:
            error = "Ingresa tu número de WhatsApp."
        elif find_user(telefono):
            error = "Este número ya está registrado. <a href='/login'>Inicia sesión</a>."
        else:
            codigo = generar_otp()
            guardar_otp(telefono, codigo)
            ok = enviar_sms_otp(telefono, codigo)
            if ok:
                return redirect(url_for('verificar_registro', tel=telefono))
            else:
                error = "No se pudo enviar el SMS. Verifica el número e intenta de nuevo."

    html = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box'>
        <h1>🐾 Crear cuenta</h1>
        <p class='sub'>Ingresa tu número de WhatsApp para recibir un código de verificación.</p>
        {% if error %}<div class='alert alert-error'>{{ error|safe }}</div>{% endif %}
        <form method='POST'>
          <div class='form-group'>
            <label>Número de WhatsApp (con código de país)</label>
            <input type='tel' name='telefono' placeholder='Ej. 526561234567' autofocus>
          </div>
          <button class='btn-primary' type='submit'>Enviar código SMS →</button>
        </form>
        <div class='link-row'>¿Ya tienes cuenta? <a href='/login'>Inicia sesión</a></div>
      </div>
    </div>"""
    return render_template_string(html, error=error)

# ══════════════════════════════════════════════════════════════════════════════
# REGISTRO — paso 2: verificar OTP
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/registro/verificar', methods=['GET','POST'])
def verificar_registro():
    telefono = request.args.get("tel","")
    error = ""
    if not telefono:
        return redirect(url_for('registro'))

    if request.method == 'POST':
        digits = [request.form.get(f"d{i}","") for i in range(1,7)]
        codigo = "".join(digits)
        ok, msg = verificar_otp(telefono, codigo)
        if ok:
            usuarios = get_usuarios()
            nuevo = {"telefono": telefono, "creado": int(time.time())}
            usuarios.append(nuevo)
            save_json(USERS_FILE, usuarios)
            session["telefono"] = telefono
            return redirect(url_for('index'))
        else:
            error = msg

    html = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box'>
        <h1>✅ Verifica tu número</h1>
        <p class='sub'>Ingresa el código de 6 dígitos que enviamos al <strong>{{ tel }}</strong>.</p>
        {% if error %}<div class='alert alert-error'>{{ error }}</div>{% endif %}
        <form method='POST' id='otpForm'>
          <div class='otp-inputs'>
            <input type='text' name='d1' id='d1' maxlength='1' inputmode='numeric'>
            <input type='text' name='d2' id='d2' maxlength='1' inputmode='numeric'>
            <input type='text' name='d3' id='d3' maxlength='1' inputmode='numeric'>
            <input type='text' name='d4' id='d4' maxlength='1' inputmode='numeric'>
            <input type='text' name='d5' id='d5' maxlength='1' inputmode='numeric'>
            <input type='text' name='d6' id='d6' maxlength='1' inputmode='numeric'>
          </div>
          <button class='btn-primary' type='submit' style='margin-top:20px'>Verificar →</button>
        </form>
        <form method='GET' action='/registro/reenviar'>
          <input type='hidden' name='tel' value='{{ tel }}'>
          <button class='btn-secondary' type='submit'>🔄 Reenviar código</button>
        </form>
        <div class='link-row'><a href='/registro'>← Cambiar número</a></div>
      </div>
    </div>
    <script>
      const inputs = document.querySelectorAll('.otp-inputs input');
      inputs.forEach((inp, i) => {
        inp.addEventListener('input', () => {
          if(inp.value && i < inputs.length-1) inputs[i+1].focus();
        });
        inp.addEventListener('keydown', e => {
          if(e.key==='Backspace' && !inp.value && i > 0) inputs[i-1].focus();
        });
      });
      inputs[0].focus();
    </script>"""
    return render_template_string(html, tel=telefono, error=error)

# ══════════════════════════════════════════════════════════════════════════════
# REGISTRO — reenviar OTP
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/registro/reenviar')
def reenviar_otp_registro():
    telefono = request.args.get("tel","")
    if telefono:
        codigo = generar_otp()
        guardar_otp(telefono, codigo)
        enviar_sms_otp(telefono, codigo)
    return redirect(url_for('verificar_registro', tel=telefono))

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN — paso 1: ingresar teléfono
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/login', methods=['GET','POST'])
def login():
    error = ""
    if request.method == 'POST':
        telefono = request.form.get("telefono","").strip()
        if not telefono:
            error = "Ingresa tu número."
        elif not find_user(telefono):
            error = "Número no registrado. <a href='/registro'>Crea una cuenta</a>."
        else:
            codigo = generar_otp()
            guardar_otp(telefono, codigo)
            ok = enviar_sms_otp(telefono, codigo)
            if ok:
                return redirect(url_for('verificar_login', tel=telefono))
            else:
                error = "No se pudo enviar el SMS. Intenta de nuevo."

    html = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box'>
        <h1>🔐 Iniciar sesión</h1>
        <p class='sub'>Te enviaremos un código de 6 dígitos por SMS para verificar tu identidad.</p>
        {% if error %}<div class='alert alert-error'>{{ error|safe }}</div>{% endif %}
        <form method='POST'>
          <div class='form-group'>
            <label>Número de WhatsApp (con código de país)</label>
            <input type='tel' name='telefono' placeholder='Ej. 526561234567' autofocus>
          </div>
          <button class='btn-primary' type='submit'>Enviar código SMS →</button>
        </form>
        <div class='link-row'>¿No tienes cuenta? <a href='/registro'>Regístrate</a></div>
      </div>
    </div>"""
    return render_template_string(html, error=error)

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN — paso 2: verificar OTP
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/login/verificar', methods=['GET','POST'])
def verificar_login():
    telefono = request.args.get("tel","")
    error = ""
    if not telefono:
        return redirect(url_for('login'))

    if request.method == 'POST':
        digits = [request.form.get(f"d{i}","") for i in range(1,7)]
        codigo = "".join(digits)
        ok, msg = verificar_otp(telefono, codigo)
        if ok:
            session["telefono"] = telefono
            return redirect(url_for('index'))
        else:
            error = msg

    html = BASE_CSS + """
    <div class='auth-wrap'>
      <div class='auth-box'>
        <h1>✅ Verifica tu número</h1>
        <p class='sub'>Código enviado al <strong>{{ tel }}</strong>.</p>
        {% if error %}<div class='alert alert-error'>{{ error }}</div>{% endif %}
        <form method='POST' id='otpForm'>
          <div class='otp-inputs'>
            <input type='text' name='d1' id='d1' maxlength='1' inputmode='numeric'>
            <input type='text' name='d2' id='d2' maxlength='1' inputmode='numeric'>
            <input type='text' name='d3' id='d3' maxlength='1' inputmode='numeric'>
            <input type='text' name='d4' id='d4' maxlength='1' inputmode='numeric'>
            <input type='text' name='d5' id='d5' maxlength='1' inputmode='numeric'>
            <input type='text' name='d6' id='d6' maxlength='1' inputmode='numeric'>
          </div>
          <button class='btn-primary' type='submit' style='margin-top:20px'>Entrar →</button>
        </form>
        <form method='GET' action='/login/reenviar'>
          <input type='hidden' name='tel' value='{{ tel }}'>
          <button class='btn-secondary' type='submit'>🔄 Reenviar código</button>
        </form>
        <div class='link-row'><a href='/login'>← Cambiar número</a></div>
      </div>
    </div>
    <script>
      const inputs = document.querySelectorAll('.otp-inputs input');
      inputs.forEach((inp, i) => {
        inp.addEventListener('input', () => {
          if(inp.value && i < inputs.length-1) inputs[i+1].focus();
        });
        inp.addEventListener('keydown', e => {
          if(e.key==='Backspace' && !inp.value && i > 0) inputs[i-1].focus();
        });
      });
      inputs[0].focus();
    </script>"""
    return render_template_string(html, tel=telefono, error=error)

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN — reenviar OTP
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/login/reenviar')
def reenviar_otp_login():
    telefono = request.args.get("tel","")
    if telefono:
        codigo = generar_otp()
        guardar_otp(telefono, codigo)
        enviar_sms_otp(telefono, codigo)
    return redirect(url_for('verificar_login', tel=telefono))

# ══════════════════════════════════════════════════════════════════════════════
# LOGOUT
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ══════════════════════════════════════════════════════════════════════════════
# FEED PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/', methods=['GET', 'POST'])
def index():
    token_ingresado = request.args.get('admin')
    es_admin  = (token_ingresado == ADMIN_TOKEN)
    usuario   = session.get("telefono")
    mascotas_perdidas = get_mascotas()

    if request.method == 'POST':
        if not usuario:
            return redirect(url_for('login'))

        nombre = request.form.get("nombre","").strip()
        if nombre:
            url_principal = ""
            lista_secundarias = []
            try:
                foto_principal = request.files.get("imagen_principal")
                if foto_principal and foto_principal.filename != '':
                    bytes_p = foto_principal.read()
                    b64_p   = base64.b64encode(bytes_p).decode('utf-8')
                    url_principal = f"data:{foto_principal.content_type};base64,{b64_p}"

                for archivo in request.files.getlist("imagenes_secundarias")[:4]:
                    if archivo and archivo.filename != '':
                        bytes_s  = archivo.read()
                        b64_s    = base64.b64encode(bytes_s).decode('utf-8')
                        lista_secundarias.append(f"data:{archivo.content_type};base64,{b64_s}")
            except Exception as e:
                print(f"⚠️ Error imágenes: {e}")

            nuevo = {
                "id":          str(int(time.time() * 1000)),
                "reportado_por": usuario,
                "nombre":      request.form.get("nombre"),
                "descripcion": request.form.get("descripcion"),
                "zona":        request.form.get("zona"),
                "contacto":    request.form.get("contacto"),
                "principal":   url_principal,
                "secundarias": lista_secundarias,
                "fecha":       request.form.get("fecha"),
                "edad":        request.form.get("edad"),
                "raza":        request.form.get("raza"),
                "genero":      request.form.get("genero"),
                "color":       request.form.get("color"),
                "collar":      request.form.get("collar"),
                "docil":       request.form.get("docil"),
                "direccion":   request.form.get("direccion"),
                "ciudad":      request.form.get("ciudad"),
                "estado":      request.form.get("estado"),
                "cp":          request.form.get("cp"),
                "calles":      request.form.get("calles"),
                "dueno":       request.form.get("dueno"),
                "recompensa":  request.form.get("recompensa"),
            }
            mascotas_perdidas.insert(0, nuevo)
            save_json(MASCOTAS_FILE, mascotas_perdidas)

        if es_admin:
            return redirect(url_for('index', admin=ADMIN_TOKEN))
        return redirect(url_for('index'))

    html_index = BASE_CSS + """
    <style>
      body { padding-bottom:120px; }
      .main-container { max-width:1100px; margin:40px auto; padding:0 24px; }
      .section-intro { margin-bottom:32px; }
      .section-intro h2 { font-size:1.8em; font-weight:800; letter-spacing:-0.03em; margin-bottom:4px; }
      .section-intro p  { color:var(--gray); font-size:0.95em; }

      .grid-feed { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:24px; }
      .card-minimal { background:var(--card); border-radius:20px; border:1px solid #e2e8f0; overflow:hidden;
        transition:transform .2s,box-shadow .2s; display:flex; flex-direction:column; height:100%; position:relative; }
      .card-minimal:active { transform:scale(0.98); }
      @media(min-width:768px){ .card-minimal:hover{ transform:translateY(-4px); box-shadow:0 12px 20px -8px rgba(0,0,0,.08); } }
      .card-img-box { width:100%; aspect-ratio:4/3; height:auto; background:#f1f5f9; position:relative; }
      .card-img-box img { width:100%; height:100%; object-fit:cover; }
      .card-badge { position:absolute; top:12px; right:12px; background:#ef4444; color:white;
        font-size:.7em; font-weight:800; padding:4px 10px; border-radius:99px; z-index:2; }
      .card-info { padding:16px; display:flex; flex-direction:column; gap:4px; }
      .card-info h3 { font-size:1.15em; font-weight:700; word-break:break-word; }
      .card-info p  { color:var(--gray); font-size:.88em; word-break:break-word; }
      .stretched-link { position:absolute; top:0;right:0;bottom:0;left:0; z-index:5; text-indent:-9999px; overflow:hidden; }

      .app-footer-bar { position:fixed; bottom:0; left:0; width:100%; background:rgba(255,255,255,.9);
        backdrop-filter:blur(20px); border-top:1px solid #e2e8f0; padding:16px 24px;
        padding-bottom:calc(16px + env(safe-area-inset-bottom)); z-index:100; display:flex; justify-content:center; }
      .btn-trigger-form { background:var(--grad); color:white; border:none; padding:16px 32px; border-radius:16px;
        font-weight:700; font-size:1em; cursor:pointer; width:100%; max-width:450px;
        box-shadow:0 4px 12px rgba(255,107,74,.2); min-height:52px; }

      .modal-overlay { position:fixed; top:0;left:0;width:100%;height:100%;
        background:rgba(15,23,42,.4); display:none; align-items:flex-end; justify-content:center; z-index:200;
        backdrop-filter:blur(8px); }
      .modal-box { background:var(--card); width:100%; max-width:500px; border-top-left-radius:28px;
        border-top-right-radius:28px; padding:24px; padding-bottom:calc(24px + env(safe-area-inset-bottom));
        max-height:90vh; overflow-y:auto; -webkit-overflow-scrolling:touch; }
      .modal-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;
        position:sticky; top:0; background:var(--card); z-index:1; }
      .btn-close { background:#f1f5f9; border:none; width:36px; height:36px; min-width:36px; border-radius:50%; cursor:pointer; flex-shrink:0; }
      .form-group label { display:block; font-size:.82em; font-weight:700; margin-bottom:6px; color:#475569; }
      .form-group input,.form-group textarea,.form-group select {
        width:100%; padding:12px 14px; border:1px solid #cbd5e1; border-radius:12px;
        font-size:1em; font-family:inherit; outline:none; background:#f8fafc; }
      .form-row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
      .form-section-title { font-size:.78em; font-weight:800; text-transform:uppercase; letter-spacing:.08em;
        color:#94a3b8; margin:20px 0 10px; border-top:1px solid #e2e8f0; padding-top:20px; }
      .file-input-styled { display:block; width:100%; padding:12px; border:2px dashed #cbd5e1;
        background:#f8fafc; border-radius:12px; cursor:pointer; font-size:.85em; }
      .btn-publish { background:var(--grad); color:white; border:none; width:100%; padding:14px;
        border-radius:12px; font-weight:700; font-size:1em; cursor:pointer; margin-top:8px; min-height:50px; }

      /* Login prompt */
      .login-prompt { text-align:center; padding:20px; background:#fff7ed; border:1px solid #fed7aa;
        border-radius:16px; color:#9a3412; font-size:.93em; }
      .login-prompt a { color:#ff6b4a; font-weight:700; text-decoration:none; }

      /* ── Responsive breakpoints ───────────────────────────────────────── */
      @media (max-width:768px) {
        .main-container { margin:24px auto; padding:0 16px; }
        .section-intro h2 { font-size:1.5em; }
        .grid-feed { grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:16px; }
        .navbar { padding:14px 16px; }
      }

      @media (max-width:600px) {
        .grid-feed { grid-template-columns:repeat(2,1fr); gap:12px; }
        .card-img-box { aspect-ratio:1/1; }
        .card-info { padding:10px 12px; }
        .card-info h3 { font-size:1em; }
        .card-info p { font-size:.8em; }
        .app-footer-bar { padding:12px 16px; padding-bottom:calc(12px + env(safe-area-inset-bottom)); }
        .btn-trigger-form { padding:14px 20px; font-size:.95em; }
        .modal-box { padding:18px; border-top-left-radius:22px; border-top-right-radius:22px; }
        .form-row { grid-template-columns:1fr; gap:0; }
      }

      @media (max-width:420px) {
        .navbar-brand { font-size:1.05em; }
        .nav-user { font-size:.78em; gap:8px; }
        .section-intro h2 { font-size:1.3em; }
        .grid-feed { grid-template-columns:repeat(2,1fr); gap:10px; }
      }
    </style>

    <div class='navbar'>
      <div class='navbar-brand'>🐾 <span>Ubican ID</span> SOS</div>
      <div class='nav-user'>
        {% if usuario %}
          📱 {{ usuario[:4] }}****{{ usuario[-4:] }}
          &nbsp;<a href='/logout'>Salir</a>
        {% else %}
          <a href='/login' style='color:#ff6b4a;font-weight:600;text-decoration:none;'>Iniciar sesión</a>
          &nbsp;/&nbsp;
          <a href='/registro' style='color:#ff6b4a;font-weight:600;text-decoration:none;'>Registrarse</a>
        {% endif %}
      </div>
    </div>

    <div class='main-container'>
      <div class='section-intro'>
        <h2>Mascotas Extraviadas</h2>
        <p>Haz clic en cualquier tarjeta para ver la información de contacto.</p>
      </div>

      <div class='grid-feed'>
        {% if not mascotas %}
          <div style='grid-column:1/-1;text-align:center;color:var(--gray);padding:60px 0;font-style:italic;'>
            📍 No hay alertas activas en este momento.
          </div>
        {% endif %}
        {% for m in mascotas %}
        <div class='card-minimal'>
          <a href='/mascota/{{ m.id }}' class='stretched-link'>Ver detalles</a>
          <div class='card-img-box'>
            <span class='card-badge'>SOS</span>
            {% if m.principal %}
              <img src='{{ m.principal }}' alt='{{ m.nombre }}' loading='lazy'>
            {% else %}
              <div style='display:flex;justify-content:center;align-items:center;height:100%;font-size:2.5em;'>🐾</div>
            {% endif %}
          </div>
          <div class='card-info'>
            <h3>{{ m.nombre }}</h3>
            <p>📍 {{ m.zona }}</p>
            {% if m.raza %}<p>🐶 {{ m.raza }}</p>{% endif %}
          </div>
        </div>
        {% endfor %}
      </div>
    </div>

    <div class='app-footer-bar'>
      {% if usuario %}
        <button class='btn-trigger-form' onclick='toggleModal(true)'>🚨 Reportar Mascota Perdida</button>
      {% else %}
        <a href='/login' style='background:var(--grad);color:white;text-decoration:none;padding:16px 32px;
          border-radius:16px;font-weight:700;font-size:1em;width:100%;max-width:450px;text-align:center;
          display:block;box-shadow:0 4px 12px rgba(255,107,74,.2);'>
          🔐 Inicia sesión para reportar
        </a>
      {% endif %}
    </div>

    {% if usuario %}
    <div id='formModal' class='modal-overlay' onclick='closeModalOutside(event)'>
      <div class='modal-box'>
        <div class='modal-head'>
          <h3>Registrar Reporte</h3>
          <button class='btn-close' onclick='toggleModal(false)'>✕</button>
        </div>
        <form method='POST' action='/' enctype='multipart/form-data' id='sosForm' novalidate>
          <p class='form-section-title'>🐾 Datos de la mascota</p>
          <div class='form-group'><label>Nombre *</label><input type='text' id='formNombre' name='nombre' placeholder='Ej. Rocko'></div>
          <div class='form-row'>
            <div class='form-group'><label>Raza</label><input type='text' name='raza' placeholder='Ej. Labrador'></div>
            <div class='form-group'><label>Edad</label><input type='text' name='edad' placeholder='Ej. 3 años'></div>
          </div>
          <div class='form-row'>
            <div class='form-group'><label>Género</label>
              <select name='genero'><option value=''>--</option><option>Macho</option><option>Hembra</option></select></div>
            <div class='form-group'><label>Color</label><input type='text' name='color' placeholder='Ej. Café'></div>
          </div>
          <div class='form-row'>
            <div class='form-group'><label>¿Collar?</label>
              <select name='collar'><option value=''>--</option><option>Sí</option><option>No</option></select></div>
            <div class='form-group'><label>¿Dócil?</label>
              <select name='docil'><option value=''>--</option><option>Sí</option><option>No</option></select></div>
          </div>
          <div class='form-group'><label>Descripción *</label>
            <textarea id='formDesc' name='descripcion' rows='3' placeholder='Señas particulares...'></textarea></div>

          <p class='form-section-title'>📍 Lugar del extravío</p>
          <div class='form-group'><label>Fecha</label><input type='date' name='fecha'></div>
          <div class='form-group'><label>Colonia / Zona *</label><input type='text' id='formZona' name='zona' placeholder='Ej. Col. Centro'></div>
          <div class='form-group'><label>Dirección</label><input type='text' name='direccion' placeholder='Ej. Calle Hidalgo 123'></div>
          <div class='form-group'><label>Entre calles</label><input type='text' name='calles' placeholder='Entre Juárez y Allende'></div>
          <div class='form-row'>
            <div class='form-group'><label>Ciudad</label><input type='text' name='ciudad' placeholder='Ej. Juárez'></div>
            <div class='form-group'><label>Estado</label><input type='text' name='estado' placeholder='Ej. Chihuahua'></div>
          </div>
          <div class='form-group'><label>C.P.</label><input type='text' name='cp' placeholder='32000'></div>

          <p class='form-section-title'>👤 Datos del dueño</p>
          <div class='form-group'><label>Nombre del dueño</label><input type='text' name='dueno' placeholder='Ej. Carlos Ramírez'></div>
          <div class='form-group'><label>Teléfono (WhatsApp) *</label>
            <input type='tel' id='formContacto' name='contacto' placeholder='526561234567'></div>
          <div class='form-group'><label>Recompensa</label><input type='text' name='recompensa' placeholder='Ej. $500 MXN'></div>

          <p class='form-section-title'>📸 Fotos</p>
          <div class='form-group'><label>Foto Principal *</label>
            <input type='file' id='principalInput' name='imagen_principal' accept='image/*' class='file-input-styled'></div>
          <div class='form-group'><label>Fotos Adicionales (Máx 4)</label>
            <input type='file' name='imagenes_secundarias' accept='image/*' multiple class='file-input-styled'></div>

          <button type='submit' class='btn-publish'>🚨 Publicar Alerta</button>
        </form>
      </div>
    </div>
    {% endif %}

    <script>
      function toggleModal(show) { document.getElementById('formModal').style.display = show ? 'flex' : 'none'; }
      function closeModalOutside(e) { if(e.target===document.getElementById('formModal')) toggleModal(false); }
      {% if usuario %}
      document.getElementById('sosForm').onsubmit = function(e) {
        const req = ['formNombre','formZona','formContacto','formDesc'];
        for(let id of req) { if(!document.getElementById(id).value.trim()) {
          e.preventDefault(); alert('⚠️ Rellena todos los campos obligatorios.'); return false; } }
        if(!document.getElementById('principalInput').files[0]) {
          e.preventDefault(); alert('⚠️ Selecciona una Foto Principal.'); return false; }
        return true;
      };
      {% endif %}
    </script>
    """
    return render_template_string(html_index, mascotas=mascotas_perdidas, es_admin=es_admin, usuario=usuario)


# ══════════════════════════════════════════════════════════════════════════════
# DETALLE MASCOTA
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/mascota/<id>')
def detalle_mascota(id):
    mascotas_perdidas = get_mascotas()
    mascota = next((m for m in mascotas_perdidas if m["id"] == id), None)
    if not mascota:
        return redirect(url_for('index'))

    html_detalle = BASE_CSS + """
    <style>
      body { padding:24px 16px 120px; }
      .detail-container { max-width:600px; margin:0 auto; }
      .btn-back { display:inline-flex; align-items:center; gap:8px; color:var(--gray); text-decoration:none;
        font-weight:600; font-size:.95em; margin-bottom:24px; }
      .hero-image-box { width:100%; aspect-ratio:4/3; height:auto; border-radius:24px; overflow:hidden;
        background:#e2e8f0; cursor:pointer; margin-bottom:16px; }
      .hero-image-box img { width:100%; height:100%; object-fit:cover; }
      .thumb-gallery { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-bottom:28px; }
      .thumb-gallery img { width:100%; height:65px; object-fit:cover; border-radius:12px;
        cursor:pointer; border:1px solid #e2e8f0; }
      .info-box h2 { font-size:2.2em; font-weight:800; margin-bottom:16px; letter-spacing:-.03em; word-break:break-word; }
      .detail-section { margin-bottom:20px; }
      .detail-section-title { font-size:.75em; font-weight:800; text-transform:uppercase;
        letter-spacing:.08em; color:#94a3b8; margin-bottom:10px; }
      .data-pills { display:flex; flex-direction:column; gap:8px; }
      .pill { display:flex; align-items:center; gap:8px; font-size:.93em; color:var(--slate);
        background:#fff; padding:11px 14px; border-radius:12px; border:1px solid #e2e8f0; word-break:break-word; }
      .pill-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
      .reward-badge { display:inline-flex; align-items:center; gap:6px; background:#fef3c7;
        color:#92400e; border:1px solid #fde68a; padding:10px 14px; border-radius:12px;
        font-weight:700; font-size:.95em; margin-bottom:20px; flex-wrap:wrap; }
      .description-box { font-size:1em; color:var(--slate); line-height:1.7; margin-bottom:28px;
        border-top:1px solid #e2e8f0; padding-top:20px; word-break:break-word; }
      .btn-whatsapp { background:var(--success); color:white; text-decoration:none; padding:16px;
        border-radius:18px; text-align:center; font-weight:700; font-size:1.05em;
        display:flex; align-items:center; justify-content:center; gap:8px;
        box-shadow:0 6px 20px rgba(16,185,129,.25); min-height:54px; }
      .lightbox { position:fixed; top:0;left:0;width:100%;height:100%;
        background:rgba(15,23,42,.95); display:none; justify-content:center; align-items:center; z-index:400; }
      .lightbox img { max-width:95%; max-height:85vh; border-radius:16px; object-fit:contain; }

      @media (max-width:600px) {
        body { padding:16px 12px 110px; }
        .hero-image-box { border-radius:18px; }
        .info-box h2 { font-size:1.7em; }
        .pill-grid { grid-template-columns:1fr; }
        .thumb-gallery { grid-template-columns:repeat(4,1fr); }
        .thumb-gallery img { height:54px; }
      }

      @media (max-width:380px) {
        .thumb-gallery { grid-template-columns:repeat(3,1fr); }
      }
    </style>

    <div class='detail-container'>
      <a href='/' class='btn-back'>← Regresar al inicio</a>

      <div class='hero-image-box' onclick="openLightbox(document.getElementById('mainPhoto').src)">
        {% if mascota.principal %}
          <img src='{{ mascota.principal }}' id='mainPhoto' alt='Foto principal'>
        {% else %}
          <div style='display:flex;justify-content:center;align-items:center;height:100%;font-size:3em;'>🐾</div>
        {% endif %}
      </div>

      <div class='thumb-gallery'>
        {% if mascota.principal %}
        <img src='{{ mascota.principal }}' onclick="changeHero(this.src);openLightbox(this.src);event.stopPropagation();">
        {% endif %}
        {% for img in mascota.secundarias %}
        <img src='{{ img }}' onclick="changeHero(this.src);openLightbox(this.src);event.stopPropagation();">
        {% endfor %}
      </div>

      <div class='info-box'>
        <h2>{{ mascota.nombre }}</h2>
        {% if mascota.recompensa %}
        <div class='reward-badge'>🏅 Recompensa: {{ mascota.recompensa }}</div>
        {% endif %}

        <div class='detail-section'>
          <div class='detail-section-title'>🐾 Datos de la mascota</div>
          <div class='pill-grid'>
            {% if mascota.raza %}<div class='pill'>🐶 <span><strong>Raza:</strong> {{ mascota.raza }}</span></div>{% endif %}
            {% if mascota.edad %}<div class='pill'>🎂 <span><strong>Edad:</strong> {{ mascota.edad }}</span></div>{% endif %}
            {% if mascota.genero %}<div class='pill'>⚧ <span><strong>Género:</strong> {{ mascota.genero }}</span></div>{% endif %}
            {% if mascota.color %}<div class='pill'>🎨 <span><strong>Color:</strong> {{ mascota.color }}</span></div>{% endif %}
            {% if mascota.collar %}<div class='pill'>🔖 <span><strong>Collar:</strong> {{ mascota.collar }}</span></div>{% endif %}
            {% if mascota.docil %}<div class='pill'>🤝 <span><strong>Dócil:</strong> {{ mascota.docil }}</span></div>{% endif %}
          </div>
        </div>

        <div class='detail-section'>
          <div class='detail-section-title'>📍 Lugar del extravío</div>
          <div class='data-pills'>
            {% if mascota.fecha %}<div class='pill'>📅 <span><strong>Fecha:</strong> {{ mascota.fecha }}</span></div>{% endif %}
            {% if mascota.zona %}<div class='pill'>🗺️ <span><strong>Zona:</strong> {{ mascota.zona }}</span></div>{% endif %}
            {% if mascota.direccion %}<div class='pill'>🏠 <span><strong>Dirección:</strong> {{ mascota.direccion }}</span></div>{% endif %}
            {% if mascota.calles %}<div class='pill'>🔀 <span><strong>Entre calles:</strong> {{ mascota.calles }}</span></div>{% endif %}
            {% if mascota.ciudad or mascota.estado %}
            <div class='pill'>🏙️ <span><strong>Ciudad/Estado:</strong> {{ mascota.ciudad }}{% if mascota.ciudad and mascota.estado %}, {% endif %}{{ mascota.estado }}</span></div>
            {% endif %}
            {% if mascota.cp %}<div class='pill'>📮 <span><strong>C.P.:</strong> {{ mascota.cp }}</span></div>{% endif %}
          </div>
        </div>

        <div class='detail-section'>
          <div class='detail-section-title'>👤 Datos del dueño</div>
          <div class='data-pills'>
            {% if mascota.dueno %}<div class='pill'>👤 <span><strong>Nombre:</strong> {{ mascota.dueno }}</span></div>{% endif %}
            <div class='pill'>📞 <span><strong>Teléfono:</strong> {{ mascota.contacto }}</span></div>
          </div>
        </div>

        <div class='description-box'>
          <strong>Detalles del extravío:</strong>
          <p style='margin-top:6px;'>{{ mascota.descripcion }}</p>
        </div>

        <a href='https://wa.me/{{ mascota.contacto }}' target='_blank' class='btn-whatsapp'>💬 Contactar por WhatsApp</a>
      </div>
    </div>

    <div id='imageLightbox' class='lightbox' onclick='closeLightbox()'>
      <img id='lightboxImg' src=''>
    </div>

    <script>
      function changeHero(src) { document.getElementById('mainPhoto').src = src; }
      function openLightbox(src) { document.getElementById('lightboxImg').src = src; document.getElementById('imageLightbox').style.display = 'flex'; }
      function closeLightbox() { document.getElementById('imageLightbox').style.display = 'none'; }
    </script>
    """
    return render_template_string(html_detalle, mascota=mascota)


if __name__ == '__main__':
    app.run(debug=True)
