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
        # 1. PROCESAR FOTO PRINCIPAL
        foto_principal = request.files.get("imagen_principal")
        url_principal = ""
        if foto_principal and foto_principal.filename != '':
            bytes_p = foto_principal.read()
            b64_p = base64.b64encode(bytes_p).decode('utf-8')
            url_principal = f"data:{foto_principal.content_type};base64,{b64_p}"

        # 2. PROCESAR FOTOS SECUNDARIAS (Máximo 4)
        fotos_secundarias = request.files.getlist("imagenes_secundarias")
        lista_secundarias = []
        for archivo in fotos_secundarias[:4]: # Capamos estrictamente a 4
            if archivo and archivo.filename != '':
                bytes_s = archivo.read()
                b64_s = base64.b64encode(bytes_s).decode('utf-8')
                data_url = f"data:{archivo.content_type};base64,{b64_s}"
                lista_secundarias.append(data_url)

        nuevo_reporte = {
            "nombre": request.form.get("nombre"),
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
                --slate-700: #334155;
                --gray-text: #64748b;
                --bg: #f8fafc;
                --card-bg: #ffffff;
                --success: #10b981;
                --danger: #ef4444;
                --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
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
            
            .admin-banner { background: #fee2e2; color: var(--danger); padding: 10px; text-align: center; font-size: 0.85em; font-weight: 700; border-radius: 12px; margin-bottom: 24px; border: 1px solid #fca5a5; }

            .main-container { max-width: 1200px; margin: 40px auto; padding: 0 24px; }
            .section-intro { margin-bottom: 32px; }
            .section-intro h2 { font-size: 2em; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 6px; }
            .section-intro p { color: var(--gray-text); font-size: 0.98em; }

            .grid-feed { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 28px; }
            
            .card { 
                background: var(--card-bg); border-radius: 24px; border: 1px solid #e2e8f0; overflow: hidden; 
                display: flex; flex-direction: column; transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
                box-shadow: var(--shadow-sm);
            }
            .card:hover { transform: translateY(-6px); box-shadow: 0 20px 25px -5px rgba(15, 23, 42, 0.08); }

            /* CONTENEDOR FOTO PRINCIPAL */
            .card-hero-image { width: 100%; height: 240px; position: relative; overflow: hidden; background: #f1f5f9; }
            .card-hero-image img { width: 100%; height: 100%; object-fit: cover; cursor: pointer; }
            
            .card-hero-placeholder { width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: linear-gradient(135deg, #f8fafc, #e2e8f0); color: var(--gray-text); gap: 8px; }
            .card-hero-placeholder span { font-size: 3rem; }

            .card-floating-badge { position: absolute; top: 16px; right: 16px; background: var(--danger); color: white; font-size: 0.75em; font-weight: 800; padding: 6px 14px; border-radius: 99px; letter-spacing: 0.05em; box-shadow: 0 4px 6px rgba(239, 68, 68, 0.2); }

            .card-body { padding: 24px; flex: 1; display: flex; flex-direction: column; }
            .card-title { font-size: 1.5em; font-weight: 800; color: var(--dark); margin-bottom: 12px; }

            .card-data-box { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
            .data-pill { display: flex; align-items: center; gap: 8px; font-size: 0.88em; color: var(--slate-700); background: #f1f5f9; padding: 8px 12px; border-radius: 10px; }
            .data-pill strong { color: var(--dark); font-weight: 700; }

            .card-description { font-size: 0.95em; color: var(--slate-700); line-height: 1.6; margin-bottom: 20px; flex: 1; }

            /* GALERÍA DE 4 IMÁGENES ABAJO */
            .card-thumb-gallery { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 20px; }
            .card-thumb-gallery img { width: 100%; height: 65px; object-fit: cover; border-radius: 12px; cursor: pointer; border: 2px solid transparent; transition: border-color 0.2s, transform 0.2s; }
            .card-thumb-gallery img:hover { border-color: #ff6b4a; transform: scale(1.03); }

            .btn-whatsapp { background: var(--success); color: white; text-decoration: none; padding: 14px; border-radius: 16px; text-align: center; font-weight: 700; font-size: 0.95em; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15); }
            .btn-whatsapp:hover { background: #059669; }
            
            .btn-delete { background: #fff5f5; color: var(--danger); text-decoration: none; padding: 10px; border-radius: 14px; text-align: center; font-weight: 700; font-size: 0.85em; display: block; margin-top: 10px; border: 1px dashed rgba(239, 68, 68, 0.3); cursor: pointer; width: 100%; }
            .btn-delete:hover { background: #fee2e2; }

            /* FOOTER */
            .app-footer-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-top: 1px solid #e2e8f0; padding: 16px 24px; z-index: 100; display: flex; justify-content: center; align-items: center; box-shadow: 0 -10px 30px rgba(15, 23, 42, 0.05); }
            .btn-trigger-form { background: var(--primary-gradient); color: white; border: none; padding: 16px 32px; border-radius: 16px; font-weight: 700; font-size: 1em; cursor: pointer; width: 100%; max-width: 500px; text-align: center; box-shadow: 0 6px 20px rgba(255, 107, 74, 0.25); }

            /* MODAL SLIDE-UP */
            .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0); display: none; align-items: flex-end; justify-content: center; z-index: 200; transition: background 0.3s ease; }
            .modal-overlay.active { background: rgba(15, 23, 42, 0.4); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
            .modal-box { background: var(--card-bg); width: 100%; max-width: 550px; border-top-left-radius: 32px; border-top-right-radius: 32px; padding: 32px 24px; max-height: 85vh; overflow-y: auto; transform: translateY(100%); transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
            .modal-overlay.active .modal-box { transform: translateY(0); }
            
            .modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
            .btn-close { background: #f1f5f9; border: none; font-size: 1em; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; }

            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; font-size: 0.85em; font-weight: 700; margin-bottom: 8px; color: var(--slate-700); }
            .form-group input, .form-group textarea { width: 100%; padding: 14px 16px; border: 1px solid #cbd5e1; border-radius: 14px; font-size: 0.95em; font-family: inherit; outline: none; background: #f8fafc; }
            .form-group input:focus, .form-group textarea:focus { border-color: #ff6b4a; background: white; }
            .form-group textarea { height: 100px; resize: none; }
            
            .file-input-wrapper { background: #f1f5f9; border: 2px dashed #cbd5e1; padding: 12px; border-radius: 14px; text-align: center; position: relative; cursor: pointer; }
            .file-input-wrapper input { absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }

            .btn-publish { background: var(--primary-gradient); color: white; border: none; width: 100%; padding: 16px; border-radius: 14px; font-weight: 700; font-size: 1em; cursor: pointer; margin-top: 12px; }

            .lightbox { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(12px); display: none; justify-content: center; align-items: center; z-index: 300; }
            .lightbox img { max-width: 90%; max-height: 80vh; border-radius: 20px; }
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
                🛠️ MODO ADMINISTRADOR ACTIVO — Tienes permisos para gestionar y eliminar reportes.
            </div>
            {% endif %}

            <div class="section-intro">
                <h2>Mascotas Extraviadas</h2>
                <p>Ayúdanos a reportar avistamientos. La comunidad unida los lleva a casa.</p>
            </div>

            <div class="grid-feed">
                {% if not mascotas %}
                    <p style="grid-column: 1/-1; text-align: center; color: var(--gray-text); padding: 80px 0; font-style: italic; font-size: 1.05em;">
                        📍 No hay alertas activas en este momento. La red está limpia.
                    </p>
                {% endif %}
                
                {% for mascota in mascotas %}
                <div class="card">
                    <!-- FOTO PRINCIPAL (HERO) -->
                    <div class="card-hero-image">
                        <span class="card-floating-badge">ALERTA SOS</span>
                        {% if mascota.principal %}
                            <img src="{{ mascota.principal }}" alt="Foto de {{ mascota.nombre }}" id="mainPhoto-{{ loop.index0 }}" onclick="openLightbox(this.src)">
                        {% else %}
                            <div class="card-hero-placeholder">
                                <span>🐾</span>
                                <p>Sin foto de portada</p>
                            </div>
                        {% endif %}
                    </div>

                    <div class="card-body">
                        <h3 class="card-title">{{ mascota.nombre }}</h3>
                        
                        <div class="card-data-box">
                            <div class="data-pill">
                                <span>📍</span>
                                <span><strong>Zona:</strong> {{ mascota.zona }}</span>
                            </div>
                            <div class="data-pill">
                                <span>📞</span>
                                <span><strong>Contacto:</strong> {{ mascota.contacto }}</span>
                            </div>
                        </div>
                        
                        <p class="card-description">
                            {{ mascota.descripcion }}
                        </p>

                        <!-- LAS 4 FOTOS DEBAJO -->
                        {% if mascota.secundarias %}
                        <div class="card-thumb-gallery">
                            <!-- Agregamos la foto principal original como primera opción para poder regresar a ella -->
                            <img src="{{ mascota.principal }}" alt="Portada" onclick="changeHero('{{ loop.index0 }}', this.src)">
                            
                            {% for img in mascota.secundarias %}
                            <img src="{{ img }}" alt="Miniatura" onclick="changeHero('{{ loop.parent.index0 }}', this.src)">
                            {% endfor %}
                        </div>
                        {% endif %}

                        <a href="https://wa.me/{{ mascota.contacto }}?text=Hola,%20tengo%20información%20sobre%20{{ mascota.nombre }}" target="_blank" class="btn-whatsapp">
                            💬 Enviar Mensaje / Avistamiento
                        </a>

                        {% if es_admin %}
                        <form method="POST" action="/eliminar/{{ loop.index0 }}">
                            <input type="hidden" name="admin_token" value="{{ admin_token }}">
                            <button type="submit" class="btn-delete" onclick="return confirm('¿Seguro que deseas eliminar el reporte de {{ mascota.nombre }}?')">
                                🗑️ Eliminar Reporte Permanente
                            </button>
                        </form>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- FOOTER -->
        <div class="app-footer-bar">
            <button class="btn-trigger-form" onclick="toggleModal(true)">🚨 Reportar Mascota Perdida</button>
        </div>

        <!-- FORMULARIO SLIDE-UP REESTRUCTURADO -->
        <div id="formModal" class="modal-overlay" onclick="closeModalOutside(event)">
            <div class="modal-box">
                <div class="modal-head">
                    <h3>Registrar Reporte de Extravío</h3>
                    <button class="btn-close" onclick="toggleModal(false)">✕</button>
                </div>
                <form method="POST" action="/?admin={% if es_admin %}{{ admin_token }}{% endif %}" enctype="multipart/form-data" id="sosForm">
                    <div class="form-group">
                        <label>Nombre de la mascota</label>
                        <input type="text" name="nombre" placeholder="Ej. Rocko, Luna..." required>
                    </div>
                    <div class="form-group">
                        <label>¿Dónde se extravió? (Zona / Colonia)</label>
                        <input type="text" name="zona" placeholder="Ej. Col. San Ángel, cerca del parque" required>
                    </div>
                    <div class="form-group">
                        <label>Teléfono de contacto (WhatsApp)</label>
                        <input type="tel" name="contacto" placeholder="Ej. 526561234567" required>
                    </div>
                    <div class="form-group">
                        <label>Descripción / Señas particulares</label>
                        <textarea name="descripcion" placeholder="Ej. Lleva un collar rojo, tiene una mancha blanca..." required></textarea>
                    </div>
                    
                    <!-- CAMPO 1: FOTO DE PORTADA (OBLIGATORIA) -->
                    <div class="form-group">
                        <label>📸 Foto Principal (Aparecerá en grande arriba) *</label>
                        <input type="file" name="imagen_principal" accept="image/*" required style="padding: 4px 0;">
                    </div>

                    <!-- CAMPO 2: FOTOS SECUNDARIAS (HASTA 4) -->
                    <div class="form-group">
                        <label>🐾 Fotos Adicionales de Apoyo (Máximo 4 imágenes debajo)</label>
                        <input type="file" id="secundariasInput" name="imagenes_secundarias" accept="image/*" multiple style="padding: 4px 0;">
                    </div>

                    <button type="submit" class="btn-publish">🚨 Publicar Alerta de Inmediato</button>
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
                if (show) { modal.style.display = 'flex'; setTimeout(() => modal.classList.add('active'), 10); }
                else { modal.classList.remove('active'); setTimeout(() => modal.style.display = 'none', 300); }
            }
            if (window.history.replaceState) { window.history.replaceState( null, null, window.location.href ); }
            function closeModalOutside(e) { if (e.target === document.getElementById('formModal')) toggleModal(false); }
            
            function changeHero(cardIndex, newSrc) {
                document.getElementById('mainPhoto-' + cardIndex).src = newSrc;
            }

            function openLightbox(src) { document.getElementById('lightboxImg').src = src; document.getElementById('imageLightbox').style.display = 'flex'; }
            function closeLightbox() { document.getElementById('imageLightbox').style.display = 'none'; }
            
            // Validación estricta antes de subir
            document.getElementById('sosForm').onsubmit = function() {
                const files = document.getElementById('secundariasInput').files;
                if(files.length > 4) { 
                    alert("⚠️ Por favor, selecciona un máximo de 4 fotografías adicionales para la galería de abajo."); 
                    return false; 
                }
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
