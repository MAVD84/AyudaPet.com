import os
import time
import random
import base64
import requests
from flask import Flask, request, render_template_string, redirect, url_for, session
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia_esto_en_produccion_segura_12345")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin_default_token")

# ─── CONFIGURACIÓN DE SUPABASE ────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://db-reportes.srvr.site")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...")

# Headers requeridos por la API de Supabase
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

# ─── FUNCIONES CLIENTE SUPABASE (REPLAZAN A HELPERS JSON) ─────────────────────
def db_get_usuario(telefono):
    url = f"{SUPABASE_URL}/rest/v1/usuarios?telefono=eq.{telefono}"
    r = requests.get(url, headers=SUPABASE_HEADERS)
    res = r.json()
    return res[0] if isinstance(res, list) and len(res) > 0 else None

def db_save_usuario(telefono, password_hash):
    url = f"{SUPABASE_URL}/rest/v1/usuarios"
    payload = {
        "telefono": telefono,
        "creado": int(time.time()),
        "password_hash": password_hash
    }
    # UPSERT: Si existe lo actualiza, si no, lo inserta
    headers = {**SUPABASE_HEADERS, "Prefer": "resolution=merge-duplicates"}
    requests.post(url, json=payload, headers=headers)

def db_get_mascotas():
    # Trae las mascotas ordenadas por ID de forma descendente (más recientes primero)
    url = f"{SUPABASE_URL}/rest/v1/mascotas?order=id.desc"
    r = requests.get(url, headers=SUPABASE_HEADERS)
    return r.json() if isinstance(r.json(), list) else []

def db_save_mascota(datos):
    url = f"{SUPABASE_URL}/rest/v1/mascotas"
    requests.post(url, json=datos, headers=SUPABASE_HEADERS)

# ─── MANEJO DE OTP EN BASE DE DATOS ───────────────────────────────────────────
def db_guardar_otp(telefono, codigo):
    url = f"{SUPABASE_URL}/rest/v1/otps"
    payload = {
        "telefono": telefono,
        "code": codigo,
        "expires": time.time() + 300
    }
    headers = {**SUPABASE_HEADERS, "Prefer": "resolution=merge-duplicates"}
    requests.post(url, json=payload, headers=headers)

def db_verificar_otp(telefono, codigo):
    url = f"{SUPABASE_URL}/rest/v1/otps?telefono=eq.{telefono}"
    r = requests.get(url, headers=SUPABASE_HEADERS).json()
    
    if not r or not isinstance(r, list):
        return False, "No se solicitó un código para este número."
    
    entry = r[0]
    if time.time() > entry["expires"]:
        # Borrar OTP expirado
        requests.delete(url, headers=SUPABASE_HEADERS)
        return False, "El código expiró. Solicita uno nuevo."
        
    if entry["code"] != codigo.strip():
        return False, "Código incorrecto."
        
    # Consumido con éxito, se borra
    requests.delete(url, headers=SUPABASE_HEADERS)
    return True, "OK"

# ─── LOGICA DE SESIÓN Y PASSWORD ──────────────────────────────────────────────
def user_has_password(telefono):
    u = db_get_usuario(telefono)
    return u is not None and bool(u.get("password_hash"))

# ─── (El resto de tus helpers de SMS y cifrado se quedan igual) ────────────────
def generar_otp(): return str(random.randint(100000, 999999))

def enviar_sms_otp(telefono, codigo):
    payload = {
        "message": f"Tu código de verificación Ubican ID es: {codigo}.",
        "recipient": [{"msisdn": telefono}],
    }
    if LABSMOBILE_SENDER: payload["tpoa"] = LABSMOBILE_SENDER
    try:
        r = requests.post(LABSMOBILE_API, json=payload, auth=(LABSMOBILE_USER, LABSMOBILE_TOKEN), timeout=10)
        return r.status_code == 200, "OK"
    except:
        return False, "Error"

# ─── RUTAS CORREGIDAS (EJEMPLO DE INTEGRACIÓN CON ACCIONES POST) ──────────────
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
            if ok: return redirect(url_for('verificar_registro', tel=telefono))
            error = "No se pudo enviar el SMS."
    # ... render_template_string se mantiene igual utilizando Jinja seguro
    return render_template_string("...", error=error)

@app.route('/', methods=['GET', 'POST'])
def index():
    token_ingresado = request.args.get('admin')
    es_admin  = (token_ingresado == ADMIN_TOKEN)
    usuario   = session.get("telefono")
    mascotas_perdidas = db_get_mascotas()

    if request.method == 'POST':
        if not usuario: return redirect(url_for('login'))
        nombre = request.form.get("nombre","").strip()
        if nombre:
            # ... (Mismo procesamiento de imágenes de tu código base)
            url_principal = "" 
            lista_secundarias = [] 

            nuevo = {
                "id":           str(int(time.time() * 1000)),
                "reportado_por": usuario,
                "nombre":       request.form.get("nombre"),
                "descripcion":  request.form.get("descripcion"),
                "zona":         request.form.get("zona"),
                "contacto":     request.form.get("contacto"),
                "principal":    url_principal,
                "secundarias":  lista_secundarias, # PostgreSQL digiere arrays nativos de JSON si están configurados
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
        return redirect(url_for('index', admin=ADMIN_TOKEN if es_admin else None))

    # Renderizado seguro de las tarjetas leyendo de Supabase
    return render_template_string("...", mascotas=mascotas_perdidas)
