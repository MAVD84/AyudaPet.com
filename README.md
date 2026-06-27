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
