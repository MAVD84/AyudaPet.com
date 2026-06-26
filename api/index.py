import os
import time
import base64
import traceback
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

ADMIN_TOKEN = "ubican123" 
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Base de datos en memoria
mascotas_perdidas = []

# =====================================================================
# 🛠️ ATRAPADOR DE ERRORES
# =====================================================================
@app.errorhandler(500)
def handle_internal_server_error(e):
    error_exacto = traceback.format_exc()
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Error en Servidor</title></head>
    <body style="font-family: system-ui, sans-serif; background: #f8fafc; padding: 20px; color: #0f172a;">
        <div style="max-width: 600px; margin: 40px auto; background: white; padding: 32px; border-radius: 24px; border: 1px solid #fca5a5; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <h2 style="color: #ef4444; margin-bottom: 12px;">⚠️ Ocurrió un error en Python</h2>
            <pre style="background: #0f172a; color: #38bdf8; padding: 16px; border-radius: 14px; overflow-x: auto; font-size: 0.85em; font-family: monospace; white-space: pre-wrap;">{error_exacto}</pre>
        </div>
    </body>
    </html>
    """, 500

# =====================================================================
# 🏠 RUTA PRINCIPAL: FEED MINIMALISTA
# =====================================================================
@app.route('/', methods=['GET', 'POST'])
def index():
    token_ingresado = request.args.get('admin')
    es_admin = (token_ingresado == ADMIN_TOKEN)

    if request.method == 'POST':
        nombre = request.form.get("nombre")
        if nombre and nombre.strip() != "":
            url_principal = ""
            lista_secundarias = []
            try:
                foto_principal = request.files.get("imagen_principal")
                if foto_principal and foto_principal.filename != '':
                    bytes_p = foto_principal.read()
                    b64_p = base64.b64encode(bytes_p).decode('utf-8')
                    url_principal = f"data:{foto_principal.content_type};base64,{b64_p}"

                fotos_secundarias = request.files.getlist("imagenes_secundarias")
                for archivo in fotos_secundarias[:4]:
                    if archivo and archivo.filename != '':
                        bytes_s = archivo.read()
                        b64_s = base64.b64encode(bytes_s).decode('utf-8')
                        data_url = f"data:{archivo.content_type};base64,{b64_s}"
                        lista_secundarias.append(data_url)
            except Exception as e:
                print(f"⚠️ Error en imágenes: {e}")

            # Identificador único para cada mascota basado en tiempo
            id_unico = str(int(time.time() * 1000))

            nuevo_reporte = {
                "id": id_unico,
                "nombre": nombre,
                "descripcion": request.form.get("descripcion"),
                "zona": request.form.get("zona"),
                "contacto": request.form.get("contacto"),
                "principal": url_principal,
                "secundarias": lista_secundarias
            }
            mascotas_perdidas.insert(0, nuevo_reporte)
            
        if es_admin:
            return redirect(url_for('index', admin=ADMIN_TOKEN))
        return redirect(url_for('index'))

    html_index = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ubican ID SOS</title>
        <style>
            :root {
                --primary-gradient: linear-gradient(135deg, #ff6b4a, #ff9f43);
                --dark: #1e293b;
                --bg: #f8fafc;
                --card-bg: #ffffff;
                --gray: #64748b;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
            body { font-family: system-ui, -apple-system, sans-serif; background-color: var(--bg); color: var(--dark); padding-bottom: 120px; }
            
            .navbar { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); position: sticky; top: 0; z-index: 90; padding: 18px 24px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
            .navbar-brand { font-size: 1.25em; font-weight: 800; }
            .navbar-brand span { background: var(--primary-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

            .main-container { max-width: 1100px; margin: 40px auto; padding: 0 24px; }
            .section-intro { margin-bottom: 32px; }
            .section-intro h2 { font-size: 1.8em; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 4px; }
            .section-intro p { color: var(--gray); font-size: 0.95em; }

            /* Grid Estilo Tarjetas Minimalistas */
            .grid-feed { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 24px; }
            .card-wrapper { text-decoration: none; color: inherit; }
            
            .card-minimal { 
                background: var(--card-bg); border-radius: 20px; border: 1px solid #e2e8f0; overflow: hidden; 
                transition: transform 0.2s ease, box-shadow 0.2s ease; display: flex; flex-direction: column; height: 100%;
            }
            .card-minimal:active { transform: scale(0.98); }
            @media (min-width: 768px) { .card-minimal:hover { transform: translateY(-4px); box-shadow: 0 12px 20px -8px rgba(0,0,0,0.08); } }

            .card-img-box { width: 100%; height: 260px; background: #f1f5f9; position: relative; }
            .card-img-box img { width: 100%; height: 100%; object-fit: cover; }
            .card-badge { position: absolute; top: 12px; right: 12px; background: #ef4444; color: white; font-size: 0.7em; font-weight: 800; padding: 4px 10px; border-radius: 99px; letter-spacing: 0.05em; }
            
            .card-info { padding: 16px; display: flex; flex-direction: column; gap: 4px; }
            .card-info h3 { font-size: 1.15em; font-weight: 700; color: var(--dark); }
            .card-info p { color: var(--gray); font-size: 0.88em; display: flex; align-items: center; gap: 4px; }

            .app-footer-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-top: 1px solid #e2e8f0; padding: 16px 24px; z-index: 100; display: flex; justify-content: center; }
            .btn-trigger-form { background: var(--primary-gradient); color: white; border: none; padding: 16px 32px; border-radius: 16px; font-weight: 700; font-size: 1em; cursor: pointer; width: 100%; max-width: 450px; text-align: center; box-shadow: 0 4px 12px rgba(255, 107, 74, 0.2); }

            /* Modal Formularios */
            .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.4); display: none; align-items: flex-end; justify-content: center; z-index: 200; backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
            .modal-box { background: var(--card-bg); width: 100%; max-width: 500px; border-top-left-radius: 28px; border-top-right-radius: 28px; padding: 24px; max-height: 85vh; overflow-y: auto; }
            .modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .btn-close { background: #f1f5f9; border: none; font-size: 1em; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; }
            .form-group { margin-bottom: 16px; }
            .form-group label { display: block; font-size: 0.85em; font-weight: 700; margin-bottom: 6px; color: #475569; }
            .form-group input, .form-group textarea { width: 100%; padding: 12px 14px; border: 1px solid #cbd5e1; border-radius: 12px; font-size: 0.95em; font-family: inherit; outline: none; background: #f8fafc; }
            .file-input-styled { display: block; width: 100%; padding: 12px; border: 2px dashed #cbd5e1; background: #f8fafc; border-radius: 12px; cursor: pointer; font-size: 0.85em; }
            .btn-publish { background: var(--primary-gradient); color: white; border: none; width: 100%; padding: 14px; border-radius: 12px; font-weight: 700; font-size: 1em; cursor: pointer; margin-top: 8px; }
        </style>
    </head>
    <body>

        <div class="navbar">
            <div class="navbar-brand">🐾 <span>Ubican ID</span> SOS</div>
        </div>

        <div class="main-container">
            <div class="section-intro">
                <h2>Mascotas Extraviadas</h2>
                <p>Haz clic en una tarjeta para ver toda la información de contacto.</p>
            </div>

            <div class="grid-feed">
                {% if not mascotas %}
                    <div style="grid-column: 1/-1; text-align: center; color: var(--gray); padding: 60px 0; font-style: italic;">
                        📍 No hay alertas activas en este momento.
                    </div>
                {% endif %}
                
                {% for mascota in mascotas %}
                <a href="/mascota/{{ mascota.id }}" class="card-wrapper">
                    <div class="card-minimal">
                        <div class="card-img-box">
                            <span class="card-badge">SOS</span>
                            {% if mascota.principal %}
                                <img src="{{ mascota.principal }}" alt="{{ mascota.nombre }}">
                            {% else %}
                                <div style="display:flex; justify-content:center; align-items:center; height:100%; font-size:2.5em;">🐾</div>
                            {% endif %}
                        </div>
                        <div class="card-info">
                            <h3>{{ mascota.nombre }}</h3>
                            <p>📍 {{ mascota.zona }}</p>
                        </div>
                    </div>
                </a>
                {% endfor %}
            </div>
        </div>

        <div class="app-footer-bar">
            <button class="btn-trigger-form" onclick="toggleModal(true)">🚨 Reportar Mascota Perdida</button>
        </div>

        <div id="formModal" class="modal-overlay" onclick="closeModalOutside(event)">
            <div class="modal-box">
                <div class="modal-head">
                    <h3>Registrar Reporte</h3>
                    <button class="btn-close" onclick="toggleModal(false)">✕</button>
                </div>
                <form method="POST" action="/" enctype="multipart/form-data" id="sosForm" novalidate>
                    <div class="form-group"><label>Nombre de la mascota *</label><input type="text" id="formNombre" name="nombre" placeholder="Ej. Rocko"></div>
                    <div class="form-group"><label>¿Dónde se extravió? *</label><input type="text" id="formZona" name="zona" placeholder="Ej. Col. Centro"></div>
                    <div class="form-group"><label>Teléfono (WhatsApp) *</label><input type="tel" id="formContacto" name="contacto" placeholder="Ej. 526561234567"></div>
                    <div class="form-group"><label>Descripción *</label><textarea id="formDesc" name="descripcion" placeholder="Señas particulares..."></textarea></div>
                    <div class="form-group"><label>📸 Foto Principal *</label><input type="file" id="principalInput" name="imagen_principal" accept="image/*" class="file-input-styled"></div>
                    <div class="form-group"><label>🐾 Fotos Adicionales (Máx 4)</label><input type="file" id="secundariasInput" name="imagenes_secundarias" accept="image/*" multiple class="file-input-styled"></div>
                    <button type="submit" class="btn-publish">🚨 Publicar Alerta</button>
                </form>
            </div>
        </div>

        <script>
            function toggleModal(show) { document.getElementById('formModal').style.display = show ? 'flex' : 'none'; }
            function closeModalOutside(e) { if (e.target === document.getElementById('formModal')) toggleModal(false); }
            document.getElementById('sosForm').onsubmit = function(e) {
                const fields = ['formNombre', 'formZona', 'formContacto', 'formDesc'];
                for(let id of fields) {
                    if(!document.getElementById(id).value.trim()) { e.preventDefault(); alert("⚠️ Por favor rellena todos los campos."); return false; }
                }
                if(!document.getElementById('principalInput').files[0]) { e.preventDefault(); alert("⚠️ Debes seleccionar una Foto Principal."); return false; }
                return true;
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_index, mascotas=mascotas_perdidas, es_admin=es_admin)

# =====================================================================
# 📄 RUTA DE DETALLES: PÁGINA INDIVIDUAL COMPLETA
# =====================================================================
@app.route('/mascota/<id>')
def detalle_mascota(id):
    # Buscar la mascota correspondiente por su ID único
    mascota = next((m for m in mascotas_perdidas if m["id"] == id), None)
    
    if not mascota:
        return redirect(url_for('index'))

    html_detalle = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Detalle de {{ mascota.nombre }}</title>
        <style>
            :root {
                --primary-gradient: linear-gradient(135deg, #ff6b4a, #ff9f43);
                --dark: #0f172a;
                --slate: #334155;
                --gray: #64748b;
                --success: #10b981;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: system-ui, -apple-system, sans-serif; background: #f8fafc; color: var(--dark); padding: 20px; }
            
            .detail-container { max-width: 650px; margin: 20px auto; background: white; border-radius: 24px; border: 1px solid #e2e8f0; overflow: hidden; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
            
            .btn-back { display: inline-flex; align-items: center; gap: 8px; color: var(--gray); text-decoration: none; font-weight: 600; font-size: 0.95em; margin-bottom: 24px; transition: color 0.2s; }
            .btn-back:active { color: var(--dark); }

            .hero-image-box { width: 100%; height: 320px; border-radius: 18px; overflow: hidden; background: #f1f5f9; cursor: pointer; margin-bottom: 16px; }
            .hero-image-box img { width: 100%; height: 100%; object-fit: cover; }

            .thumb-gallery { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-bottom: 24px; }
            .thumb-gallery img { width: 100%; height: 60px; object-fit: cover; border-radius: 10px; cursor: pointer; border: 1px solid #e2e8f0; }

            .info-box h2 { font-size: 2.2em; font-weight: 800; margin-bottom: 16px; letter-spacing: -0.02em; }
            
            .data-pills { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
            .pill { display: flex; align-items: center; gap: 8px; font-size: 0.95em; color: var(--slate); background: #f1f5f9; padding: 10px 14px; border-radius: 12px; }
            
            .description-box { font-size: 1.05em; color: var(--slate); line-height: 1.7; margin-bottom: 28px; border-top: 1px solid #e2e8f0; padding-top: 20px; }

            .btn-whatsapp { background: var(--success); color: white; text-decoration: none; padding: 16px; border-radius: 16px; text-align: center; font-weight: 700; font-size: 1.05em; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2); }

            /* Lightbox Pantalla Completa */
            .lightbox { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.95); display: none; justify-content: center; align-items: center; z-index: 400; }
            .lightbox img { max-width: 95%; max-height: 85vh; border-radius: 16px; object-fit: contain; }
        </style>
    </head>
    <body>

        <div class="detail-container">
            <!-- Botón de regreso al Inicio -->
            <a href="/" class="btn-back">← Regresar al inicio</a>

            <div class="hero-image-box" onclick="openLightbox(document.getElementById('mainPhoto').src)">
                {% if mascota.principal %}
                    <img src="{{ mascota.principal }}" id="mainPhoto" alt="Foto principal">
                {% else %}
                    <div style="display:flex; justify-content:center; align-items:center; height:100%; font-size:3em;">🐾</div>
                {% endif %}
            </div>

            <!-- Galería de fotos adicionales -->
            <div class="thumb-gallery">
                {% if mascota.principal %}
                <img src="{{ mascota.principal }}" alt="P" onclick="changeHero(this.src); openLightbox(this.src); event.stopPropagation();">
                {% endif %}
                {% for img in mascota.secundarias %}
                <img src="{{ img }}" alt="S" onclick="changeHero(this.src); openLightbox(this.src); event.stopPropagation();">
                {% endfor %}
            </div>

            <div class="info-box">
                <h2>{{ mascota.nombre }}</h2>
                
                <div class="data-pills">
                    <div class="pill">📍 <span><strong>Ubicación:</strong> {{ mascota.zona }}</span></div>
                    <div class="pill">📞 <span><strong>Teléfono de contacto:</strong> {{ mascota.contacto }}</span></div>
                </div>

                <div class="description-box">
                    <strong>Detalles del extravío:</strong>
                    <p style="margin-top: 6px;">{{ mascota.descripcion }}</p>
                </div>

                <a href="https://wa.me/{{ mascota.contacto }}" target="_blank" class="btn-whatsapp">💬 Contactar por WhatsApp</a>
            </div>
        </div>

        <div id="imageLightbox" class="lightbox" onclick="closeLightbox()">
            <img id="lightboxImg" src="">
        </div>

        <script>
            function changeHero(newSrc) { document.getElementById('mainPhoto').src = newSrc; }
            function openLightbox(src) { document.getElementById('lightboxImg').src = src; document.getElementById('imageLightbox').style.display = 'flex'; }
            function closeLightbox() { document.getElementById('imageLightbox').style.display = 'none'; }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_detalle, mascota=mascotas)

if __name__ == '__main__':
    app.run(debug=True)
