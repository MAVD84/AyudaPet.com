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
        # Procesar fotos
        url_principal = ""
        foto_p = request.files.get("imagen_principal")
        if foto_p and foto_p.filename != '':
            url_principal = f"data:{foto_p.content_type};base64,{base64.b64encode(foto_p.read()).decode('utf-8')}"
        
        lista_secundarias = []
        for f in request.files.getlist("imagenes_secundarias"):
            if f and f.filename != '':
                lista_secundarias.append(f"data:{f.content_type};base64,{base64.b64encode(f.read()).decode('utf-8')}")

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
            "zona": request.form.get("zona"),
            "dueno": request.form.get("dueno"),
            "whatsapp": request.form.get("whatsapp"),
            "recompensa": request.form.get("recompensa"),
            "descripcion": request.form.get("descripcion"),
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
        body { font-family: system-ui, sans-serif; background: #f8fafc; padding-bottom: 100px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px; padding: 20px; max-width: 1100px; margin: auto; }
        .card { background: white; border-radius: 20px; border: 1px solid #e2e8f0; padding: 15px; position: relative; }
        .footer-bar { position: fixed; bottom:0; width:100%; padding: 20px; background: rgba(255,255,255,0.95); text-align: center; border-top: 1px solid #eee; }
        .modal { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:99; overflow-y:auto; }
        .modal-content { background: white; width: 90%; max-width: 500px; margin: 40px auto; padding: 20px; border-radius: 20px; }
        input, select, textarea { width:100%; padding:8px; margin:5px 0; border:1px solid #ddd; border-radius:8px; }
    </style></head>
    <body>
        <div class="grid">
            {% for m in mascotas %}
            <div class="card">
                <a href="/mascota/{{ m.id }}" style="position:absolute; inset:0; z-index:1;"></a>
                {% if m.principal %}<img src="{{ m.principal }}" style="width:100%; height:200px; object-fit:cover; border-radius:10px;">{% endif %}
                <h3>{{ m.nombre }}</h3><p>📍 {{ m.zona }}</p>
            </div>
            {% endfor %}
        </div>
        <div class="footer-bar"><button onclick="document.getElementById('m').style.display='block'" style="background:var(--primary); color:white; padding:15px 30px; border:none; border-radius:15px; font-weight:bold; cursor:pointer;">🚨 Reportar Mascota</button></div>
        
        <div id="m" class="modal"><div class="modal-content">
            <form method="POST" enctype="multipart/form-data">
                <label>01. FECHA DE EXTRAVÍO:</label><input type="date" name="fecha" required>
                <label>Nombre:</label><input type="text" name="nombre">
                <label>Edad:</label><input type="text" name="edad">
                <label>Raza:</label><input type="text" name="raza">
                <label>Género:</label><select name="genero"><option>Macho</option><option>Hembra</option></select>
                <label>Color:</label><input type="text" name="color">
                <label>¿Collar?:</label><select name="collar"><option>Si</option><option>No</option></select>
                <label>¿Dócil?:</label><select name="docil"><option>Si</option><option>No</option></select>
                <label>Dirección:</label><input type="text" name="direccion">
                <label>Ciudad:</label><input type="text" name="ciudad">
                <label>Estado:</label><input type="text" name="estado">
                <label>CP:</label><input type="text" name="cp">
                <label>Entre calles:</label><input type="text" name="calles">
                <label>Zona:</label><input type="text" name="zona">
                <label>Dueño:</label><input type="text" name="dueno">
                <label>WhatsApp (+52/+1):</label><input type="text" name="whatsapp">
                <label>Recompensa:</label><select name="recompensa"><option>No</option><option>Si</option></select>
                <label>Descripción:</label><textarea name="descripcion"></textarea>
                <label>Foto Principal:</label><input type="file" name="imagen_principal">
                <label>Fotos Adicionales:</label><input type="file" name="imagenes_secundarias" multiple>
                <button type="submit" style="width:100%; padding:15px; background:var(--primary); color:white; border:none; border-radius:10px;">PUBLICAR</button>
            </form>
        </div></div>
    </body></html>
    """
    return render_template_string(html_index, mascotas=mascotas_perdidas)

@app.route('/mascota/<id>')
def detalle_mascota(id):
    m = next((m for m in mascotas_perdidas if m["id"] == id), None)
    if not m: return redirect(url_for('index'))
    return render_template_string("""
    <body style="padding:20px; max-width:600px; margin:auto; font-family:sans-serif;">
        <a href="/">← Regresar</a>
        <h1>{{ m.nombre }}</h1>
        {% if m.principal %}<img src="{{ m.principal }}" style="width:100%; border-radius:20px;">{% endif %}
        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; margin:10px 0;">
            {% for img in m.secundarias %}<img src="{{ img }}" style="width:100%; height:80px; object-fit:cover; border-radius:10px;">{% endfor %}
        </div>
        <p>📅 {{ m.fecha }} | 🐕 {{ m.raza }} | 🎂 {{ m.edad }} años | 🎨 {{ m.color }}</p>
        <p>⚧ {{ m.genero }} | Collar: {{ m.collar }} | Dócil: {{ m.docil }}</p>
        <hr><p>📍 {{ m.direccion }}, {{ m.ciudad }}, {{ m.estado }} (CP: {{ m.cp }})</p>
        <p>🚧 Entre calles: {{ m.calles }}</p><hr>
        <p>👤 {{ m.dueno }} | 💰 Recompensa: {{ m.recompensa }}</p>
        <p>📝 {{ m.descripcion }}</p>
        <a href="https://wa.me/{{ m.whatsapp }}" style="display:block; padding:18px; background:green; color:white; text-align:center; border-radius:15px; text-decoration:none; font-weight:bold;">CONTACTAR POR WHATSAPP</a>
    </body>""", m=m)

if __name__ == '__main__': app.run(debug=True)
