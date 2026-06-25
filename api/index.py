import os
import base64
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import requests

app = Flask(__name__)

# Configuración del Bot (Telegram Webhook operativo en /webhook)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8174194177:AAHZ62p41CqtAkssj4-x1ajEQTKK60Ibs-Q")
WEB_OFICIAL = "https://sos.ubicanid.com/"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# BASE DE DATOS EN MEMORIA
# Dejamos una lista vacía para que tú mismo hagas las pruebas reales subiendo imágenes
mascotas_perdidas = []

def send_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try: requests.post(TELEGRAM_API_URL, json=payload)
    except Exception as e: print(f"Error en Telegram: {e}")

# ==================== RUTA WEB PRINCIPAL ====================
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Obtenemos la lista de archivos multimedia enviados bajo el nombre 'imagenes'
        archivos = request.files.getlist("imagenes")
        lista_imagenes_base64 = []

        # Procesamos un máximo de 5 archivos para no saturar la memoria
        for archivo in archivos[:5]:
            if archivo and archivo.filename != '':
                # Leemos los bytes del archivo y los convertimos a texto base64
                bytes_imagen = archivo.read()
                base64_codificado = base64.b64encode(bytes_imagen).decode('utf-8')
                # Creamos el formato Data URL para que el HTML sepa renderizarlo directo
                data_url = f"data:{archivo.content_type};base64,{base64_codificado}"
                lista_imagenes_base64.append(data_url)

        nuevo_reporte = {
            "nombre": request.form.get("nombre"),
            "descripcion": request.form.get("descripcion"),
            "zona": request.form.get("zona"),
            "contacto": request.form.get("contacto"),
            "imagenes": lista_imagenes_base64  # Guardamos la lista de imágenes (de 0 a 5)
        }
        
        mascotas_perdidas.insert(0, nuevo_reporte)
        return redirect(url_for('index'))

    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ubican ID SOS - Reporte con Imágenes</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
            .header { text-align: center; margin-bottom: 30px; padding: 20px 0; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
            .header h1 { margin: 0; color: #e67e22; font-size: 2.2em; }
            .header p { margin: 5px 0 0 0; color: #666; }
            .main-layout { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; max-width: 1200px; margin: 0 auto; }
            
            /* Formulario */
            .form-container { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); height: fit-content; }
            .form-container h2 { margin-top: 0; color: #2c3e50; font-size: 1.4em; border-bottom: 2px solid #f39c12; padding-bottom: 8px; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: 600; font-size: 0.9em; color: #444; }
            .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 0.95em; }
            .form-group textarea { resize: vertical; height: 80px; }
            .btn-submit { background-color: #e67e22; color: white; border: none; width: 100%; padding: 12px; border-radius: 6px; font-size: 1em; font-weight: bold; cursor: pointer; transition: background 0.2s; }
            .btn-submit:hover { background-color: #d35400; }
            
            /* Feed / Galería */
            .feed-container { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
            .feed-container h2 { margin-top: 0; color: #2c3e50; font-size: 1.4em; border-bottom: 2px solid #2ecc71; padding-bottom: 8px; }
            .grid-mascotas { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 15px; }
            .card { background: #fff; border: 1px solid #e1e8ed; border-radius: 10px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: space-between; border-left: 5px solid #e74c3c; }
            .card-title { font-size: 1.3em; font-weight: bold; color: #c0392b; margin: 0 0 10px 0; }
            .card-text { font-size: 0.95em; color: #555; margin: 5px 0; }
            .card-label { font-weight: bold; color: #333; }
            
            /* Mini galería dentro de la tarjeta */
            .card-gallery { display: grid; grid-template-columns: repeat(5, 1fr); gap: 5px; margin: 10px 0; }
            .card-gallery img { width: 100%; height: 55px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd; cursor: pointer; }
            .no-image { background: #f8f9fa; text-align: center; color: #999; font-size: 0.85em; padding: 15px; border-radius: 6px; border: 1px dashed #ccc; margin: 10px 0; }
            
            .card-footer { margin-top: 15px; padding-top: 10px; border-top: 1px solid #eee; text-align: center; }
            .btn-contactar { display: inline-block; background-color: #2ecc71; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 0.9em; }
            
            @media (max-width: 768px) { .main-layout { grid-template-columns: 1fr; } }
        </style>
    </head>
    <body>

        <div class="header">
            <h1>🐾 Ubican ID SOS</h1>
            <p>Reportes Activos con Carga Multimedia</p>
        </div>

        <div class="main-layout">
            <!-- FORMULARIO -->
            <div class="form-container">
                <h2>Generar Alerta SOS</h2>
                <!-- ENCTYPE es obligatorio para aceptar archivos -->
                <form method="POST" action="/" enctype="multipart/form-data" id="sosForm">
                    <div class="form-group">
                        <label for="nombre">Nombre de la Mascota:</label>
                        <input type="text" id="nombre" name="nombre" required>
                    </div>
                    <div class="form-group">
                        <label for="zona">¿Dónde se perdió?:</label>
                        <input type="text" id="zona" name="zona" placeholder="Colonia, calles..." required>
                    </div>
                    <div class="form-group">
                        <label for="contacto">Teléfono de Contacto (WhatsApp):</label>
                        <input type="tel" id="contacto" name="contacto" placeholder="Ej. 6561234567" required>
                    </div>
                    <div class="form-group">
                        <label for="descripcion">Detalles Importantes:</label>
                        <textarea id="descripcion" name="descripcion" required></textarea>
                    </div>
                    <div class="form-group">
                        <label for="imagenes">Fotos de la Mascota (Máximo 5):</label>
                        <!-- 'multiple' activa la selección múltiple en el móvil/PC -->
                        <input type="file" id="imagenes" name="imagenes" accept="image/*" multiple>
                    </div>
                    <button type="submit" class="btn-submit">🚨 Publicar Reporte SOS</button>
                </form>
            </div>

            <!-- FEED DE MASCOTAS -->
            <div class="feed-container">
                <h2>Alertas de Búsqueda de Mascotas</h2>
                {% if not mascotas %}
                    <p style="color: #888; text-align: center; padding: 40px 0;">No hay reportes activos en este momento. ¡Usa el formulario para crear el primero!</p>
                {% endif %}
                <div class="grid-mascotas">
                    {% for mascota in mascotas %}
                    <div class="card">
                        <div>
                            <div class="card-title">🚨 {{ mascota.nombre }}</div>
                            <p class="card-text"><span class="card-label">📍 Zona:</span> {{ mascota.zona }}</p>
                            <p class="card-text"><span class="card-label">📝 Señas:</span> {{ mascota.descripcion }}</p>
                            
                            <!-- Renderizado de imágenes -->
                            {% if mascota.imagenes %}
                                <div class="card-gallery">
                                    {% for img_data in mascota.imagenes %}
                                        <img src="{{ img_data }}" alt="Foto de {{ mascota.nombre }}" onclick="window.open(this.src)">
                                    {% endfor %}
                                </div>
                            {% else %}
                                <div class="no-image">Sin fotos adjuntas</div>
                            {% endif %}
                        </div>
                        <div class="card-footer">
                            <a href="https://wa.me/{{ mascota.contacto }}" target="_blank" class="btn-contactar">💬 Enviar Información</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Validación rápida con JS en el navegador para evitar que suban más de 5 archivos -->
        <script>
            document.getElementById('sosForm').onsubmit = function() {
                var fileInput = document.getElementById('imagenes');
                if(fileInput.files.length > 5) {
                    alert("Por seguridad, solo puedes subir un máximo de 5 imágenes por reporte.");
                    return false;
                }
                return true;
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content, mascotas=mascotas_perdidas)

# ==================== WEBHOOK DE TELEGRAM ====================
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"status": "ignored"}), 200
    return jsonify({"status": "success"}), 200
