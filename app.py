import os
import time
import random
import requests
from flask import Flask, request, render_template_string, redirect, url_for, session
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia_esto_en_produccion")
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv("MAX_CONTENT_LENGTH", 16777216))

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "ubican123")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ─── FUNCIONES DE BASE DE DATOS (Sincronizadas con tu esquema) ────────────────

def db_save_mascota(datos):
    # Incluye todos los campos de tu tabla 'mascotas'
    url = f"{SUPABASE_URL}/rest/v1/mascotas"
    try: requests.post(url, json=datos, headers=SUPABASE_HEADERS, timeout=10)
    except Exception as e: print(f"⚠️ Error db_save_mascota: {e}")

# ─── RUTA PRINCIPAL Y FORMULARIO ──────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def index():
    usuario = session.get("telefono")
    if request.method == 'POST' and usuario:
        # Recolectar TODOS los campos de tu esquema SQL
        nuevo = {
            "id": str(int(time.time() * 1000)),
            "reportado_por": usuario,
            "nombre": request.form.get("nombre"),
            "descripcion": request.form.get("descripcion"),
            "zona": request.form.get("zona"),
            "contacto": request.form.get("contacto"),
            "principal": upload_to_supabase_storage(request.files.get("imagen_principal")),
            "secundarias": [],
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

    # Renderizado con la marca Ubican ID
    html = """
    <div class='navbar'>
      <a href='/' class='navbar-brand'>🐾 Ubican <span>ID</span></a>
    </div>
    """
    return render_template_string(html)

# ... (Mantén aquí el resto de tus rutas: /registro, /login, /mascota/<id>, etc.)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
