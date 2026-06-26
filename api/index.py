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
        # Recolectar todos los campos nuevos
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
        
        # Procesar imagen
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
    <title>Registro SOS</title>
    <style>
        body { font-family: sans-serif; padding: 20px; line-height: 1.6; max-width: 600px; margin: auto; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 8px; margin-top: 5px; }
        button { background: #ff6b4a; color: white; border: none; padding: 15px; width: 100%; font-weight: bold; cursor: pointer; }
    </style>
    </head>
    <body>
        <h2>Reportar Mascota Perdida</h2>
        <form method="POST" enctype="multipart/form-data">
            <div class="form-group"><label>01. FECHA DE EXTRAVÍO:</label><input type="date" name="fecha" required></div>
            <hr>
            <h3>INFORMACIÓN DE LA MASCOTA</h3>
            <div class="form-group"><label>Nombre:</label><input type="text" name="nombre"></div>
            <div class="form-group"><label>Edad:</label><input type="text" name="edad"></div>
            <div class="form-group"><label>Raza:</label><input type="text" name="raza"></div>
            <div class="form-group"><label>Género:</label><select name="genero"><option>Macho</option><option>Hembra</option></select></div>
            <div class="form-group"><label>Color:</label><input type="text" name="color"></div>
            <div class="form-group"><label>¿Collar?:</label><select name="collar"><option>Si</option><option>No</option></select></div>
            <div class="form-group"><label>¿Dócil?:</label><select name="docil"><option>Si</option><option>No</option></select></div>
            <hr>
            <h3>UBICACIÓN DE EXTRAVÍO</h3>
            <div class="form-group"><label>Dirección:</label><input type="text" name="direccion"></div>
            <div class="form-group"><label>Ciudad:</label><input type="text" name="ciudad"></div>
            <div class="form-group"><label>Estado:</label><input type="text" name="estado"></div>
            <div class="form-group"><label>Codigo Postal:</label><input type="text" name="cp"></div>
            <div class="form-group"><label>Entre calles:</label><input type="text" name="calles"></div>
            <hr>
            <h3>CONTACTO / DUEÑO</h3>
            <div class="form-group"><label>Dueño/Contacto:</label><input type="text" name="dueno"></div>
            <div class="form-group"><label>WhatsApp (Lada +52/+1):</label><input type="text" name="whatsapp" placeholder="+52..."></div>
            <div class="form-group"><label>Recompensa:</label><select name="recompensa"><option>No</option><option>Si</option></select></div>
            <div class="form-group"><label>Foto:</label><input type="file" name="imagen" accept="image/*"></div>
            <button type="submit">PUBLICAR ALERTA</button>
        </form>
        <hr>
        <h2>Reportes Activos</h2>
        {% for m in mascotas %}
            <div style="border-bottom: 1px solid #ccc; padding: 10px 0;">
                <a href="/mascota/{{ m.id }}"><strong>{{ m.nombre }}</strong> - {{ m.ciudad }}</a>
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
    <head><title>Detalle: {{ m.nombre }}</title></head>
    <body style="padding: 20px; font-family: sans-serif;">
        <a href="/">← Regresar</a>
        <h1>{{ m.nombre }}</h1>
        {% if m.foto %}<img src="{{ m.foto }}" style="max-width: 300px; display:block;">{% endif %}
        <p><strong>Fecha:</strong> {{ m.fecha }}</p>
        <p><strong>Raza:</strong> {{ m.raza }} | <strong>Edad:</strong> {{ m.edad }} | <strong>Color:</strong> {{ m.color }}</p>
        <p><strong>Género:</strong> {{ m.genero }} | <strong>¿Collar?:</strong> {{ m.collar }} | <strong>¿Dócil?:</strong> {{ m.docil }}</p>
        <hr>
        <p><strong>Ubicación:</strong> {{ m.direccion }}, {{ m.ciudad }}, {{ m.estado }} (CP: {{ m.cp }})</p>
        <p><strong>Entre calles:</strong> {{ m.calles }}</p>
        <hr>
        <p><strong>Dueño:</strong> {{ m.dueno }}</p>
        <p><strong>Recompensa:</strong> {{ m.recompensa }}</p>
        <a href="https://wa.me/{{ m.whatsapp }}" style="background: green; color: white; padding: 10px; text-decoration: none;">Contactar por WhatsApp</a>
    </body>
    </html>
    """
    return render_template_string(html, m=m)

if __name__ == '__main__':
    app.run(debug=True)
