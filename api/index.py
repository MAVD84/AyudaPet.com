import os
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import requests

app = Flask(__name__)

# Configuración del Bot (Se queda igual para no afectar tu Telegram)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8174194177:AAHZ62p41CqtAkssj4-x1ajEQTKK60Ibs-Q")
WEB_OFICIAL = "https://sos.ubicanid.com/"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# BASE DE DATOS EN MEMORIA (Lista de Python para guardar los reportes temporalmente)
# Inicializamos con dos reportes de ejemplo para que la página no se vea vacía
mascotas_perdidas = [
    {
        "nombre": "Rocky",
        "descripcion": "Golden Retriever juguetón, llevaba collar azul sin placa.",
        "zona": "Colonia Centro, cerca del parque principal",
        "contacto": "55-1234-5678"
    },
    {
        "nombre": "Luna",
        "descripcion": "Gatita siamesa de ojos azules, muy tímida y asustadiza.",
        "zona": "Fraccionamiento Las Américas, Calle 4",
        "contacto": "656-987-6543"
    }
]

def send_message(chat_id, text):
    """Función para el bot de Telegram"""
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try: requests.post(TELEGRAM_API_URL, json=payload)
    except Exception as e: print(f"Error en Telegram: {e}")

# ==================== RUTA WEB PRINCIPAL (MOSTRAR Y REPORTAR) ====================
@app.route('/', methods=['GET', 'POST'])
def index():
    # Si el usuario llena el formulario y le da al botón "Publicar Reporte"
    if request.method == 'POST':
        nuevo_reporte = {
            "nombre": request.form.get("nombre"),
            "descripcion": request.form.get("descripcion"),
            "zona": request.form.get("zona"),
            "contacto": request.form.get("contacto")
        }
        # Lo añadimos al principio de nuestra lista para que aparezca primero
        mascotas_perdidas.insert(0, nuevo_reporte)
        
        # Opcional: Alértate a ti mismo en Telegram en tiempo real cuando alguien reporte en la web
        # send_message("TU_CHAT_ID", f"🚨 *Nuevo reporte web:* {nuevo_reporte['nombre']} se perdió en {nuevo_reporte['zona']}.")
        
        return redirect(url_for('index'))

    # Diseño HTML y CSS integrado directamente (Estilo Ubican ID SOS)
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ubican ID SOS - Reporte de Mascotas</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
            .header { text-align: center; margin-bottom: 30px; padding: 20px 0; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
            .header h1 { margin: 0; color: #e67e22; font-size: 2.2em; }
            .header p { margin: 5px 0 0 0; color: #666; }
            .main-layout { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; max-width: 1200px; margin: 0 auto; }
            
            /* Estilos del Formulario */
            .form-container { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); height: fit-content; }
            .form-container h2 { margin-top: 0; color: #2c3e50; font-size: 1.4em; border-bottom: 2px solid #f39c12; padding-bottom: 8px; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: 600; font-size: 0.9em; color: #444; }
            .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 0.95em; }
            .form-group textarea { resize: vertical; height: 80px; }
            .btn-submit { background-color: #e67e22; color: white; border: none; width: 100%; padding: 12px; border-radius: 6px; font-size: 1em; font-weight: bold; cursor: pointer; transition: background 0.2s; }
            .btn-submit:hover { background-color: #d35400; }
            
            /* Estilos de la Galería de Reportes */
            .feed-container { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
            .feed-container h2 { margin-top: 0; color: #2c3e50; font-size: 1.4em; border-bottom: 2px solid #2ecc71; padding-bottom: 8px; }
            .grid-mascotas { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-top: 15px; }
            .card { background: #fff; border: 1px solid #e1e8ed; border-radius: 10px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: space-between; border-left: 5px solid #e74c3c; }
            .card-title { font-size: 1.3em; font-weight: bold; color: #c0392b; margin: 0 0 10px 0; display: flex; align-items: center; gap: 5px; }
            .card-text { font-size: 0.95em; color: #555; margin: 5px 0; }
            .card-label { font-weight: bold; color: #333; }
            .card-footer { margin-top: 15px; padding-top: 10px; border-top: 1fr solid #eee; text-align: center; }
            .btn-contactar { display: inline-block; background-color: #2ecc71; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 0.9em; }
            
            /* Responsivo para celulares */
            @media (max-width: 768px) {
                .main-layout { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>

        <div class="header">
            <h1>🐾 Ubican ID SOS</h1>
            <p>Panel en Tiempo Real - Reportes de Mascotas Extraviadas</p>
        </div>

        <div class="main-layout">
            <!-- COLUMNA 1: FORMULARIO -->
            <div class="form-container">
                <h2>Generar Alerta SOS</h2>
                <form method="POST" action="/">
                    <div class="form-group">
                        <label for="nombre">Nombre de la Mascota:</label>
                        <input type="text" id="nombre" name="nombre" placeholder="Ej. Max, Hunky" required>
                    </div>
                    <div class="form-group">
                        <label for="zona">¿Dónde se perdió? (Zona/Colonia):</label>
                        <input type="text" id="zona" name="zona" placeholder="Ej. Col. Juárez, Cruce de calles X e Y" required>
                    </div>
                    <div class="form-group">
                        <label for="contacto">Teléfono de Contacto:</label>
                        <input type="tel" id="contacto" name="contacto" placeholder="Ej. 6561234567" required>
                    </div>
                    <div class="form-group">
                        <label for="descripcion">Descripción o Señas Particulares:</label>
                        <textarea id="descripcion" name="descripcion" placeholder="Ej. Color café, talla mediana, muy asustadizo..." required></textarea>
                    </div>
                    <button type="submit" class="btn-submit">🚨 Publicar Reporte SOS</button>
                </form>
            </div>

            <!-- COLUMNA 2: GALERÍA DE REPORTES -->
            <div class="feed-container">
                <h2>Mascotas Buscadas en la Zona</h2>
                <div class="grid-mascotas">
                    {% for mascota in mascotas %}
                    <div class="card">
                        <div>
                            <div class="card-title">🚨 {{ mascota.nombre }}</div>
                            <p class="card-text"><span class="card-label">📍 Zona:</span> {{ mascota.zona }}</p>
                            <p class="card-text"><span class="card-label">📝 Detalles:</span> {{ mascota.descripcion }}</p>
                        </div>
                        <div class="card-footer">
                            <a href="https://wa.me/{{ mascota.contacto }}" target="_blank" class="btn-contactar">💬 Reportar Avistamiento</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

    </body>
    </html>
    """
    return render_template_string(html_content, mascotas=mascotas_perdidas)

# ==================== WEBHOOK DE TELEGRAM ====================
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Mantiene tu bot de Telegram funcionando en la ruta /webhook"""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"status": "ignored"}), 200

    message = data["message"]
    chat_id = message.get("chat")["id"]
    text = message.get("text", "")
    texto_minuscula = text.lower().strip()

    if texto_minuscula in ["/start", "/menu", "/volver"]:
        welcome = "🐾 *¡Bienvenido a Ubican ID SOS!* 🐾\n\nUsa /planes para ver coberturas o visita nuestra web para ver la lista de reportes en tiempo real."
        send_message(chat_id, welcome)
    elif texto_minuscula in ["/planes", "/verplanes"]:
        planes = "📊 *Planes Ubican ID*\n• Reacción Rápida (5km): $405 MXN\n• Impacto Semanal (10km): $860 MXN\n• Cobertura Total (15km): $1,305 MXN"
        send_message(chat_id, planes)
    else:
        send_message(chat_id, "❌ Escribe /menu para ver opciones.")

    return jsonify({"status": "success"}), 200
