import os, time, random, requests
from flask import Flask, request, render_template_string, redirect, url_for, session
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secreto_2026")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_HEADERS = {
    "apikey": os.getenv("SUPABASE_ANON_KEY"),
    "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ─── DB HELPERS ─────────────────────────────────────────────────────────────
def db_query(table, method="GET", json=None, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{table}{params}"
    return requests.request(method, url, json=json, headers=SUPABASE_HEADERS).json()

# ─── UI BASE ────────────────────────────────────────────────────────────────
LAYOUT = """
<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>
<style>body{font-family:sans-serif; background:#f4f7f6; padding:20px;} .card{background:#fff; padding:15px; border-radius:8px; margin-bottom:10px; border-left:5px solid #ff6b4a;}</style></head>
<body><h1>UBICAN ID</h1><hr>{{ content|safe }}</body></html>
"""

# ─── RUTAS ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    mascotas = db_query("mascotas", params="?order=creado_at.desc")
    items = "".join([f"<div class='card'><h3>{m.get('nombre')}</h3><p>Zona: {m.get('zona')}</p></div>" for m in mascotas])
    return render_template_string(LAYOUT, content=f"<h2>Mascotas</h2>{items}<a href='/registro'>Registrar</a>")

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        tel = request.form.get('tel')
        code = str(random.randint(100000, 999999))
        db_query("otps", method="POST", json={"telefono": tel, "code": code, "expires": time.time() + 300})
        return render_template_string(LAYOUT, content=f"<form action='/verificar' method='POST'><input name='tel' value='{tel}' type='hidden'><input name='code' placeholder='Código'><button>Verificar</button></form>")
    return render_template_string(LAYOUT, content="<form method='POST'><input name='tel' placeholder='Teléfono'><button>Enviar SMS</button></form>")

@app.route('/verificar', methods=['POST'])
def verificar():
    tel, code = request.form.get('tel'), request.form.get('code')
    r = db_query("otps", params=f"?telefono=eq.{tel}")
    if r and r[0]['code'] == code:
        session['tel'] = tel
        return render_template_string(LAYOUT, content="<form action='/set_password' method='POST'><input type='password' name='pwd' placeholder='Contraseña'><button>Guardar</button></form>")
    return "Error. <a href='/registro'>Reintentar</a>"

@app.route('/set_password', methods=['POST'])
def set_password():
    db_query("usuarios", method="POST", json={"telefono": session['tel'], "creado": int(time.time()), "password_hash": generate_password_hash(request.form.get('pwd'))})
    return redirect('/')

@app.route('/reportar', methods=['POST'])
def reportar():
    if 'tel' not in session: return redirect('/login')
    # Mapeo completo de los 22 campos
    datos = {
        "id": str(int(time.time()*1000)),
        "reportado_por": session['tel'],
        "nombre": request.form.get("nombre"),
        "descripcion": request.form.get("descripcion"),
        "zona": request.form.get("zona"),
        "contacto": request.form.get("contacto"),
        "principal": request.form.get("principal"),
        "secundarias": request.form.getlist("secundarias"),
        "fecha": request.form.get("fecha"),
        "edad": request.form.get("edad"),
        "raza": request.form.get("raza"),
        "genero": request.form.get("genero"),
        "color": request.form.get("color"),
        "collar": request.form.get("collar"),
        "docil": request.form.get("docil"),
        "direccion": request.form.get("direccion"),
        "ciudad": request.form.get("ciudad"),
        "estado": request.form.get("estado"),
        "cp": request.form.get("cp"),
        "calles": request.form.get("calles"),
        "dueno": request.form.get("dueno"),
        "recompensa": request.form.get("recompensa")
    }
    db_query("mascotas", method="POST", json=datos)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
