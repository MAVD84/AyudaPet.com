import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuración del Bot (Se recomienda usar Variables de Entorno en Vercel)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8174194177:AAHZ62p41CqtAkssj4-x1ajEQTKK60Ibs-Q")
WEB_OFICIAL = "https://sos.ubicanid.com/"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_message(chat_id, text):
    """Función ligera para enviar la respuesta de vuelta al usuario"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(TELEGRAM_API_URL, json=payload)
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

@app.route('/', methods=['POST'])
def telegram_webhook():
    """Esta función recibe los mensajes que Telegram le redirige al servidor"""
    data = request.get_json()
    
    # Validamos que sea un mensaje de texto válido
    if not data or "message" not in data:
        return jsonify({"status": "ignored"}), 200

    message = data["message"]
    chat_id = message.get("chat")["id"]
    text = message.get("text", "")

    # Limpiamos el texto para evitar fallas por mayúsculas o espacios libres
    texto_minuscula = text.lower().strip()

    # Menú Principal
    if texto_minuscula in ["/start", "/menu", "/volver"]:
        welcome = (
            "🐾 *¡Bienvenido al asistente virtual de Ubican ID SOS!* 🐾\n\n"
            "Ayudamos a las familias a encontrar a sus mascotas de forma efectiva mediante anuncios geolocalizados en redes sociales.\n\n"
            "Por favor, selecciona o escribe una de las siguientes opciones:\n\n"
            "🛡️ /planes - Conoce nuestros 3 planes de búsqueda\n"
            "❓ /funcionamiento - ¿Cómo logramos encontrar a tu mascota?\n"
            "🌐 /web - Enlace directo a nuestra plataforma oficial\n"
            "💬 /whatsapp - Contactar con soporte técnico inmediato\n"
        )
        send_message(chat_id, welcome)

    # Catálogo de planes
    elif texto_minuscula in ["/planes", "/verplanes"]:
        planes = (
            "📊 *Planes y Precios de Geo-Anuncios (Ubican ID)*\n\n"
            "⚡ *1. Reacción Rápida (3 Días)*\n"
            "• *Precio:* $405 MXN\n"
            "• Anuncios en Facebook e Instagram.\n"
            "• Radio de 5 km a la redonda de donde se extravió.\n"
            "• Activación en menos de 30 min.\n\n"
            "🔥 *2. Impacto Semanal (7 Días)*\n"
            "• *Precio:* $860 MXN\n"
            "• Radio ampliado a 10 km a la redonda.\n"
            "• Incluye asesoría especializada contra extorsiones.\n\n"
            "🏆 *3. Cobertura Total (11 Días)*\n"
            "• *Precio:* $1,305 MXN\n"
            "• Radio máximo de 15 km a la redonda.\n"
            "• Formato de alta visibilidad en Video / Reel.\n\n"
            f"🔗 Contrata directamente aquí: {WEB_OFICIAL}"
        )
        send_message(chat_id, planes)

    # Explicación operativa
    elif texto_minuscula in ["/funcionamiento", "/comofunciona"]:
        info = (
            "🧐 *¿Cómo funciona Ubican ID SOS?*\n\n"
            "1️⃣ *Geolocalización:* Generamos alertas dirigidas específicamente al sector exacto donde se perdió tu mascota.\n\n"
            "2️⃣ *Redes Sociales:* Los anuncios aparecen directamente en los muros y secciones de Facebook, Instagram y WhatsApp del perímetro seleccionado.\n\n"
            "3️⃣ *Inmediatez:* Activamos la campaña en menos de 30 minutos tras recibir el reporte."
        )
        send_message(chat_id, info)

    # Redirección Web
    elif texto_minuscula == "/web":
        send_message(chat_id, f"🌐 *Plataforma Oficial de Ubican ID*\n\nAccede para registrar una mascota o realizar un reporte:\n{WEB_OFICIAL}")

    # Enlace WhatsApp
    elif texto_minuscula == "/whatsapp":
        send_message(chat_id, "💬 *Atención Personalizada por WhatsApp*\n\n¿Tienes dudas? Conversa con un asesor de inmediato:\nhttps://wa.me/message/UBICANID_LINK_WHATSAPP")

    # Mensaje de error / Guía
    else:
        send_message(chat_id, "❌ *Opción no reconocida.*\n\nPor favor, escribe o presiona /menu para ver las opciones disponibles.")

    return jsonify({"status": "success"}), 200

@app.route('/', methods=['GET'])
def index():
    """Ruta del navegador por si entras directo al link de Vercel"""
    return "Servidor del Bot de Ubican ID activo correctamente.", 200