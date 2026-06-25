import os
import base64
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import requests

app = Flask(__name__)

# Configuración del Bot (Telegram Webhook operativo en /webhook)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8174194177:AAHZ62p41CqtAkssj4-x1ajEQTKK60Ibs-Q")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# BASE DE DATOS EN MEMORIA (Iniciamos con reportes de prueba estéticos)
mascotas_perdidas = [
    {
        "nombre": "Gohan",
        "descripcion": "Pug color arena con collar rojo. Tiene una pequeña cicatriz en la oreja izquierda. Es muy asustadizo pero no muerde.",
        "zona": "Colonia Praderas, cerca de Av. de las Torres",
        "contacto": "6561234567",
        "imagenes": []
    },
    {
        "nombre": "Kira",
        "descripcion": "Husky Siberiana de ojos heterocromáticos (uno azul y uno café). Trae placa de Ubican ID pero se borró el teléfono.",
        "zona": "Cerca del Parque Central",
        "contacto": "6569876543",
        "imagenes": []
    }
]

@app.route('/', methods=['GET', 'POST'])
def index():
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
            
            body { 
                font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background-color: var(--bg);
                color: var(--dark);
                padding-bottom: 60px;
            }

            /* Navbar Superior */
            .navbar {
                background: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                position: sticky; top: 0; z-index: 90;
                padding: 16px 24px;
                display: flex; justify-content: space-between; align-items: center;
                border-bottom: 1px solid rgba(226, 232, 240, 0.8);
            }
            .navbar-brand { font-size: 1.25em; font-weight: 800; color: var(--dark); display: flex; align-items: center; gap: 8px; }
            .navbar-brand span { background: var(--primary-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

            /* Contenedor Principal Dashboard */
            .main-container { max-width: 1200px; margin: 40px auto; padding: 0 24px; }
            
            .section-intro { margin-bottom: 32px; }
            .section-intro h2 { font-size: 1.75em; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 6px; }
            .section-intro p { color: var(--gray-text); font-size: 0.95em; }

            /* Grid Dinámico de Tarjetas */
            .grid-feed {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
                gap: 24px;
            }
            
            /* Tarjetas de Reporte Premium */
            .card {
                background: var(--card-bg);
                border-radius: 20px;
                border: 1px solid #e2e8f0;
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02), 0 2px 4px -1px rgba(0,0,0,0.01);
                overflow: hidden;
                display: flex;
                flex-direction: column;
                transition: transform 0.25s ease, box-shadow 0.25s ease;
            }
            .card:hover {
                transform: translateY(-4px);
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.02);
            }

            .card-body { padding: 24px; flex: 1; display: flex; flex-direction: column; }
            
            .card-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
            .card-badge { background: #fee2e2; color: var(--danger); font-size: 0.75em; font-weight: 700; padding: 4px 12px; border-radius: 99px; letter-spacing: 0.5px; }
            .card-title { font-size: 1.4em; font-weight: 800; color: var(--dark); }

            .info-row { display: flex; font-size: 0.9em; margin-bottom: 8px; line-height: 1.4; }
            .info-row strong { color: var(--dark); width: 85px; flex-shrink: 0; font-weight: 600; }
            .info-row span { color: var(--gray-text); }
            
            .card-description { 
                background: #f8fafc; padding: 14px; border-radius: 12px; 
                font-size: 0.92em; color: #475569; margin: 16px 0; 
                line-height: 1.5; border-left: 4px solid var(--primary);
                flex: 1;
            }

            /* Carrusel de Fotos Deslizable Moderno */
            .card-gallery { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 8px; scroll-snap-type: x mandatory; }
            .card-gallery::-webkit-scrollbar { height: 5px; }
            .card-gallery::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
            .card-gallery img {
                width: 75px; height: 75px; object-fit: cover; border-radius: 10px;
                cursor: pointer; border: 1px solid #f1f5f9; transition: opacity 0.2s;
                scroll-snap-align: start;
            }
            .card-gallery img:hover { opacity: 0.85; }
            .no-photos { font-size: 0.8em; color: var(--gray-text); font-style: italic; margin-bottom: 16px; text-align: center; background: #f1f5f9; padding: 10px; border-radius: 10px; }

            /* Botón de Acción Principal */
            .btn-whatsapp {
                background: #10b981; color: white; text-decoration: none;
                padding: 12px; border-radius: 12px; text-align: center;
                font-weight: 700; font-size: 0.9em; display: flex; align-items: center; justify-content: center; gap: 6px;
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2); transition: background 0.2s, transform 0.2s;
            }
            .btn-whatsapp:active { transform: scale(0.98); }

            /* Botón Flotante Moderno (FAB) */
            .fab {
                position: fixed; bottom: 32px; right: 32px;
                background: var(--primary-gradient); color: white;
                border: none; width: 60px; height: 60px; border-radius: 50%;
                font-size: 24px; cursor: pointer; z-index: 100;
                display: flex; align-items: center; justify-content: center;
                box-shadow: 0 10px 25px -5px rgba(255, 107, 74, 0.4);
                transition: transform 0.2s ease;
            }
            .fab:hover { transform: scale(1.08); }
            .fab:active { transform: scale(0.95); }

            /* Modales con Efecto Blur Avanzado */
            .modal-overlay {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(15, 23, 42, 0.4); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
                display: none; justify-content: center; align-items: center; z-index: 200;
                opacity: 0; transition: opacity 0.3s ease; padding: 16px;
            }
            .modal-overlay.active { display: flex; opacity: 1; }

            .modal-box {
                background: var(--card-bg); width: 100%; max-width: 460px;
                border-radius: 24px; padding: 32px; max-height: 90vh; overflow-y: auto;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                transform: scale(0.9); transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            }
            .modal-overlay.active .modal-box { transform: scale(1); }

            .modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
            .modal-head h3 { font-size: 1.3em; font-weight: 800; }
            .btn-close { background: #f1f5f9; border: none; font-size: 1em; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; color: var(--gray-text); display: flex; align-items: center; justify-content: center; }

            /* Estilos del Formulario */
            .form-group { margin-bottom: 18px; }
            .form-group label { display: block; font-size: 0.85em; font-weight: 700; color: var(--dark); margin-bottom: 6px; }
            .form-group input, .form-group textarea {
                width: 100%; padding: 12px 16px; border: 1px solid #cbd5e1; border-radius: 12px;
                font-size: 0.95em; font-family: inherit; outline: none; background: #fff; transition: border-color 0.2s;
            }
            .form-group input:focus, .form-group textarea:focus { border-color: #ff6b4a; box-shadow: 0 0 0 3px rgba(255,107,74,0.1); }
            .form-group textarea { height: 90px; resize: none; }
            
            .btn-publish {
                background: var(--primary-gradient); color: white; border: none; width: 100%;
                padding: 14px; border-radius: 12px; font-weight: 700; font-size: 1em; cursor: pointer;
                margin-top: 12px; box-shadow: 0 4px 12px rgba(255, 107, 74, 0.2);
            }

            /* Lightbox (Visor de Fotos) */
            .lightbox {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(10px);
                display: none; justify-content: center; align-items: center; z-index: 300;
            }
            .lightbox img { max-width: 90%; max-height: 80vh; border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
            .lightbox-close { position: absolute; top: 24px; right: 24px; color: white; font-size: 32px; cursor: pointer; }

            @media (max-width: 600px) {
                .main-container { margin: 20px auto; }
                .grid-feed { grid-template-columns: 1fr; gap: 16px; }
                .modal-box { padding: 24px; }
                .fab { bottom: 20px; right: 20px; width: 54px; height: 54px; }
            }
        </style>
    </head>
    <body>

        <!-- NAVBAR -->
        <div class="navbar">
            <div class="navbar-brand">🐾 <span>Ubican ID</span> SOS</div>
        </div>

        <!-- CONTENIDO PRINCIPAL -->
        <div class="main-container">
            <div class="section-intro">
                <h2>Mascotas Extraviadas</h2>
                <p>Red comunitaria en tiempo real para reportes y avistamientos.</p>
            </div>

            <!-- FEED DE REPORTES -->
            <div class="grid-feed">
                {% if not mascotas %}
                    <p style="grid-column: 1/-1; text-align: center; color: var(--gray-text); padding: 60px 0;">No hay alertas SOS activas en tu zona.</p>
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

                        <!-- Carrusel de imágenes -->
                        {% if mascota.imagenes %}
                        <div class="card-gallery">
                            {% for img in mascota.imagenes %}
                            <img src="{{ img }}" alt="Foto de {{ mascota.nombre }}" onclick="openLightbox(this.src)">
                            {% endfor %}
                        </div>
                        {% else %}
                        <div class="no-photos">Sin fotografías adjuntas</div>
                        {% endif %}

                        <a href="https://wa.me/{{ mascota.contacto }}?text=Hola,%20vi%20tu%20reporte%20de%20{{ mascota.nombre }}%20en%20UbicanID" target="_blank" class="btn-whatsapp">
                            💬 Informar Avistamiento
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- BOTÓN FLOTANTE (FAB) -->
        <button class="fab" onclick="toggleModal(true)">＋</button>

        <!-- MODAL FORMULARIO -->
        <div id="formModal" class="modal-overlay" onclick="closeModalOutside(event)">
            <div class="modal-box">
                <div class="modal-head">
                    <h3>Crear Reporte de Extravío</h3>
                    <button class="btn-close" onclick="toggleModal(false)">✕</button>
                </div>
                <form method="POST" action="/" enctype="multipart/form-data" id="sosForm">
                    <div class="form-group">
                        <label>Nombre de la mascota</label>
                        <input type="text" name="nombre" placeholder="Ej. Rocko" required>
                    </div>
                    <div class="form-group">
                        <label>¿Dónde se vio por última vez? (Zona/Colonia)</label>
                        <input type="text" name="zona" placeholder="Ej. Col. Juárez, calle Poniente" required>
                    </div>
                    <div class="form-group">
                        <label>Teléfono de contacto (WhatsApp)</label>
                        <input type="tel" name="contacto" placeholder="Ej. 6560000000" required>
                    </div>
                    <div class="form-group">
                        <label>Descripción / Señas particulares</label>
                        <textarea name="descripcion" placeholder="Tamaño, señas, si lleva collar, temperamento..." required></textarea>
                    </div>
                    <div class="form-group">
                        <label>Fotografías (Máximo 5)</label>
                        <input type="file" id="filesInput" name="imagenes" accept="image/*" multiple style="padding: 8px 0;">
                    </div>
                    <button type="submit" class="btn-publish">🚨 Publicar Alerta SOS</button>
                </form>
            </div>
        </div>

        <!-- LIGHTBOX -->
        <div id="imageLightbox" class="lightbox" onclick="closeLightbox()">
            <span class="lightbox-close">&times;</span>
            <img id="lightboxImg" src="" alt="Ampliada">
        </div>

        <!-- CONTROLADORES INTERACTIVOS -->
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

            function closeModalOutside(e) {
                if (e.target === document.getElementById('formModal')) toggleModal(false);
            }

            function openLightbox(src) {
                document.getElementById('lightboxImg').src = src;
                document.getElementById('imageLightbox').style.display = 'flex';
            }

            function closeLightbox() {
                document.getElementById('imageLightbox').style.display = 'none';
            }

            document.getElementById('sosForm').onsubmit = function() {
                const files = document.getElementById('filesInput').files;
                if(files.length > 5) {
                    alert("⚠️ Por favor, selecciona un máximo de 5 fotografías.");
                    return false;
                }
                return true;
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content, mascotas=mascotas_perdidas)

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    return jsonify({"status": "success"}), 200
