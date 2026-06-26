import os
import time
import base64
import traceback
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

ADMIN_TOKEN = "ubican123" 
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

mascotas_perdidas = []

@app.errorhandler(500)
def handle_internal_server_error(e):
    error_exacto = traceback.format_exc()
    return f"<pre>{error_exacto}</pre>", 500

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nombre = request.form.get("nombre")
        if nombre:
            url_principal = ""
            foto_principal = request.files.get("imagen_principal")
            if foto_principal and foto_principal.filename != '':
                bytes_p = foto_principal.read()
                b64_p = base64.b64encode(bytes_p).decode('utf-8')
                url_principal = f"data:{foto_principal.content_type};base64,{b64_p}"

            nuevo_reporte = {
                "id": str(int(time.time() * 1000)),
                "nombre": nombre,
                "descripcion": request.form.get("descripcion"),
                "zona": request.form.get("zona"),
                "contacto": request.form.get("contacto"),
                # Nuevos campos
                "fecha": request.form.get("fecha"),
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
                "recompensa": request.form.get("recompensa"),
                "principal": url_principal
            }
            mascotas_perdidas.insert(0, nuevo_reporte)
        return redirect(url_for('index'))

    html_index = """
    <!DOCTYPE html>
    <html lang="es">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Ubican ID SOS</title>
    <style>
        body { font-family: sans-serif; padding: 20px; max-width: 600px; margin: auto; background: #f8fafc; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; font-size: 0.9em; }
        input, select, textarea { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 8px; }
        .btn-publish { background: #ff6b4a; color: white; padding: 15px; width: 100%; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
    </style>
    </head>
    <body>
        <h2>Reportar Mascota</h2>
        <form method="POST" enctype="multipart/form-data">
            <div class="form-group"><label>01. FECHA DE EXTRAVÍO:</label><input type="date" name="fecha"></div>
            <h3>INFORMACIÓN DE LA MASCOTA</h3>
            <div class="form-group"><label>Nombre:</label><input type="text" name="nombre" required></div>
            <div class="form-group"><label>Edad:</label><input type="text" name="edad"></div>
            <div class="form-group"><label>Raza:</label><input type="text" name="raza"></div>
            <div class="form-group"><label>Género:</label><select name="genero"><option>Macho</option><option>Hembra</option></select></div>
            <div class="form-group"><label>Color:</label><input type="text" name="color"></div>
            <div class="form-group"><label>¿Collar?:</label><select name="collar"><option>Si</option><option>No</option></select></div>
            <div class="form-group"><label>¿Dócil?:</label><select name="docil"><option>Si</option><option>No</option></select></div>
            <h3>UBICACIÓN</h3>
            <div class="form-group"><label>Dirección:</label><input type="text" name="direccion"></div>
            <div class="form-group"><label>Ciudad:</label><input type="text" name="ciudad"></div>
            <div class="form-group"><label>Estado:</label><input type="text" name="estado"></div>
            <div class="form-group"><label>Código Postal:</label><input type="text" name="cp"></div>
            <div class="form-group"><label>Entre calles:</label><input type="text" name="calles"></div>
            <div class="form-group"><label>Zona (Resumen):</label><input type="text" name="zona"></div>
            <h3>CONTACTO</h3>
            <div class="form-group"><label>Dueño/Contacto:</label><input type="text" name="dueno"></div>
            <div class="form-group"><label>WhatsApp (+52/+1):</label><input type="tel" name="whatsapp"></div>
            <div class="form-group"><label>Recompensa:</label><select name="recompensa"><option>No</option><option>Si</option></select></div>
            <div class="form-group"><label>Descripción:</label><textarea name="descripcion"></textarea></div>
            <div class="form-group"><label>Foto Principal:</label><input type="file" name="imagen_principal"></div>
            <button type="submit" class="btn-publish">PUBLICAR ALERTA</button>
        </form>
        <hr>
        {% for m in mascotas %}
            <div style="padding:10px; border-bottom:1px solid #ccc;">
                <a href="/mascota/{{ m.id }}"><strong>{{ m.nombre }}</strong> - {{ m.zona }}</a>
            </div>
        {% endfor %}
    </body>
    </html>
    """
    return render_template_string(html_index, mascotas=mascotas_perdidas)

@app.route('/mascota/<id>')
def detalle_mascota(id):
    m = next((m for m in mascotas_perdidas if m["id"] == id), None)
    if not m: return redirect(url_for('index'))

    html_detalle = """
    <!DOCTYPE html>
    <html lang="es">
    <head><title>{{ m.nombre }}</title></head>
    <body style="font-family:sans-serif; padding:20px; line-height:1.6;">
        <a href="/">← Regresar</a>
        <h1>{{ m.nombre }}</h1>
        {% if m.principal %}<img src="{{ m.principal }}" style="max-width:300px; display:block;">{% endif %}
        <p><strong>Fecha Extravío:</strong> {{ m.fecha }}</p>
        <p><strong>Raza:</strong> {{ m.raza }} | <strong>Edad:</strong> {{ m.edad }} | <strong>Color:</strong> {{ m.color }}</p>
        <p><strong>Género:</strong> {{ m.genero }} | <strong>Collar:</strong> {{ m.collar }} | <strong>Dócil:</strong> {{ m.docil }}</p>
        <hr>
        <p><strong>Dirección:</strong> {{ m.direccion }}, {{ m.ciudad }}, {{ m.estado }} (CP: {{ m.cp }})</p>
        <p><strong>Entre calles:</strong> {{ m.calles }}</p>
        <hr>
        <p><strong>Dueño:</strong> {{ m.dueno }} | <strong>Recompensa:</strong> {{ m.recompensa }}</p>
        <p><strong>Detalles:</strong> {{ m.descripcion }}</p>
        <a href="https://wa.me/{{ m.whatsapp }}" style="background:green; color:white; padding:10px; text-decoration:none;">Contactar por WhatsApp</a>
    </body>
    </html>
    """
    return render_template_string(html_detalle, m=m)

if __name__ == '__main__':
    app.run(debug=True)
