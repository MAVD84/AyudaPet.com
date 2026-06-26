import os
import base64
import traceback
from flask import Flask, request, jsonify, render_template_string, redirect, url_for

app = Flask(__name__)

ADMIN_TOKEN = "ubican123" 
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

mascotas_perdidas = []

# =====================================================================
# 🛠️ ATRAPADOR DE ERRORES (Muestra el fallo real en la pantalla)
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
            <p style="color: #64748b; font-size: 0.95em; line-height: 1.5;">El formulario intentó procesarse pero algo falló en el código. Cópia todo el texto de la caja negra de abajo y pégamelo en el chat para corregirlo de inmediato:</p>
            <pre style="background: #0f172a; color: #38bdf8; padding: 16px; border-radius: 14px; overflow-x: auto; font-size: 0.85em; font-family: monospace; margin-top: 20px; white-space: pre-wrap;">{error_exacto}</pre>
        </div>
    </body>
    </html>
    """, 500
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

            nuevo_reporte = {
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
            body { font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif; background-color: var(--bg); color: var(--dark); padding-bottom: 100px; }

            .navbar {
                background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
                position: sticky; top: 0; z-index: 90; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center;
                border-bottom: 1px solid rgba(226, 232, 240, 0.8);
            }
            .navbar-brand { font-size: 1.25em; font-weight: 800; color: var(--dark); display: flex; align-items: center; gap: 8px; }
            .navbar-brand span { background: var(--primary-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

            .main-container { max-width: 1200px; margin: 40px auto; padding: 0 24px; }
            .section-intro { margin-bottom: 32px; }
            .section-intro h2 { font-size: 2em; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 6px; }
            .section-intro p { color: var(--gray-text); font-size: 0.98em; }

            .grid-feed { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 28px; }
            
            .card { 
                background: var(--card-bg); border-radius: 24px; border: 1px solid #e2e8f0; overflow: hidden; 
                display: flex; flex-direction: column; box-shadow: var(--shadow-sm);
            }

            .card-hero-image { width: 100%; height: 240px; position: relative; overflow: hidden; background: #f1f5f9; }
            .card-hero-image img { width: 100%; height: 100%; object-fit: cover; }
            .card-floating-badge { position: absolute; top: 16px; right: 16px; background: var(--danger); color: white; font-size: 0.75em; font-weight: 800; padding: 6px 14px; border-radius: 99px; }

            .card-body { padding: 24px; flex: 1; display: flex; flex-direction: column; }
            .card-title { font-size: 1.5em; font-weight: 800; color: var(--dark); margin-bottom: 12px; }

            .card-data-box { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
            .data-pill { display: flex; align-items: center; gap: 8px; font-size: 0.88em; color: var(--slate-700); background: #f1f5f9; padding: 8px 12px; border-radius: 10px; }
            .card-description { font-size: 0.95em; color: var(--slate-700); line-height: 1.6; margin-bottom: 20px; flex: 1; }

            .card-thumb-gallery { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-bottom: 20px; }
            .card-thumb-gallery img { width: 100%; height: 55px; object-fit: cover; border-radius: 10px; cursor: pointer; }

            .btn-whatsapp { background: var(--success); color: white; text-decoration: none; padding: 14px; border-radius: 16px; text-align: center; font-weight: 700; font-size: 0.95em; display: flex; align-items: center; justify-content: center; gap: 8px; }

            .app-footer-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-top: 1px solid #e2e8f0; padding: 16px 24px; z-index: 100; display: flex; justify-content: center; }
            .btn-trigger-form { background: var(--primary-gradient); color: white; border: none; padding: 16px 32px; border-radius: 16px; font-weight: 700; font-size: 1em; cursor: pointer; width: 100%; max-width: 500px; text-align: center; box-shadow: 0 6px 20px rgba(255, 107, 74, 0.25); }

            .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.5); display: none; align-items: flex-end; justify-content: center; z-index: 200; backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
            .modal-box { background: var(--card-bg); width: 100%; max-width: 550px; border-top-left-radius: 32px; border-top-right-radius: 32px; padding: 32px 24px; max-height: 85vh; overflow-y: auto; z-index: 250; position: relative; pointer-events: auto; }
            
            .modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
            .btn-close { background: #f1f5f9; border: none; font-size: 1.2em; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; }

            .form-group { margin-bottom: 20px; position: relative; z-index: 300; }
            .form-group label { display: block; font-size: 0.85em; font-weight: 700; margin-bottom: 8px; color: var(--slate-700); }
            .form-group input[type="text"], .form-group input[type="tel"], .form-group textarea { width: 100%; padding: 14px 16px; border: 1px solid #cbd5e1; border-radius: 14px; font-size: 0.95em; font-family: inherit; outline: none; background: #f8fafc; }
            
            .file-input-styled { display: block; width: 100%; padding: 14px; border: 2px dashed #cbd5e1; background: #f8fafc; border-radius: 14px; font-size: 0.9em; color: var(--slate-700); cursor: pointer; outline: none; position: relative; z-index: 350 !important; }
            .file-input-styled:active { background: #e2e8f0; border-color: #ff6b4a; }

            .btn-publish { background: var(--primary-gradient); color: white; border: none; width: 100%; padding: 16px; border-radius: 14px; font-weight: 700; font-size: 1em; cursor: pointer; margin-top: 12px; position: relative; z-index: 300; }

            .lightbox { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.95); display: none; justify-content: center; align-items: center; z-index: 400; }
            .lightbox img { max-width: 90%; max-height: 80vh; border-radius: 20px; }
            @media (max-width: 600px) { .grid-feed { grid-template-columns: 1fr; } }
        </style>
    </head>
    <body>

        <div class="navbar">
            <div class="navbar-brand">🐾 <span>Ubican ID</span> SOS</div>
        </div>

        <div class="main-container">
            <div class="section-intro">
                <h2>Mascotas Extraviadas</h2>
                <p>Ayúdanos a reportar avistamientos. La comunidad unida los lleva a casa.</p>
            </div>

            <div class="grid-feed">
                {% if not mascotas %}
                    <div style="grid-column: 1/-1; text-align: center; color: var(--gray-text); padding: 80px 0; font-style: italic; font-size: 1.05em;">
                        📍 No hay alertas activas en este momento.
                    </div>
                {% endif %}
                
                {% for mascota in mascotas %}
                {% set card_id = loop.index0 %} <!-- Evitamos loop.parent guardando el ID aquí -->
                <div class="card">
                    <div class="card-hero-image">
                        <span class="card-floating-badge">ALERTA SOS</span>
                        {% if mascota.principal %}
                            <img src="{{ mascota.principal }}" alt="Foto" id="mainPhoto-{{ card_id }}" onclick="openLightbox(this.src)">
                        {% else %}
                            <div class="card-hero-placeholder"><span>🐾</span><p>Sin foto</p></div>
                        {% endif %}
                    </div>
                    <div class="card-body">
                        <h3 class="card-title">{{ mascota.nombre }}</h3>
                        <div class="card-data-box">
                            <div class="data-pill">📍 <span><strong>Zona:</strong> {{ mascota.zona }}</span></div>
                            <div class="data-pill">📞 <span><strong>Contacto:</strong> {{ mascota.contacto }}</span></div>
                        </div>
                        <p class="card-description">{{ mascota.descripcion }}</p>
                        <div class="card-thumb-gallery">
                            {% if mascota.principal %}
                            <img src="{{ mascota.principal }}" alt="P" onclick="changeHero('{{ card_id }}', this.src)">
                            {% endif %}
                            {% for img in mascota.secundarias %}
                            <img src="{{ img }}" alt="S" onclick="changeHero('{{ card_id }}', this.src)">
                            {% endfor %}
                        </div>
                        <a href="https://wa.me/{{ mascota.contacto }}" target="_blank" class="btn-whatsapp">💬 Enviar Mensaje</a>
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
                    <h3>Registrar Reporte de Extravío</h3>
                    <button class="btn-close" onclick="toggleModal(false)">✕</button>
                </div>
                <form method="POST" action="/" enctype="multipart/form-data" id="sosForm" novalidate>
                    <div class="form-group">
                        <label>Nombre de la mascota *</label>
                        <input type="text" id="formNombre" name="nombre" placeholder="Ej. Rocko...">
                    </div>
                    <div class="form-group">
                        <label>¿Dónde se extravió? *</label>
                        <input type="text" id="formZona" name="zona" placeholder="Ej. Col. Centro">
                    </div>
                    <div class="form-group">
                        <label>Teléfono (WhatsApp) *</label>
                        <input type="tel" id="formContacto" name="contacto" placeholder="Ej. 526561234567">
                    </div>
                    <div class="form-group">
                        <label>Descripción *</label>
                        <textarea id="formDesc" name="descripcion" placeholder="Señas particulares..."></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>📸 Foto Principal (Obligatoria) *</label>
                        <input type="file" id="principalInput" name="imagen_principal" accept="image/jpeg, image/png" class="file-input-styled">
                    </div>

                    <div class="form-group">
                        <label>🐾 Fotos Adicionales (Opcional, Máx 4)</label>
                        <input type="file" id="secundariasInput" name="imagenes_secundarias" accept="image/jpeg, image/png" multiple class="file-input-styled">
                    </div>

                    <button type="submit" class="btn-publish">🚨 Publicar Alerta de Inmediato</button>
                </form>
            </div>
        </div>

        <div id="imageLightbox" class="lightbox" onclick="closeLightbox()">
            <img id="lightboxImg" src="">
        </div>

        <script>
            function toggleModal(show) {
                const modal = document.getElementById('formModal');
                if (show) { modal.style.display = 'flex'; }
                else { modal.style.display = 'none'; }
            }
            function closeModalOutside(e) { if (e.target === document.getElementById('formModal')) toggleModal(false); }
            function changeHero(cardIndex, newSrc) { document.getElementById('mainPhoto-' + cardIndex).src = newSrc; }
            function openLightbox(src) { document.getElementById('lightboxImg').src = src; document.getElementById('imageLightbox').style.display = 'flex'; }
            function closeLightbox() { document.getElementById('imageLightbox').style.display = 'none'; }
            
            document.getElementById('sosForm').onsubmit = function(e) {
                const nombre = document.getElementById('formNombre').value.trim();
                const zona = document.getElementById('formZona').value.trim();
                const contacto = document.getElementById('formContacto').value.trim();
                const desc = document.getElementById('formDesc').value.trim();
                const fotoP = document.getElementById('principalInput').files[0];
                
                if (!nombre || !zona || !contacto || !desc) {
                    e.preventDefault();
                    alert("⚠️ Por favor rellena todos los campos.");
                    return false;
                }
                if (!fotoP) {
                    e.preventDefault();
                    alert("⚠️ Debes seleccionar una 'Foto Principal'.");
                    return false;
                }
                return true;
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content, mascotas=mascotas_perdidas, es_admin=es_admin, admin_token=ADMIN_TOKEN)

if __name__ == '__main__':
    app.run(debug=True)
