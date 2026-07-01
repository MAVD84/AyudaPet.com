# AyudaPet

Aplicacion PHP + MySQL para reportes de mascotas perdidas/localizadas.

## Stack

- PHP 8.3 con Apache
- MySQL/MariaDB
- LabsMobile para OTP por SMS
- Google Maps Places + mapa con `API_KEY`
- Uploads locales en `/uploads`

## Variables de entorno

Configura estas variables en Coolify:

```env
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=ayudapet
MYSQL_USER=ayudapet
MYSQL_PASSWORD=

SHOW_OTP_IN_DEV=false
OTP_TTL_SECONDS=300

LABSMOBILE_USER=
LABSMOBILE_TOKEN=
LABSMOBILE_SENDER=AYUDAPET
LABSMOBILE_API=https://api.labsmobile.com/json/send
LABSMOBILE_DEFAULT_COUNTRY_CODE=52

API_KEY=
```

## Base de datos

Ejecuta [database/schema.sql](database/schema.sql) en tu MySQL antes de usar la app.

## Coolify

1. Usa el `Dockerfile` del repo.
2. Agrega un servicio MySQL en el mismo proyecto/red.
3. Configura las variables `MYSQL_*` con los datos del servicio MySQL.
4. Recomendado: crea un volumen persistente para `/var/www/html/uploads` para no perder imagenes al redeploy.
5. Ejecuta el SQL de `database/schema.sql`.
6. Redeploy.

## Desarrollo local rapido

Con PHP instalado:

```bash
php -S 127.0.0.1:8000
```

Necesitas un MySQL accesible y las variables de entorno `MYSQL_*`.

## Notas

- El repo ya no usa Supabase ni Flask.
- Las imagenes se guardan localmente en `/uploads`.
- No subas archivos `.env` al repositorio.
