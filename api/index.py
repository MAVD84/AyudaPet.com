import os
import time
import base64
import traceback
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Base de datos temporal
mascotas_perdidas = []

@app.errorhandler(500)
def handle_internal_server_error(e):
    return f"<pre>{traceback.format_exc()}</pre>", 500

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Guardamos todos los datos del formulario
        nuevo_reporte = {
            "id": str(int(time.time() * 1000)),
            "nombre": request.form.get("nombre"),
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
            "descripcion": request.form.get("descripcion"),
            "zona": request.form.get("zona")
        }
        
        foto = request.files.get("imagen_principal")
        if foto and foto.filename != '':
            b64 = base64.b64encode(foto.read()).decode('utf-8')
            nuevo_reporte["principal"] = f"data:{foto.content_type};base64,{b64}"
            
        mascotas_perdidas.insert(0, nuevo_reporte)
        return redirect(url_for('index'))

    html_index = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ubican ID SOS</title>
        <style>
            :root { --primary: #ff6b4a; }
            body { font-family: system-ui, sans-serif; background: #f8fafc; padding-bottom: 100px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px; padding: 20px; max-width: 1100px; margin: auto; }
            .card { background: white; border-radius: 20px; border: 1px solid #e2e8f0; overflow: hidden; position: relative; transition: transform 0.2s; }
            .card:hover { transform: translateY(-5px); }
            .stretched-link { position: absolute; top:0; left:0; width:100%; height:100%; z-index:1; }
            .card-img { width: 100%; height: 200px; object-fit: cover; background: #eee; }
            .card-body { padding: 15px; }
            
            .footer-bar { position: fixed; bottom:0; width:100%; padding: 20px; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); text-align: center; z-index: 100; border-top: 1px solid #e2e8f0; }
            .btn { background: var(--primary); color: white; padding: 15px 30px; border-radius: 15px; border: none; font-weight: bold; cursor: pointer; }
            
            .modal { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index: 200; overflow-y: auto; }
            .modal-content { background: white; width: 90%; max-width: 500px; margin: 50px auto; padding: 25px; border-radius: 20px; }
            .form-group { margin-bottom: 12px; }
            input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
        </style>
    </head>
    <body>
        <div class="grid">
            {% for m in mascotas %}
            <div class="card">
                <a href="/mascota/{{ m.id }}" class="stretched-link"></a>
                {% if m.principal %}<img src="{{ m.principal }}" class="card-img">{% endif %}
                <div class="card-body">
                    <h3>{{ m.nombre }}</h3>
                    <p>📍 {{ m.zona }}</p>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="footer-bar"><button class="btn" onclick="document.getElementById('modal').style.display='block'">🚨 Reportar Mascota</button></div>
        
        <div id="modal" class="modal">
            <div class="modal-content">
                <h2>Registrar Reporte</h2>
                <form method="POST" enctype="multipart/form-data">
                    <div class="form-group"><label>01. FECHA DE EXTRAVÍO:</label><input type="date" name="fecha" required></div>
                    <div class="form-group"><label>Nombre:</label><input type="text" name="nombre"></div>
                    <div class="form-group"><label>Edad:</label><input type="text" name="edad"></div>
                    <div class="form-group"><label>Raza:</label><input type="text" name="raza"></div>
                    <div class="form-group"><label>Género:</label><select name="genero"><option>Macho</option><option>Hembra</option></select></div>
                    <div class="form-group"><label>Color:</label><input type="text" name="color"></div>
                    <div class="form-group"><label>¿Collar?:</label><select name="collar"><option>Si</option><option>No</option></select></div>
                    <div class="form-group"><label>¿Dócil?:</label><select name="docil"><option>Si</option><option>No</option></select></div>
                    <div class="form-group"><label>Dirección:</label><input type="text" name="direccion"></div>
                    <div class="form-group"><label>Ciudad:</label><input type="text" name="ciudad"></div>
                    <div class="form-group"><label>Estado:</label><input type="text" name="estado"></div>
                    <div class="form-group"><label>CP:</label><input type="text" name="cp"></div>
                    <div class="form-group"><label>Entre calles:</label><input type="text" name="calles"></div>
                    <div class="form-group"><label>Zona:</label><input type="text" name="zona"></div>
                    <div class="form-group"><label>Dueño/Contacto:</label><input type="text" name="dueno"></div>
                    <div class="form-group"><label>WhatsApp (+52/+1):</label><input type="text" name="whatsapp"></div>
                    <div class="form-group"><label>Recompensa:</label><select name="recompensa"><option>No</option><option>Si</option></select></div>
                    <div class="form-group"><label>Descripción:</label><textarea name="descripcion"></textarea></div>
                    <div class="form-group"><label>Foto:</label><input type="file" name="imagen_principal"></div>
                    <button type="submit" class="btn" style="width:100%">PUBLICAR</button>
                    <button type="button" onclick="document.getElementById('modal').style.display='none'" style="width:100%; margin-top:10px; background:none; border:none; color:gray;">Cancelar</button>
                </form>
            </div>
        </div>
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
    <body style="padding:20px; max-width:600px; margin:auto; font-family:sans-serif; line-height:1.6;">
        <a href="/" style="text-decoration:none; color:gray;">← Regresar</a>
        <h1 style="margin-top:10px;">{{ m.nombre }}</h1>
        {% if m.principal %}<img src="{{ m.principal }}" style="max-width:100%; border-radius:20px; display:block;">{% endif %}
        
        <div style="margin-top:20px;">
            <p>📅 <strong>Fecha extravío:</strong> {{ m.fecha }}</p>
            <p>🐾 <strong>Raza:</strong> {{ m.raza }} | <strong>Edad:</strong> {{ m.edad }} | <strong>Color:</strong> {{ m.color }}</p>
            <p>⚧ <strong>Género:</strong> {{ m.genero }} | <strong>Collar:</strong> {{ m.collar }} | <strong>Dócil:</strong> {{ m.docil }}</p>
            <hr>
            <p>📍 <strong>Ubicación:</strong> {{ m.direccion }}, {{ m.ciudad }}, {{ m.estado }} (CP: {{ m.cp }})</p>
            <p>🗺️ <strong>Entre calles:</strong> {{ m.calles }}</p>
            <hr>
            <p>👤 <strong>Dueño:</strong> {{ m.dueno }}</p>
            <p>💰 <strong>Recompensa:</strong> {{ m.recompensa }}</p>
            <p>📝 <strong>Detalles:</strong> {{ m.descripcion }}</p>
        </div>
        
        <a href="https://wa.me/{{ m.whatsapp }}" style="display:block; padding:18px; background:#25D366; color:white; text-align:center; border-radius:15px; text-decoration:none; font-weight:bold; margin-top:20px;">
            💬 Contactar por WhatsApp
        </a>
    </body>
    </html>
    """
    return render_template_string(html_detalle, m=m)

if __name__ == '__main__':
    app.run(debug=True)
