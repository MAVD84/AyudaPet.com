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
    return f"<pre>{traceback.format_exc()}</pre>", 500

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Guardamos todos los campos solicitados
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
            :root { --primary-gradient: linear-gradient(135deg, #ff6b4a, #ff9f43); --dark: #1e293b; --bg: #f8fafc; --card-bg: #ffffff; --gray: #64748b; }
            * { box-sizing: border-box; }
            body { font-family: system-ui, sans-serif; background-color: var(--bg); color: var(--dark); padding-bottom: 120px; }
            .main-container { max-width: 1100px; margin: 40px auto; padding: 0 24px; }
            .grid-feed { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 24px; }
            .card-minimal { background: var(--card-bg); border-radius: 20px; border: 1px solid #e2e8f0; overflow: hidden; position: relative; transition: transform 0.2s; }
            .card-img-box { width: 100%; height: 260px; background: #f1f5f9; }
            .card-img-box img { width: 100%; height: 100%; object-fit: cover; }
            .card-info { padding: 16px; }
            .stretched-link { position: absolute; top:0; right:0; bottom:0; left:0; z-index:5; }
            .app-footer-bar { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(20px); border-top: 1px solid #e2e8f0; padding: 16px 24px; z-index: 100; text-align: center; }
            .btn-trigger-form { background: var(--primary-gradient); color: white; border: none; padding: 16px 32px; border-radius: 16px; font-weight: 700; cursor: pointer; }
            .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: none; z-index: 200; overflow-y: auto; }
            .modal-box { background: white; width: 90%; max-width: 500px; margin: 40px auto; padding: 24px; border-radius: 20px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; font-weight: 700; font-size: 0.85em; }
            input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 10px; }
        </style>
    </head>
    <body>
        <div class="main-container">
            <div class="grid-feed">
                {% for m in mascotas %}
                <div class="card-minimal">
                    <a href="/mascota/{{ m.id }}" class="stretched-link"></a>
                    <div class="card-img-box">{% if m.principal %}<img src="{{ m.principal }}">{% endif %}</div>
                    <div class="card-info"><h3>{{ m.nombre }}</h3><p>📍 {{ m.zona }}</p></div>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="app-footer-bar">
            <button class="btn-trigger-form" onclick="document.getElementById('modal').style.display='block'">🚨 Reportar Mascota Perdida</button>
        </div>
        <div id="modal" class="modal-overlay">
            <div class="modal-box">
                <form method="POST" enctype="multipart/form-data">
                    <h3>Registrar Reporte</h3>
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
                    <div class="form-group"><label>Código Postal:</label><input type="text" name="cp"></div>
                    <div class="form-group"><label>Entre calles:</label><input type="text" name="calles"></div>
                    <div class="form-group"><label>Zona:</label><input type="text" name="zona"></div>
                    <div class="form-group"><label>Dueño/Contacto:</label><input type="text" name="dueno"></div>
                    <div class="form-group"><label>WhatsApp (+52/+1):</label><input type="text" name="whatsapp"></div>
                    <div class="form-group"><label>Recompensa:</label><select name="recompensa"><option>No</option><option>Si</option></select></div>
                    <div class="form-group"><label>Descripción:</label><textarea name="descripcion"></textarea></div>
                    <div class="form-group"><label>Foto:</label><input type="file" name="imagen_principal"></div>
                    <button type="submit" style="width:100%; padding:15px; background:orange; border:none; border-radius:10px; font-weight:bold;">PUBLICAR</button>
                    <button type="button" onclick="document.getElementById('modal').style.display='none'" style="width:100%; margin-top:10px; padding:10px; border:none; background:none;">Cancelar</button>
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
    return render_template_string("""
    <body style="padding:24px; max-width:600px; margin:auto; font-family:sans-serif; line-height:1.7;">
        <a href="/">← Regresar</a>
        <h1>{{ m.nombre }}</h1>
        {% if m.principal %}<img src="{{ m.principal }}" style="max-width:100%; border-radius:20px;">{% endif %}
        <p><strong>Fecha:</strong> {{ m.fecha }}</p>
        <p><strong>Info:</strong> {{ m.raza }}, {{ m.edad }} años, {{ m.color }}</p>
        <p><strong>Género:</strong> {{ m.genero }} | <strong>Collar:</strong> {{ m.collar }} | <strong>Dócil:</strong> {{ m.docil }}</p>
        <hr><p><strong>Ubicación:</strong> {{ m.direccion }}, {{ m.ciudad }}, {{ m.estado }} (CP: {{ m.cp }})</p>
        <p><strong>Entre calles:</strong> {{ m.calles }}</p><hr>
        <p><strong>Dueño:</strong> {{ m.dueno }} | <strong>Recompensa:</strong> {{ m.recompensa }}</p>
        <p><strong>Detalles:</strong> {{ m.descripcion }}</p>
        <a href="https://wa.me/{{ m.whatsapp }}" style="display:block; padding:18px; background:green; color:white; text-align:center; border-radius:15px; text-decoration:none; font-weight:bold;">Contactar por WhatsApp</a>
    </body>""", m=m)

if __name__ == '__main__': app.run(debug=True)
