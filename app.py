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

LABSMOBILE_USER = os.getenv("LABSMOBILE_USER")
LABSMOBILE_TOKEN = os.getenv("LABSMOBILE_TOKEN")
LABSMOBILE_SENDER = os.getenv("LABSMOBILE_SENDER")
LABSMOBILE_API = os.getenv("LABSMOBILE_API", "https://api.labsmobile.com/json/send")

# ─── HELPERS BASE DE DATOS ────────────────────────────────────────────────────

def db_get_usuario(telefono):
    url = f"{SUPABASE_URL}/rest/v1/usuarios?telefono=eq.{telefono}"
    r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10).json()
    return r[0] if isinstance(r, list) and len(r) > 0 else None

def db_save_usuario(telefono, password_hash):
    url = f"{SUPABASE_URL}/rest/v1/usuarios"
    payload = {"telefono": telefono, "creado": int(time.time()), "password_hash": password_hash}
    requests.post(url, json=payload, headers={**SUPABASE_HEADERS, "Prefer": "resolution=merge-duplicates"}, timeout=10)

def db_get_mascotas():
    url = f"{SUPABASE_URL}/rest/v1/mascotas?order=creado_at.desc"
    try: return requests.get(url, headers=SUPABASE_HEADERS, timeout=10).json()
    except: return []

def db_get_mascota_por_id(id_mascota):
    url = f"{SUPABASE_URL}/rest/v1/mascotas?id=eq.{id_mascota}"
    r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10).json()
    return r[0] if r and isinstance(r, list) else None

def db_save_mascota(datos):
    url = f"{SUPABASE_URL}/rest/v1/mascotas"
    requests.post(url, json=datos, headers=SUPABASE_HEADERS, timeout=10)

def db_update_mascota(id_mascota, datos):
    url = f"{SUPABASE_URL}/rest/v1/mascotas?id=eq.{id_mascota}"
    requests.patch(url, json=datos, headers=SUPABASE_HEADERS, timeout=10)

def db_delete_mascota(id_mascota):
    url = f"{SUPABASE_URL}/rest/v1/mascotas?id=eq.{id_mascota}"
    requests.delete(url, headers=SUPABASE_HEADERS, timeout=10)

def db_verificar_otp(telefono, codigo):
    url = f"{SUPABASE_URL}/rest/v1/otps?telefono=eq.{telefono}"
    r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10).json()
    if not r: return False, "No solicitado."
    entry = r[0]
    if time.time() > entry["expires"]: return False, "Expiró."
    if entry["code"] != codigo: return False, "Erróneo."
    requests.delete(url, headers=SUPABASE_HEADERS, timeout=10)
    return True, "OK"

# ─── RUTAS ────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def index():
    usuario = session.get("telefono")
    if request.method == 'POST' and usuario:
        nuevo = {
            "id": str(int(time.time() * 1000)),
            "reportado_por": usuario,
            "nombre": request.form.get("nombre"),
            "descripcion": request.form.get("descripcion"),
            "zona": request.form.get("zona"),
            "contacto": request.form.get("contacto"),
            "principal": "",
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
    
    return render_template_string("""
    <h1>Bienvenido a UBICAN ID</h1>
    <a href='/registro'>Registrar</a> | <a href='/login'>Login</a>
    """)

@app.route('/mascota/editar/<id_mascota>', methods=['GET', 'POST'])
def editar_mascota(id_mascota):
    if request.method == 'POST':
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
    return "Edición de UBICAN ID"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
