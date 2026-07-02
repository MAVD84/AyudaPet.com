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
MYSQL_HOST=localhost
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

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID=

BOOST_NOTIFY_EMAIL=
MAIL_FROM=no-reply@ayudapet.com
SMTP_HOST=mail.ayudapet.com
SMTP_PORT=587
SMTP_USER=no-reply@ayudapet.com
SMTP_PASS=
SMTP_SECURE=tls
SMTP_FROM=no-reply@ayudapet.com
SMTP_FROM_NAME=AyudaPet
CRON_SECRET=
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
- Para impulsar anuncios, crea un producto/precio en Stripe por `$1,300 MXN`, usa ese `STRIPE_PRICE_ID` y configura el webhook a `https://ayudapet.com/stripe/webhook` escuchando `checkout.session.completed`.
- `BOOST_NOTIFY_EMAIL` recibe un correo cada vez que un anuncio se activa como impulsado.
- Para correos SMTP usa el email real creado en tu hosting. Normalmente `SMTP_PORT=587` con `SMTP_SECURE=tls`; si tu hosting indica puerto `465`, usa `SMTP_SECURE=ssl`.
- Para probar correo inicia sesion y abre `/correo/prueba`; la pagina muestra si SMTP envio o el error exacto.
- Para avisar impulsos vencidos, configura un cron que abra `https://ayudapet.com/cron/boosts?token=TU_CRON_SECRET` una vez por hora o una vez al dia.
