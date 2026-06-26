import os
import time
import base64
import traceback
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

ADMIN_TOKEN = "ubican123" 
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

mascotas_perdidas = []

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

            id_unico = str(int(time.time() * 1000))

            nuevo_reporte = {
                "id": id_unico,
                "nombre": request.form.get("nombre"),
                "descripcion": request.form.get("descripcion"),
                "zona": request.form.get("zona"),
                "contacto": request.form.get("contacto"),
                "principal": url_principal,
                "secundarias": lista_secundarias,
                # ── Campos nuevos ──────────────────────────────────────────
                "fecha":      request.form.get("fecha"),
                "edad":       request.form.get("edad"),
                "raza":       request.form.get("raza"),
                "genero":     request.form.get("genero"),
                "color":      request.form.get("color"),
                "collar":     request.form.get("collar"),
                "docil":      request.form.get("docil"),
                "direccion":  request.form.get("direccion"),
                "ciudad":     request.form.get("ciudad"),
                "estado":     request.form.get("estado"),
                "cp":         request.form.get("cp"),
                "calles":     request.form.get("calles"),
                "dueno":      request.form.get("dueno"),
                "recompensa": request.form.get("recompensa"),
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

            .grid-feed { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 24px; }
            
            .card-minimal { 
                background: var(--card-bg); border-radius: 20px; border: 1px solid #e2e8f0; overflow: hidden; 
                transition: transform 0.2s ease, box-shadow 0.2s ease; display: flex; flex-direction: column; height: 100%;
                position: relative;
            }
            .card-minimal:active { transform: scale(0.98); }
            @media (min-width: 768px) { .card-minimal:hover { transform: translateY(-4px); box-shadow: 0 12px 20px -8px rgba(0,0,0,0.08); } }

            .card-img-box { width: 100%; height: 260px; background: #f1f5f9; position: relative; }
            .card-img-box img { width: 100%; height: 100%; object-fit: cover; }
            .card-badge { position: absolute; top: 12px; right: 12px; background: #ef4444; color: white; font-size: 0.7em; font-weight: 800; padding: 4px 10px; border-radius: 99px; letter-spacing: 0.05em; z-index: 2; }
            
            .card-info { padding: 16px; display: flex; flex-direction: column; gap: 4px; }
            .card-info h3 { font-size: 1.15em; font-weight: 700; color: var(--dark); }
            .card-info p { color: var(--gray); font-size: 0.88em; display: flex; align-items: center; gap: 4px; }

            .stretched-link {
                position: absolute;
                top: 0; right: 0; bottom: 0; left: 0;
                z-index: 5;
                text-indent: -9999px;
                overflow: hidden;
            }

            .app-footer-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-top: 1px solid #e2e8f0; padding: 16px 24px; z-index: 100; display: flex; justify-content: center; }
            .btn-trigger-form { background: var(--primary-gradient); color: white; border: none; padding: 16px 32px; border-radius: 16px; font-weight: 700; font-size: 1em; cursor: pointer; width: 100%; max-width: 450px; text-align: center; box-shadow: 0 4px 12px rgba(255, 107, 74, 0.2); }

            .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.4); display: none; align-items: flex-end; justify-content: center; z-index: 200; backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
            .modal-box { background: var(--card-bg); width: 100%; max-width: 500px; border-top-left-radius: 28px; border-top-right-radius: 28px; padding: 24px; max-height: 85vh; overflow-y: auto; }
            .modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .btn-close { background: #f1f5f9; border: none; font-size: 1em; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; }
            .form-group { margin-bottom: 16px; }
            .form-group label { display: block; font-size: 0.85em; font-weight: 700; margin-bottom: 6px; color: #475569; }
            .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 12px 14px; border: 1px solid #cbd5e1; border-radius: 12px; font-size: 0.95em; font-family: inherit; outline: none; background: #f8fafc; }
            .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
            .form-section-title { font-size: 0.8em; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin: 20px 0 10px 0; border-top: 1px solid #e2e8f0; padding-top: 20px; }
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
                <p>Haz clic en cualquier tarjeta para ver toda la información de contacto.</p>
            </div>

            <div class="grid-feed">
                {% if not mascotas %}
                    <div style="grid-column: 1/-1; text-align: center; color: var(--gray); padding: 60px 0; font-style: italic;">
                        📍 No hay alertas activas en este momento.
                    </div>
                {% endif %}
                
                {% for mascota in mascotas %}
                <div class="card-minimal">
                    <a href="/mascota/{{ mascota.id }}" class="stretched-link">Ver detalles</a>
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
                        {% if mascota.raza %}<p>🐶 {{ mascota.raza }}</p>{% endif %}
                    </div>
                </div>
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

                    <p class="form-section-title">🐾 Datos de la mascota</p>
                    <div class="form-group"><label>Nombre de la mascota *</label><input type="text" id="formNombre" name="nombre" placeholder="Ej. Rocko"></div>
                    <div class="form-row">
                        <div class="form-group"><label>Especie / Raza</label><input type="text" name="raza" placeholder="Ej. Labrador"></div>
                        <div class="form-group"><label>Edad</label><input type="text" name="edad" placeholder="Ej. 3 años"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Género</label>
                            <select name="genero">
                                <option value="">-- Seleccionar --</option>
                                <option value="Macho">Macho</option>
                                <option value="Hembra">Hembra</option>
                            </select>
                        </div>
                        <div class="form-group"><label>Color / Pelaje</label><input type="text" name="color" placeholder="Ej. Café con blanco"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>¿Trae collar?</label>
                            <select name="collar">
                                <option value="">-- Seleccionar --</option>
                                <option value="Sí">Sí</option>
                                <option value="No">No</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>¿Es dócil?</label>
                            <select name="docil">
                                <option value="">-- Seleccionar --</option>
                                <option value="Sí">Sí</option>
                                <option value="No">No</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-group"><label>Descripción *</label><textarea id="formDesc" name="descripcion" rows="3" placeholder="Señas particulares, comportamiento..."></textarea></div>

                    <p class="form-section-title">📍 Lugar del extravío</p>
                    <div class="form-group"><label>Fecha en que se perdió</label><input type="date" name="fecha"></div>
                    <div class="form-group"><label>Colonia / Zona *</label><input type="text" id="formZona" name="zona" placeholder="Ej. Col. Centro"></div>
                    <div class="form-group"><label>Dirección exacta</label><input type="text" name="direccion" placeholder="Ej. Calle Hidalgo 123"></div>
                    <div class="form-group"><label>Entre calles</label><input type="text" name="calles" placeholder="Ej. Entre Juárez y Allende"></div>
                    <div class="form-row">
                        <div class="form-group"><label>Ciudad</label><input type="text" name="ciudad" placeholder="Ej. Juárez"></div>
                        <div class="form-group"><label>Estado</label><input type="text" name="estado" placeholder="Ej. Chihuahua"></div>
                    </div>
                    <div class="form-group"><label>Código Postal</label><input type="text" name="cp" placeholder="Ej. 32000"></div>

                    <p class="form-section-title">👤 Datos del dueño</p>
                    <div class="form-group"><label>Nombre del dueño</label><input type="text" name="dueno" placeholder="Ej. Carlos Ramírez"></div>
                    <div class="form-group"><label>Teléfono (WhatsApp) *</label><input type="tel" id="formContacto" name="contacto" placeholder="Ej. 526561234567"></div>
                    <div class="form-group"><label>Recompensa</label><input type="text" name="recompensa" placeholder="Ej. $500 MXN o 'Sí, negociable'"></div>

                    <p class="form-section-title">📸 Fotos</p>
                    <div class="form-group"><label>Foto Principal *</label><input type="file" id="principalInput" name="imagen_principal" accept="image/*" class="file-input-styled"></div>
                    <div class="form-group"><label>Fotos Adicionales (Máx 4)</label><input type="file" id="secundariasInput" name="imagenes_secundarias" accept="image/*" multiple class="file-input-styled"></div>

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
                    if(!document.getElementById(id).value.trim()) { e.preventDefault(); alert("⚠️ Por favor rellena todos los campos obligatorios."); return false; }
                }
                if(!document.getElementById('principalInput').files[0]) { e.preventDefault(); alert("⚠️ Debes seleccionar una Foto Principal."); return false; }
                return true;
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_index, mascotas=mascotas_perdidas, es_admin=es_admin)


@app.route('/mascota/<id>')
def detalle_mascota(id):
    mascota = next((m for m in mascotas_perdidas if m["id"] == id), None)
    
    if not mascota:
        return redirect(url_for('index'))

    html_detalle = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ mascota.nombre }} — Ubican ID SOS</title>
        <style>
            :root {
                --primary-gradient: linear-gradient(135deg, #ff6b4a, #ff9f43);
                --dark: #0f172a;
                --slate: #334155;
                --gray: #64748b;
                --success: #10b981;
                --bg: #f8fafc;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
            body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--dark); padding: 24px 16px 120px 16px; }
            
            .detail-container { max-width: 600px; margin: 0 auto; background: transparent; }
            
            .btn-back { display: inline-flex; align-items: center; gap: 8px; color: var(--gray); text-decoration: none; font-weight: 600; font-size: 0.95em; margin-bottom: 24px; transition: color 0.2s; }
            .btn-back:active { color: var(--dark); }

            .hero-image-box { width: 100%; height: 350px; border-radius: 24px; overflow: hidden; background: #e2e8f0; cursor: pointer; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }
            .hero-image-box img { width: 100%; height: 100%; object-fit: cover; }

            .thumb-gallery { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 28px; }
            .thumb-gallery img { width: 100%; height: 65px; object-fit: cover; border-radius: 12px; cursor: pointer; border: 1px solid #e2e8f0; background: #fff; }

            .info-box h2 { font-size: 2.4em; font-weight: 800; margin-bottom: 18px; letter-spacing: -0.03em; }

            /* Sección con título interno */
            .detail-section { margin-bottom: 20px; }
            .detail-section-title { font-size: 0.75em; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 10px; }

            .data-pills { display: flex; flex-direction: column; gap: 8px; }
            .pill { display: flex; align-items: center; gap: 8px; font-size: 0.93em; color: var(--slate); background: #ffffff; padding: 11px 14px; border-radius: 12px; border: 1px solid #e2e8f0; }
            .pill-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

            /* Badge especial para recompensa */
            .reward-badge { display: inline-flex; align-items: center; gap: 6px; background: #fef3c7; color: #92400e; border: 1px solid #fde68a; padding: 10px 14px; border-radius: 12px; font-weight: 700; font-size: 0.95em; margin-bottom: 20px; }

            .description-box { font-size: 1.02em; color: var(--slate); line-height: 1.7; margin-bottom: 28px; border-top: 1px solid #e2e8f0; padding-top: 20px; }

            .btn-whatsapp { background: var(--success); color: white; text-decoration: none; padding: 16px; border-radius: 18px; text-align: center; font-weight: 700; font-size: 1.05em; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 6px 20px rgba(16, 185, 129, 0.25); }

            .lightbox { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.95); display: none; justify-content: center; align-items: center; z-index: 400; }
            .lightbox img { max-width: 95%; max-height: 85vh; border-radius: 16px; object-fit: contain; }
        </style>
    </head>
    <body>

        <div class="detail-container">
            <a href="/" class="btn-back">← Regresar al inicio</a>

            <div class="hero-image-box" onclick="openLightbox(document.getElementById('mainPhoto').src)">
                {% if mascota.principal %}
                    <img src="{{ mascota.principal }}" id="mainPhoto" alt="Foto principal">
                {% else %}
                    <div style="display:flex; justify-content:center; align-items:center; height:100%; font-size:3em;" id="mainPhoto">🐾</div>
                {% endif %}
            </div>

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

                {% if mascota.recompensa %}
                <div class="reward-badge">🏅 Recompensa: {{ mascota.recompensa }}</div>
                {% endif %}

                <!-- Datos de la mascota -->
                <div class="detail-section">
                    <div class="detail-section-title">🐾 Datos de la mascota</div>
                    <div class="data-pills">
                        <div class="pill-grid">
                            {% if mascota.raza %}<div class="pill">🐶 <span><strong>Raza:</strong> {{ mascota.raza }}</span></div>{% endif %}
                            {% if mascota.edad %}<div class="pill">🎂 <span><strong>Edad:</strong> {{ mascota.edad }}</span></div>{% endif %}
                            {% if mascota.genero %}<div class="pill">⚧ <span><strong>Género:</strong> {{ mascota.genero }}</span></div>{% endif %}
                            {% if mascota.color %}<div class="pill">🎨 <span><strong>Color:</strong> {{ mascota.color }}</span></div>{% endif %}
                            {% if mascota.collar %}<div class="pill">🔖 <span><strong>Collar:</strong> {{ mascota.collar }}</span></div>{% endif %}
                            {% if mascota.docil %}<div class="pill">🤝 <span><strong>Dócil:</strong> {{ mascota.docil }}</span></div>{% endif %}
                        </div>
                    </div>
                </div>

                <!-- Lugar del extravío -->
                <div class="detail-section">
                    <div class="detail-section-title">📍 Lugar del extravío</div>
                    <div class="data-pills">
                        {% if mascota.fecha %}<div class="pill">📅 <span><strong>Fecha:</strong> {{ mascota.fecha }}</span></div>{% endif %}
                        {% if mascota.zona %}<div class="pill">🗺️ <span><strong>Zona/Colonia:</strong> {{ mascota.zona }}</span></div>{% endif %}
                        {% if mascota.direccion %}<div class="pill">🏠 <span><strong>Dirección:</strong> {{ mascota.direccion }}</span></div>{% endif %}
                        {% if mascota.calles %}<div class="pill">🔀 <span><strong>Entre calles:</strong> {{ mascota.calles }}</span></div>{% endif %}
                        {% if mascota.ciudad or mascota.estado %}
                        <div class="pill">🏙️ <span><strong>Ciudad/Estado:</strong> {{ mascota.ciudad }}{% if mascota.ciudad and mascota.estado %}, {% endif %}{{ mascota.estado }}</span></div>
                        {% endif %}
                        {% if mascota.cp %}<div class="pill">📮 <span><strong>C.P.:</strong> {{ mascota.cp }}</span></div>{% endif %}
                    </div>
                </div>

                <!-- Datos del dueño -->
                <div class="detail-section">
                    <div class="detail-section-title">👤 Datos del dueño</div>
                    <div class="data-pills">
                        {% if mascota.dueno %}<div class="pill">👤 <span><strong>Nombre:</strong> {{ mascota.dueno }}</span></div>{% endif %}
                        <div class="pill">📞 <span><strong>Teléfono:</strong> {{ mascota.contacto }}</span></div>
                    </div>
                </div>

                <!-- Descripción -->
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
    return render_template_string(html_detalle, mascota=mascota)


if __name__ == '__main__':
    app.run(debug=True)
