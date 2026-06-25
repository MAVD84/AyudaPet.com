import os
import base64
from flask import Flask, request, jsonify, render_template_string, redirect, url_for

app = Flask(__name__)

# Configuración del Admin (Token Secreto)
ADMIN_TOKEN = "ubican123" 

# BASE DE DATOS EN MEMORIA (Inicia limpia)
mascotas_perdidas = []

@app.route('/', methods=['GET', 'POST'])
def index():
    token_ingresado = request.args.get('admin')
    es_admin = (token_ingresado == ADMIN_TOKEN)

    if request.method == 'POST':
        archivos = request.files.getlist("imagenes")
        lista_imagenes_base64 = []

        for archivo in archivos[:5]:
            if archivo and archivo.filename != '':
                bytes_imagen = archivo.read()
                base64_codificado = base64.b64encode(bytes_imagen).decode('utf-8')
                data_url = f"data:{archivo.content_type};base64,{base64_codificado}"
                lista_imagenes_base64.append(data_url)

        nuevo_reporte = {
            "nombre": request.form.get("nombre"),
            "descripcion": request.form.get("descripcion"),
            "zona": request.form.get("zona"),
            "contacto": request.form.get("contacto"),
            "imagenes": lista_imagenes_base64
        }
        
        mascotas_perdidas.insert(0, nuevo_reporte)
        if es_admin:
            return redirect(url_for('index', admin=ADMIN_TOKEN))
        return redirect(url_for('index'))

    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ubican ID SOS | Panel de Alertas</title>
        <style>
            :root {
                --primary: #f39c12;
                --primary-gradient: linear-gradient(135deg, #ff6b4a, #ff9f43);
                --dark: #0f172a;
                --gray-text: #64748b;
                --bg: #f8fafc;
                --card-bg: #ffffff;
                --success: #10b981;
                --danger: #ef4444;
            }

            * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
            body { font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif; background-color: var(--bg); color: var(--dark); padding-bottom: 90px; }

            .navbar {
                background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
                position: sticky; top: 0; z-index: 90; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center;
                border-bottom: 1px solid rgba(226, 232, 240, 0.8);
            }
            .navbar-brand { font-size: 1.25em; font-weight: 800; color: var(--dark); display: flex; align-items: center; gap: 8px; }
            .navbar-brand span { background: var(--primary-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            
            .admin-banner { background: #fee2e2; color: var(--danger); padding: 8px; text-align: center; font-size: 0.85em; font-weight: 700; border-radius: 8px; margin-bottom: 20px; }

            .main-container { max-width: 1200px; margin: 40px auto; padding: 0 24px; }
            .section-intro { margin-bottom: 32px; }
            .section-intro h2 { font-size: 1.75em; font-weight: 800; margin-bottom: 6px; }
            .section-intro p { color: var(--gray-text); font-size: 0.95em; }

            .grid-feed { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 24px; }
            
            .card { background: var(--card-bg); border-radius: 20px; border: 1px solid #e2e8f0; overflow: hidden; display: flex; flex-direction: column; transition: transform 0.25s ease, box-shadow 0.25s ease; }
            .card:hover { transform: translateY(-4px); box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05); }
            .card-body { padding: 24px; flex: 1; display: flex; flex-direction: column; }
            
            .card-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
            .card-badge { background: #fee2e2; color: var(--danger); font-size: 0.75em; font-weight: 700; padding: 4px 12px; border-radius: 99px; }
            .card-title { font-size: 1.4em; font-weight: 800; }

            .info-row { display: flex; font-size: 0.9em; margin-bottom: 8px; }
            .info-row strong { color: var(--dark); width: 85px; flex-shrink: 0; }
            .info-row span { color: var(--gray-text); }
            
            .card-description { background: #f8fafc; padding: 14px; border-radius: 12px; font-size: 0.92em; color: #475569; margin: 16px 0; line-height: 1.5; border-left: 4px solid var(--primary); flex: 1; }

            .card-gallery { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 12px; }
            .card-gallery img { width: 75px; height: 75px; object-fit: cover; border-radius: 10px; cursor: pointer; border: 1px solid #f1f5f9; }
            .no-photos { font-size: 0.8em; color: var(--gray-text); font-style: italic; margin-bottom: 16px; text-align: center; background: #f1f5f9; padding: 10px; border-radius: 10px; }

            .btn-whatsapp { background: #10b981; color: white; text-decoration: none; padding: 12px; border-radius: 12px; text-align: center; font-weight: 700; font-size: 0.9em; display: block; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2); }
            
            .btn-delete { background: #ef4444; color: white; text-decoration: none; padding: 10px; border-radius: 12px; text-align: center; font-weight: 700; font-size: 0.85em; display: block; margin-top: 8px; border: none; cursor: pointer; width: 100%; }

            /* EL FOOTER FIJO DE ACCIÓN */
            .app-footer-bar { 
                position: fixed; bottom: 0; left: 0; width: 100%; 
                background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
                border-top: 1px solid #e2e8f0; padding: 16px 24px; z-index: 100;
                display: flex; justify-content: center; align-items: center;
                box-shadow: 0 -10px 25px rgba(15, 23, 42, 0.04);
            }
            .btn-trigger-form {
                background: var(--primary-gradient); color: white; border: none;
                padding: 14px 28px; border-radius: 14px; font-weight: 700; font-size: 0.95em;
                cursor: pointer; width: 100%; max-width: 500px; text-align: center;
                box-shadow: 0 4px 14px rgba(255, 107, 74, 0.3); transition: transform 0.2s ease;
            }
            .btn-trigger-form:active { transform: scale(0.98); }

            /* EL FORMULARIO DESLIZANTE DESDE ABAJO */
            .modal-overlay { 
                position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                background: rgba(15, 23, 42, 0); backdrop-filter: blur(0px); -webkit-backdrop-filter: blur(0px);
                display: none; align-items: flex-end; justify-content: center; z-index: 200;
                transition: background 0.3s ease, backdrop-filter 0.3s ease;
            }
            .modal-overlay.active { 
                background: rgba(15, 23, 42, 0.5); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
            }
            .modal-box { 
                background: var(--card-bg); width: 100%; max-width: 550px; 
                border-top-left-radius: 28px; border-top-right-radius: 28px; 
                padding: 32px 24px; max-height: 85vh; overflow-y: auto; 
                transform: translateY(100%); transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1); 
                box-shadow: 0 -15px 30px rgba(0,0,0,0.1);
            }
            .modal-overlay.active .modal-box { transform: translateY(0); }
            
            .modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
            .btn-close { background: #f1f5f9; border: none; font-size: 1em; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; }

            .form-group { margin-bottom: 18px; }
            .form-group label { display: block; font-size: 0.85em; font-weight: 700; margin-bottom: 6px; }
            .form-group input, .form-group textarea { width: 100%; padding: 12px 16px; border: 1px solid #cbd5e1; border-radius: 12px; font-size: 0.95em; font-family: inherit; outline: none; }
            .form-group input:focus, .form-group textarea:focus { border-color: #ff6b4a; }
            .form-group textarea { height: 90px; resize: none; }
            .btn-publish { background: var(--primary-gradient); color: white; border: none; width: 100%; padding: 14px; border-radius: 12px; font-weight: 700; font-size: 1em; cursor: pointer; margin-top: 12px; }

            .lightbox { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(10px); display: none; justify-content: center; align-items: center; z-index: 300; }
            .lightbox img { max-width: 90%; max-height: 80vh; border-radius: 16px; }
            .lightbox-close { position: absolute; top: 24px; right: 24px; color: white; font-size: 32px; cursor: pointer; }
            @media (max-width: 600px) { .grid-feed { grid-template-columns: 1fr; } }
        </style>
    </head>
    <body>

        <div class="navbar">
            <div class="navbar-brand">🐾 <span>Ubican ID</span> SOS</div>
        </div>

        <div class="main-container">
            {% if es_admin %}
            <div class="admin-banner">
                🛠️ MODO ADMINISTRADOR ACTIVO — Tienes permisos para eliminar reportes falsos o viejos.
            </div>
            {% endif %}

            <div class="section-intro">
                <h2>Mascotas Extraviadas</h2>
                <p>Red comunitaria en tiempo real para reportes y avistamientos.</p>
            </div>

            <div class="grid-feed">
                {% if not mascotas %}
                    <p style="grid-column: 1/-1; text-align: center; color: var(--gray-text); padding: 60px 0; font-style: italic;">
                        No hay alertas SOS activas en este momento.
                    </p>
                {% endif %}
                
                {% for mascota in mascotas %}
                <div class="card">
                    <div class="card-body">
                        <div class="card-meta">
                            <h3 class="card-title">{{ mascota.nombre }}</h3>
                            <span class="card-badge">SOS</span>
                        </div>
                        
                        <div class="info-row"><strong>📍 Zona:</strong> <span>{{ mascota.zona }}</span></div>
                        <div class="info-row"><strong>📞 Contacto:</strong> <span>{{ mascota.contacto }}</span></div>
                        
                        <div class="card-description">
                            {{ mascota.descripcion }}
                        </div>

                        {% if mascota.imagenes %}
                        <div class="card-gallery">
                            {% for img in mascota.imagenes %}
                            <img src="{{ img }}" alt="Foto" onclick="openLightbox(this.src)">
                            {% endfor %}
                        </div>
                        {% else %}
                        <div class="no-photos">Sin fotografías adjuntas</div>
                        {% endif %}

                        <a href="https://wa.me/{{ mascota.contacto }}?text=Hola" target="_blank" class="btn-whatsapp">
                            💬 Informar Avistamiento
                        </a>

                        {% if es_admin %}
                        <form method="POST" action="/eliminar/{{ loop.index0 }}">
                            <input type="hidden" name="admin_token" value="{{ admin_token }}">
                            <button type="submit" class="btn-delete" onclick="return confirm('¿Seguro que quieres borrar a {{ mascota.nombre }}?')">
                                🗑️ Eliminar Reporte
                            </button>
                        </form>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- EL FOOTER CON EL ACCESO AL FORMULARIO -->
        <div class="app-footer-bar">
            <button class="btn-trigger-form" onclick="toggleModal(true)">🚨 Reportar Mascota Perdida</button>
        </div>

        <!-- PANEL SLIDE-UP DESDE EL FONDO -->
        <div id="formModal" class="modal-overlay" onclick="closeModalOutside(event)">
            <div class="modal-box">
                <div class="modal-head">
                    <h3>Crear Reporte de Extravío</h3>
                    <button class="btn-close" onclick="toggleModal(false)">✕</button>
                </div>
                <form method="POST" action="/?admin={% if es_admin %}{{ admin_token }}{% endif %}" enctype="multipart/form-data" id="sosForm">
                    <div class="form-group">
                        <label>Nombre de la mascota</label>
                        <input type="text" name="nombre" required>
                    </div>
                    <div class="form-group">
                        <label>¿Dónde se vio por última vez? (Zona/Colonia)</label>
                        <input type="text" name="zona" required>
                    </div>
                    <div class="form-group">
                        <label>Teléfono de contacto (WhatsApp)</label>
                        <input type="tel" name="contacto" required>
                    </div>
                    <div class="form-group">
                        <label>Descripción / Señas particulares</label>
                        <textarea name="descripcion" required></textarea>
                    </div>
                    <div class="form-group">
                        <label>Fotografías (Máximo 5)</label>
                        <input type="file" id="filesInput" name="imagenes" accept="image/*" multiple style="padding: 8px 0;">
                    </div>
                    <button type="submit" class="btn-publish">🚨 Publicar Alerta SOS</button>
                </form>
            </div>
        </div>

        <div id="imageLightbox" class="lightbox" onclick="closeLightbox()">
            <span class="lightbox-close">&times;</span>
            <img id="lightboxImg" src="" alt="Ampliada">
        </div>

        <script>
            function toggleModal(show) {
                const modal = document.getElementById('formModal');
                if (show) { 
                    modal.style.display = 'flex'; 
                    setTimeout(() => modal.classList.add('active'), 10); 
                } else { 
                    modal.classList.remove('active'); 
                    setTimeout(() => modal.style.display = 'none', 300); 
                }
            }
            if (window.history.replaceState) { window.history.replaceState( null, null, window.location.href ); }
            function closeModalOutside(e) { if (e.target === document.getElementById('formModal')) toggleModal(false); }
            function openLightbox(src) { document.getElementById('lightboxImg').src = src; document.getElementById('imageLightbox').style.display = 'flex'; }
            function closeLightbox() { document.getElementById('imageLightbox').style.display = 'none'; }
            document.getElementById('sosForm').onsubmit = function() {
                const files = document.getElementById('filesInput').files;
                if(files.length > 5) { alert("⚠️ Selecciona un máximo de 5 fotografías."); return false; }
                return true;
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content, mascotas=mascotas_perdidas, es_admin=es_admin, admin_token=ADMIN_TOKEN)

@app.route('/eliminar/<int:index>', methods=['POST'])
def eliminar_mascota(index):
    token_verificacion = request.form.get('admin_token')
    if token_verificacion == ADMIN_TOKEN:
        if 0 <= index < len(mascotas_perdidas):
            mascotas_perdidas.pop(index)
    return redirect(url_for('index', admin=ADMIN_TOKEN))

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    return jsonify({"status": "success"}), 200
