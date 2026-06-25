import os
import base64
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import requests

app = Flask(__name__)

# Configuración del Bot (Telegram Webhook operativo en /webhook)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8174194177:AAHZ62p41CqtAkssj4-x1ajEQTKK60Ibs-Q")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# BASE DE DATOS EN MEMORIA (Iniciamos con un reporte completo de prueba)
mascotas_perdidas = [
    {
        "nombre": "Gohan",
        "descripcion": "Pug color arena con collar rojo, cicatriz pequeña en la oreja izquierda. Muy dócil.",
        "zona": "Colonia Praderas, cerca de la avenida de las Torres",
        "contacto": "6561234567",
        "imagenes": [] # Puedes subir reales desde la app
    }
]

# ==================== RUTA WEB PRINCIPAL ====================
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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Ubican ID SOS</title>
        <style>
            /* Reset y Estilos Base de App Móvil */
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                background-color: #f1f3f5; 
                margin: 0; 
                padding: 0; 
                display: flex; 
                justify-content: center;
            }
            
            /* Contenedor tipo pantalla de celular */
            .app-container {
                width: 100%;
                max-width: 500px;
                background-color: #ffffff;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                position: relative;
                box-shadow: 0 0 20px rgba(0,0,0,0.05);
            }

            /* Header Fijo Estilo App */
            .app-header {
                position: sticky;
                top: 0;
                background: linear-gradient(135deg, #e67e22, #f39c12);
                color: white;
                padding: 16px;
                text-align: center;
                z-index: 100;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .app-header h1 { margin: 0; font-size: 1.35em; font-weight: 700; letter-spacing: 0.5px; }
            .app-header p { margin: 4px 0 0 0; font-size: 0.85em; opacity: 0.9; }

            /* Feed de reportes */
            .app-feed { padding: 16px; flex: 1; padding-bottom: 90px; }
            .no-reports { text-align: center; color: #7f8c8d; margin-top: 40px; font-size: 0.95em; }

            /* Tarjetas de Reporte (Feed Cards) */
            .card {
                background: #fff;
                border-radius: 16px;
                padding: 16px;
                margin-bottom: 16px;
                border: 1px solid #edf2f7;
                box-shadow: 0 4px 12px rgba(0,0,0,0.03);
                border-top: 4px solid #e74c3c;
            }
            .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
            .card-title { font-size: 1.2em; font-weight: 700; color: #c0392b; margin: 0; }
            .status-badge { background: #fadbd8; color: #e74c3c; padding: 4px 10px; border-radius: 20px; font-size: 0.75em; font-weight: 700; }
            
            .card-info { font-size: 0.92em; color: #4a5568; line-height: 1.5; margin-bottom: 8px; }
            .card-info strong { color: #2d3748; display: inline-block; width: 75px; }
            .card-desc { background: #f8f9fa; padding: 10px 12px; border-radius: 8px; font-style: italic; color: #4a5568; border-left: 3px solid #cbd5e0; margin: 12px 0; }

            /* Carrusel / Galería Táctil dentro de la Tarjeta */
            .card-media { display: flex; gap: 8px; overflow-x: auto; margin: 12px 0; padding-bottom: 4px; scroll-snap-type: x mandatory; }
            .card-media::-webkit-scrollbar { height: 4px; }
            .card-media::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 4px; }
            .card-media img { 
                width: 100px; 
                height: 100px; 
                object-fit: cover; 
                border-radius: 10px; 
                border: 1px solid #e2e8f0; 
                cursor: pointer;
                scroll-snap-align: start;
                transition: transform 0.2s;
            }
            .card-media img:active { transform: scale(0.95); }

            /* Botón de WhatsApp */
            .btn-action {
                display: flex;
                align-items: center;
                justify-content: center;
                background-color: #2ecc71;
                color: white;
                text-decoration: none;
                padding: 10px;
                border-radius: 10px;
                font-weight: 700;
                font-size: 0.9em;
                margin-top: 12px;
                text-align: center;
                transition: background 0.2s;
            }
            .btn-action:hover { background-color: #27ae60; }

            /* Botón Flotante (FAB) */
            .fab {
                position: fixed;
                bottom: 24px;
                right: calc(50% - 210px); /* Centrado relativo al contenedor max-width de 500px */
                width: 56px;
                height: 56px;
                background: linear-gradient(135deg, #e67e22, #d35400);
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                border: none;
                cursor: pointer;
                box-shadow: 0 6px 16px rgba(230, 126, 34, 0.4);
                z-index: 200;
                transition: transform 0.2s, background 0.2s;
            }
            @media (max-width: 500px) { .fab { right: 24px; } }
            .fab:active { transform: scale(0.9) rotate(90deg); }

            /* Modales (Estructuras de Capa Flotante superpuestas) */
            .overlay {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0, 0, 0, 0.5); display: none; justify-content: center; align-items: flex-end;
                z-index: 300; opacity: 0; transition: opacity 0.3s ease;
            }
            .overlay.active { display: flex; opacity: 1; }

            /* Formulario emergente desde abajo (Estilo iOS/Android Sheets) */
            .modal-sheet {
                width: 100%; max-width: 500px; background: white;
                border-top-left-radius: 24px; border-top-right-radius: 24px;
                padding: 24px; max-height: 85vh; overflow-y: auto;
                transform: translateY(100%); transition: transform 0.3s ease;
            }
            .overlay.active .modal-sheet { transform: translateY(0); }
            
            .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .modal-header h2 { margin: 0; font-size: 1.3em; color: #2c3e50; }
            .close-btn { background: #f1f3f5; border: none; font-size: 1.2em; width: 32px; height: 32px; border-radius: 50%; cursor: pointer; color: #7f8c8d; }

            /* Formulario Inputs */
            .form-group { margin-bottom: 16px; }
            .form-group label { display: block; font-size: 0.85em; font-weight: 700; color: #4a5568; margin-bottom: 6px; }
            .form-group input, .form-group textarea {
                width: 100%; padding: 12px; border: 1px solid #cbd5e0; border-radius: 10px;
                font-size: 0.95em; font-family: inherit; outline: none; background: #f8f9fa;
            }
            .form-group input:focus, .form-group textarea:focus { border-color: #e67e22; background: #fff; }
            .btn-send { background: #e67e22; color: white; border: none; width: 100%; padding: 14px; border-radius: 10px; font-weight: bold; font-size: 1em; cursor: pointer; margin-top: 10px; }

            /* Visor de Imágenes Pantalla Completa (Lightbox) */
            .lightbox {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.9); display: none; justify-content: center; align-items: center;
                z-index: 400; padding: 20px;
            }
            .lightbox img { max-width: 100%; max-height: 80vh; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
            .lightbox-close { position: absolute; top: 24px; right: 24px; color: white; font-size: 30px; cursor: pointer; font-weight: bold; }
        </style>
    </head>
    <body>

        <div class="app-container">
            <!-- HEADER APP -->
            <div class="app-header">
                <h1>Ubican ID SOS</h1>
                <p>Reportes Recientes de la Comunidad</p>
            </div>

            <!-- FEED DE REPORTES -->
            <div class="app-feed">
                {% if not mascotas %}
                    <p class="no-reports">No hay reportes de extravíos vigentes.<br>Usa el botón de abajo para reportar.</p>
                {% endif %}
                
                {% for mascota in mascotas %}
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🚨 {{ mascota.nombre }}</h3>
                        <span class="status-badge">BUSCADO</span>
                    </div>
                    
                    <div class="card-info"><strong>📍 Zona:</strong>{{ mascota.zona }}</div>
                    <div class="card-info"><strong>📞 Teléfono:</strong>{{ mascota.contacto }}</div>
                    
                    <div class="card-desc">
                        "{{ mascota.descripcion }}"
                    </div>

                    <!-- Muestra las imágenes en una fila horizontal deslizable si existen -->
                    {% if mascota.imagenes %}
                    <div class="card-media">
                        {% for img in mascota.imagenes %}
                        <img src="{{ img }}" alt="Foto" onclick="openLightbox(this.src)">
                        {% endfor %}
                    </div>
                    {% endif %}

                    <a href="https://wa.me/{{ mascota.contacto }}?text=Hola,%20vi%20tu%20reporte%20de%20{{ mascota.nombre }}%20en%20UbicanID" target="_blank" class="btn-action">
                        💬 Enviar Mensaje / Avistamiento
                    </a>
                </div>
                {% endfor %}
            </div>

            <!-- BOTÓN FLOTANTE (FAB) -->
            <button class="fab" onclick="openFormModal()">➕</button>
        </div>

        <!-- MODAL DEL FORMULARIO (Desliza desde abajo) -->
        <div id="formModal" class="overlay" onclick="closeFormModal(event)">
            <div class="modal-sheet" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2>🚨 Publicar Reporte SOS</h2>
                    <button class="close-btn" onclick="closeFormModal(null)">✕</button>
                </div>
                <form method="POST" action="/" enctype="multipart/form-data" id="sosForm">
                    <div class="form-group">
                        <label>Nombre de la mascota:</label>
                        <input type="text" name="nombre" placeholder="Ej. Firulais, Kira" required>
                    </div>
                    <div class="form-group">
                        <label>¿Dónde se extravió? (Zona / Colonia):</label>
                        <input type="text" name="zona" placeholder="Ej. Cruce de Av. Juárez y Calle 5" required>
                    </div>
                    <div class="form-group">
                        <label>Tu Teléfono de Contacto:</label>
                        <input type="tel" name="contacto" placeholder="Ej. 6560000000" required>
                    </div>
                    <div class="form-group">
                        <label>Señas particulares o descripción:</label>
                        <textarea name="descripcion" placeholder="Color de pelaje, si traía collar, tamaño, nivel de timidez..." required></textarea>
                    </div>
                    <div class="form-group">
                        <label>Fotos (Selecciona hasta 5 imágenes):</label>
                        <input type="file" id="imagenesInput" name="imagenes" accept="image/*" multiple>
                    </div>
                    <button type="submit" class="btn-send">Publicar en el Feed</button>
                </form>
            </div>
        </div>

        <!-- MODAL DE IMAGEN AMPLIADA (Lightbox) -->
        <div id="imageLightbox" class="lightbox" onclick="closeLightbox()">
            <span class="lightbox-close">&times;</span>
            <img id="lightboxImg" src="" alt="Imagen ampliada">
        </div>

        <!-- COMPORTAMIENTO INTERACTIVO (JavaScript Móvil) -->
        <script>
            // Funciones del Formulario Emergente
            function openFormModal() {
                const modal = document.getElementById('formModal');
                modal.style.display = 'flex';
                setTimeout(() => modal.classList.add('active'), 10);
            }

            function closeFormModal(event) {
                if (event && event.target !== document.getElementById('formModal')) return;
                const modal = document.getElementById('formModal');
                modal.classList.remove('active');
                setTimeout(() => modal.style.display = 'none', 300);
            }

            // Funciones del Visor de Fotos Ampliadas (Lightbox)
            function openLightbox(src) {
                const lightbox = document.getElementById('imageLightbox');
                const img = document.getElementById('lightboxImg');
                img.src = src;
                lightbox.style.display = 'flex';
            }

            function closeLightbox() {
                document.getElementById('imageLightbox').style.display = 'none';
            }

            // Validación de cantidad de fotos antes de mandar datos
            document.getElementById('sosForm').onsubmit = function() {
                const files = document.getElementById('imagenesInput').files;
                if(files.length > 5) {
                    alert("⚠️ Lo sentimos, el límite son 5 imágenes por mascota.");
                    return false;
                }
                return true;
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content, mascotas=mascotas_perdidas)

# Webhook pasivo para Telegram
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    return jsonify({"status": "success"}), 200
