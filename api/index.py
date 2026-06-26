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
        if nombre and nombre.strip() != "":
            url_principal = ""
            lista_secundarias = []
            try:
                foto_principal = request.files.get("imagen_principal")
                if foto_principal and foto_principal.filename != '':
                    b64_p = base64.b64encode(foto_principal.read()).decode('utf-8')
                    url_principal = f"data:{foto_principal.content_type};base64,{b64_p}"

                for archivo in request.files.getlist("imagenes_secundarias")[:4]:
                    if archivo and archivo.filename != '':
                        b64_s = base64.b64encode(archivo.read()).decode('utf-8')
                        lista_secundarias.append(f"data:{archivo.content_type};base64,{b64_s}")
            except: pass

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
                "recompensa": request.form.get("recompensa"),
                "principal": url_principal,
                "secundarias": lista_secundarias
            }
            mascotas_perdidas.insert(0, nuevo_reporte)
        return redirect(url_for('index'))

    html_index = """
    <!DOCTYPE html>
    <html lang="es"><head><meta charset="UTF-8"><title>Ubican ID SOS</title>
    <style>
        :root { --primary: #ff6b4a; }
        body { font-family: system-ui, sans-serif; background: #f8fafc; padding-bottom: 120px; }
        .grid-feed { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 24px; padding: 40px 24px; max-width: 1100px; margin: auto; }
        .card-minimal { background: white; border-radius: 20px; border: 1px solid #e2e8f0; overflow: hidden; position: relative; }
        .card-img-box { width: 100%; height: 260px; background: #f1f5f9; }
        .card-img-box img { width: 100%; height: 100%; object-fit: cover; }
        .app-footer-bar { position: fixed; bottom: 0; width: 100%; background: rgba(255,255,255,0.9); backdrop-filter: blur(10px); padding: 16px; text-align: center; }
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: none; z-index: 200; overflow-y: auto; }
        .modal-box { background: white; width: 90%; max-width: 500px; margin: 40px auto; padding: 24px; border-radius: 20px; }
        .form-group { margin-bottom: 12px; }
        input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 10px; }
    </style></head>
    <body>
        <div class="grid-feed">
            {% for m in mascotas %}
            <div class="card-minimal">
                <a href="/mascota/{{ m.id }}" style="position:absolute; inset:0; z-index:5;"></a>
                <div class="card-img-box">{% if m.principal %}<img src="{{ m.principal }}">{% endif %}</div>
                <div style="padding:16px;"><h3>{{ m.nombre }}</h3><p>📍 {{ m.zona }}</p></div>
            </div>
            {% endfor %}
        </div>
        <div class="app-footer-bar"><button onclick="document.getElementById('m').style.display='block'" style="background:var(--primary); color:white; border:none; padding:15px 40px; border-radius:15px; font-weight:bold; cursor:pointer;">🚨 REPORTAR MASCOTA</button></div>
        
        <div id="m" class="modal-overlay">
            <div class="modal-box">
                <form method="POST" enctype="multipart/form-data">
                    <div class="form-group"><label>Fecha extravío:</label><input type="date" name="fecha" required></div>
                    <div class="form-group"><label>Nombre:</label><input type="text" name="nombre" required></div>
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
                    <div class="form-group"><label>Dueño:</label><input type="text" name="dueno"></div>
                    <div class="form-group"><label>WhatsApp:</label><input type="text" name="contacto" placeholder="Ej. 52656..."></div>
                    <div class="form-group"><label>Recompensa:</label><select name="recompensa"><option>No</option><option>Si</option></select></div>
                    <div class="form-group"><label>Descripción:</label><textarea name="descripcion"></textarea></div>
                    <div class="form-group"><label>Foto Principal:</label><input type="file" name="imagen_principal"></div>
                    <div class="form-group"><label>Fotos adicionales:</label><input type="file" name="imagenes_secundarias" multiple></div>
                    <button type="submit" style="width:100%; padding:15px; background:var(--primary); color:white; border:none; border-radius:10px;">PUBLICAR</button>
                    <button type="button" onclick="document.getElementById('m').style.display='none'" style="width:100%; margin-top:10px; background:none; border:none; color:gray;">Cancelar</button>
                </form>
            </div>
        </div>
    </body></html>
    """
    return render_template_string(html_index, mascotas=mascotas_perdidas)

@app.route('/mascota/<id>')
def detalle_mascota(id):
    m = next((m for m in mascotas_perdidas if m["id"] == id), None)
    if not m: return redirect(url_for('index'))
    return render_template_string("""
    <body style="padding:20px; max-width:600px; margin:auto; font-family:sans-serif; line-height:1.6;">
        <a href="/">← Regresar</a>
        <h1>{{ m.nombre }}</h1>
        {% if m.principal %}<img src="{{ m.principal }}" style="width:100%; border-radius:20px;">{% endif %}
        <h3>Datos</h3>
        <p>📅 <strong>Fecha:</strong> {{ m.fecha }} | 🐕 <strong>Raza:</strong> {{ m.raza }} | 🎂 <strong>Edad:</strong> {{ m.edad }} | 🎨 <strong>Color:</strong> {{ m.color }}</p>
        <p>⚧ <strong>Género:</strong> {{ m.genero }} | 📿 <strong>Collar:</strong> {{ m.collar }} | 😇 <strong>Dócil:</strong> {{ m.docil }}</p>
        <hr>
        <p>📍 <strong>Dirección:</strong> {{ m.direccion }}, {{ m.ciudad }}, {{ m.estado }} (CP: {{ m.cp }})</p>
        <p>🚧 <strong>Entre calles:</strong> {{ m.calles }}</p>
        <hr>
        <p>👤 <strong>Dueño:</strong> {{ m.dueno }} | 💰 <strong>Recompensa:</strong> {{ m.recompensa }}</p>
        <p>📝 <strong>Descripción:</strong> {{ m.descripcion }}</p>
        <a href="https://wa.me/{{ m.contacto }}" style="display:block; padding:20px; background:#25D366; color:white; text-align:center; border-radius:15px; text-decoration:none; font-weight:bold;">💬 CONTACTAR POR WHATSAPP</a>
    </body>""", m=m)

if __name__ == '__main__': app.run(debug=True)
