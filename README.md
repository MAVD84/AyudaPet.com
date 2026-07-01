# UBICAN ID - Reportes SOS

Aplicacion Flask para registrar usuarios por telefono, verificar OTP y publicar reportes de mascotas perdidas o encontradas usando Supabase como base de datos.

## Configuracion

1. Copia `.env.example` a `.env`.
2. Rellena valores reales y nuevos. No reutilices claves que hayan sido publicadas en Git.
3. En Supabase, ejecuta `supabase_hardening.sql` despues de rotar credenciales.

Variables principales:

- `SECRET_KEY`: valor largo y aleatorio para sesiones Flask.
- `SUPABASE_URL`: URL del proyecto Supabase.
- `SUPABASE_SERVICE_ROLE_KEY`: key solo para el servidor Flask.
- `SUPABASE_STORAGE_BUCKET`: bucket publico donde se suben fotos de reportes.
- `SHOW_OTP_IN_DEV`: usa `true` solo en desarrollo para ver codigos OTP en pantalla.
- `LABSMOBILE_*`: credenciales para envio de SMS. `LABSMOBILE_DEFAULT_COUNTRY_CODE=52` convierte telefonos mexicanos de 10 digitos a formato internacional.
- `GOOGLE_SHEETS_WEBHOOK_URL`: URL del Web App de Apps Script para guardar nombre y WhatsApp de visitantes.
- `GOOGLE_SHEETS_WEBHOOK_SECRET`: clave privada simple para validar que el registro viene desde AyudaPet.

## Registro inicial en Google Sheets

1. Crea un Google Sheet con una hoja llamada `Registros`.
2. En Google Sheets abre `Extensiones > Apps Script`.
3. Pega este codigo y cambia `CAMBIA_ESTE_SECRETO` por el mismo valor que pondras en Coolify como `GOOGLE_SHEETS_WEBHOOK_SECRET`:

```js
const SHEET_NAME = "Registros";
const WEBHOOK_SECRET = "CAMBIA_ESTE_SECRETO";

function doPost(e) {
  const data = JSON.parse(e.postData.contents || "{}");
  if (WEBHOOK_SECRET && data.secret !== WEBHOOK_SECRET) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME)
    || SpreadsheetApp.getActiveSpreadsheet().insertSheet(SHEET_NAME);

  if (sheet.getLastRow() === 0) {
    sheet.appendRow(["Fecha", "Nombre", "WhatsApp", "WhatsApp E164", "Pagina", "User Agent"]);
  }

  sheet.appendRow([
    data.registrado_at || new Date().toISOString(),
    data.nombre || "",
    data.whatsapp || "",
    data.whatsapp_e164 || "",
    data.pagina || "",
    data.user_agent || "",
  ]);

  return ContentService.createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

4. Publica como `Implementar > Nueva implementacion > Aplicacion web`.
5. Usa `Ejecutar como: Yo` y `Quien tiene acceso: Cualquier usuario`.
6. Copia la URL del Web App en Coolify como `GOOGLE_SHEETS_WEBHOOK_URL`.

## Desarrollo local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre `http://127.0.0.1:5000`.

## Seguridad

- `.env` esta ignorado por Git.
- No expongas `SUPABASE_SERVICE_ROLE_KEY` en frontend.
- Ejecuta `supabase_storage.sql` para crear el bucket publico de imagenes.
- Rota las claves que estuvieron en el historial del repositorio.
- Para eliminar secretos del historial publico, usa una herramienta como `git filter-repo` o rota claves y reemplaza el repositorio si prefieres una ruta simple.
