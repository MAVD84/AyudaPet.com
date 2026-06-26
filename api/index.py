import os
import time
import base64
import traceback
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

mascotas_perdidas = []

@app.errorhandler(500)
def handle_internal_server_error(e):
    return "Error en el servidor: " + traceback.format_exc(), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Mapeo de todos los campos solicitados
        nueva_mascota = {
            "id": str(int(time.time() * 1000)),
            "fecha": request.form.get("fecha"),
            "nombre": request.form.get("nombre"),
            "edad": request.form.get("edad"),
            "raza": request.form.get("raza"),
            "genero": request.form.get("genero"),
            "color": request.form.get("color"),
            "collar": request.form.get("collar"),
            "docil": request.form.get("docil"),
            "direccion": request.form.get("direccion"),
            "ciudad": request.form.get("ciudad"),
            "estado": request.form.get("estado"),
            "cp": request.form.get("cp"),
            "calles": request.form.get("calles"),
            "dueno": request.form.get("dueno"),
            "whatsapp": request.form.get("whatsapp"),
            "recompensa": request.form.get("recompensa")
        }
        
        foto = request.files.get("imagen")
        if foto and foto.filename != '':
            bytes_p = foto.read()
            b64_p = base64.b64encode(bytes_p).decode('utf-8')
            nueva_mascota["foto"] = f"data:{foto.content_type};base64,{b64_p}"
            
        mascotas_perdidas.insert(0, nueva_mascota)
        return redirect(url_for('index'))

    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reportar Mascota</title>
    <style>
        body { font-family: system-ui, sans-serif; padding: 20px; line-height: 1.5; max-width: 500px; margin: auto; background: #f9f9f9; }
        .section { background: white; padding: 20px; margin-bottom: 20px; border-radius: 12px; border: 1px solid #eee; }
        label { display: block; font-weight: 600; font-size: 0.9em; margin-top: 10px; color: #444; }
        input, select { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
        button { background: #ff6b4a; color: white; border: none; padding: 16px; width: 100%; font-weight: bold; cursor: pointer; border-radius: 8px; font-size: 1em; }
    </style>
    </head>
    <body>
        <h2>Reportar Mascota Perdida</h2>
        <form method="POST" enctype="multipart/form-data">
            <div class="section">
                <label>01. FECHA DE EXTRAVÍO:</label>
                <input type="date" name="fecha" required>
            </div>

            <div class="section">
                <h3>INFORMACIÓN DE LA MASCOTA</h3>
                <label>Nombre:</label><input type="text" name="nombre">
                <label>Edad:</label><input type="text" name="edad">
                <label>Raza:</label><input type="text" name="raza">
                <label>Género:</label><select name="genero"><option>Macho</option><option>Hembra</option></select>
                <label>Color:</label><input type="text" name="color">
                <label>¿Collar?:</label><select name="collar"><option>Si</option><option>No</option></select>
                <label>¿Dócil?:</label><select name="docil"><option>Si</option><option>No</option></select>
            </div>

            <div class="section">
                <h3>UBICACIÓN DE EXTRAVÍO</h3>
                <label>Dirección:</label><input type="text" name="direccion">
                <label>Ciudad:</label><input type="text" name="ciudad">
                <label>Estado:</label><input type="text" name="estado">
                <label>Codigo Postal:</label><input type="text" name="cp">
                <label>Entre calles:</label><input type="text" name="calles">
            </div>

            <div class="section">
                <h3>CONTACTO / DUEÑO</h3>
                <label>Dueño/Contacto:</label><input type="text" name="dueno">
                <label>WhatsApp (Lada +52/+1):</label><input type="text" name="whatsapp" placeholder="+52...">
                <label>Recompensa:</label><select name="recompensa"><option>No</option><option>Si</option></select>
                <label>Foto:</label><input type="file" name="imagen" accept="image/*">
            </div>
            
            <button type="submit">PUBLICAR ALERTA</button>
        </form>

        <hr style="margin: 40px 0;">
        <h2>Reportes Activos</h2>
        {% for m in mascotas %}
            <div style="padding: 10px 0; border-bottom: 1px solid #ddd;">
                <a href="/mascota/{{ m.id }}" style="text-decoration:none; color:#333;">
                    <strong>{{ m.nombre }}</strong> <small>({{ m.ciudad }})</small>
                </a>
            </div>
        {% endfor %}
    </body>
    </html>
    """
    return render_template_string(html, mascotas=mascotas_perdidas)

@app.route('/mascota/<id>')
def detalle_mascota(id):
    m = next((item for item in mascotas_perdidas if item["id"] == id), None)
    if not m: return "No encontrado"
    
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head><title>{{ m.nombre }}</title>
    <style>
        body { font-family: system-ui, sans-serif; padding: 20px; line-height: 1.6; max-width: 600px; margin: auto; }
        .data-box { margin-bottom: 10px; }
    </style>
    </head>
    <body>
        <a href="/">← Regresar</a>
        <h1>{{ m.nombre }}</h1>
        {% if m.foto %}<img src="{{ m.foto }}" style="max-width: 100%; border-radius: 12px;">{% endif %}
        
        <h3>Información</h3>
        <p class="data-box">📅 <strong>Fecha extravío:</strong> {{ m.fecha }}</p>
        <p class="data-box">🐕 <strong>Raza:</strong> {{ m.raza }} | <strong>Edad:</strong> {{ m.edad }} | <strong>Color:</strong> {{ m.color }}</p>
        <p class="data-box">⚧ <strong>Género:</strong> {{ m.genero }} | <strong>Collar:</strong> {{ m.collar }} | <strong>Dócil:</strong> {{ m.docil }}</p>
        
        <h3>Ubicación</h3>
        <p class="data-box">📍 {{ m.direccion }}, {{ m.ciudad }}, {{ m.estado }} (CP: {{ m.cp }})</p>
        <p class="data-box">🗺️ <strong>Entre calles:</strong> {{ m.calles }}</p>
        
        <h3>Contacto</h3>
        <p class="data-box">👤 <strong>Dueño:</strong> {{ m.dueno }}</p>
        <p class="data-box">💰 <strong>Recompensa:</strong> {{ m.recompensa }}</p>
        
        <a href="https://wa.me/{{ m.whatsapp }}" style="display:block; background: #25D366; color: white; padding: 15px; text-align:center; text-decoration: none; border-radius: 10px; font-weight:bold; margin-top:20px;">
            💬 Contactar por WhatsApp
        </a>
    </body>
    </html>
    """
    return render_template_string(html, m=m)

if __name__ == '__main__':
    app.run(debug=True)
