import os
import time
import requests
from flask import Flask, request, render_template_string, redirect, url_for, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia_esto_en_produccion")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ─── FUNCIONES BASE DE DATOS ─────────────────────────────────────────────────
def db_get_mascotas():
    url = f"{SUPABASE_URL}/rest/v1/mascotas?order=creado_at.desc"
    try: return requests.get(url, headers=SUPABASE_HEADERS, timeout=10).json()
    except: return []

def db_save_mascota(datos):
    url = f"{SUPABASE_URL}/rest/v1/mascotas"
    requests.post(url, json=datos, headers=SUPABASE_HEADERS, timeout=10)

def db_update_mascota(id_mascota, datos):
    url = f"{SUPABASE_URL}/rest/v1/mascotas?id=eq.{id_mascota}"
    requests.patch(url, json=datos, headers=SUPABASE_HEADERS, timeout=10)

# ─── RUTAS ───────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def index():
    usuario = session.get("telefono")
    mascotas = db_get_mascotas()
    
    if request.method == 'POST' and usuario:
        nuevo = {
            "id": str(int(time.time() * 1000)),
            "reportado_por": usuario,
            "nombre": request.form.get("nombre"),
            "descripcion": request.form.get("descripcion"),
            "zona": request.form.get("zona"),
            "contacto": request.form.get("contacto"),
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
        db_save_mascota(nuevo)
        return redirect(url_for('index'))

    # Diseño plano (sin bloques para evitar el error)
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <style>
            :root { --grad: linear-gradient(135deg,#ff6b4a,#ff9f43); }
            body { font-family:sans-serif; background:#f8fafc; margin:0; }
            .navbar { background:#fff; padding:20px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; }
            .navbar-brand { font-size:1.5em; font-weight:800; text-decoration:none; color:#1e293b; }
            .navbar-brand span { background:var(--grad); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
            .main-container { max-width:1000px; margin:20px auto; padding:0 20px; }
            .grid-feed { display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:20px; }
            .card { background:#fff; border-radius:15px; padding:15px; box-shadow:0 4px 6px rgba(0,0,0,0.05); }
        </style>
    </head>
    <body>
        <div class='navbar'>
            <a href='/' class='navbar-brand'>🐾 UBICAN <span>ID</span></a>
            <div><a href='/registro'>Registrar</a> | <a href='/login'>Login</a></div>
        </div>
        <div class='main-container'>
            <h2>Mascotas Reportadas</h2>
            <div class='grid-feed'>
                {% for m in mascotas %}
                <div class='card'>
                    <h3>{{ m.nombre }}</h3>
                    <p>📍 {{ m.zona }}</p>
                    <p>Raza: {{ m.raza }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, mascotas=mascotas)

@app.route('/mascota/editar/<id_mascota>', methods=['POST'])
def editar_mascota(id_mascota):
    datos = {
        "nombre": request.form.get("nombre"),
        "descripcion": request.form.get("descripcion"),
        "zona": request.form.get("zona"),
        "contacto": request.form.get("contacto"),
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
    db_update_mascota(id_mascota, datos)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
