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

PAYPAL_CLIENT_ID=
PAYPAL_SECRET=
PAYPAL_MODE=live
PAYPAL_DONATE_URL=https://www.paypal.com/ncp/payment/8PWUWFX8JZFUE
BOOST_BUTTON_ENABLED=true

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
- Para impulsar anuncios con PayPal, crea una app REST en PayPal Developer y configura `PAYPAL_CLIENT_ID`, `PAYPAL_SECRET` y `PAYPAL_MODE=live`. El pago se captura al volver a `https://ayudapet.com/paypal/return`.
- Para donativos por PayPal, el boton usa `PAYPAL_DONATE_URL`. El enlace actual es `https://www.paypal.com/ncp/payment/8PWUWFX8JZFUE`.
- Usa `BOOST_BUTTON_ENABLED=false` para ocultar temporalmente el boton de impulso y manejarlo manualmente.
- `BOOST_NOTIFY_EMAIL` recibe un correo cada vez que un anuncio se activa como impulsado.
- Para correos SMTP usa el email real creado en tu hosting. Normalmente `SMTP_PORT=587` con `SMTP_SECURE=tls`; si tu hosting indica puerto `465`, usa `SMTP_SECURE=ssl`.
- Para probar correo inicia sesion y abre `/correo/prueba`; la pagina muestra si SMTP envio o el error exacto.
- Para avisar impulsos vencidos, configura un cron que abra `https://ayudapet.com/cron/boosts?token=TU_CRON_SECRET` una vez por hora o una vez al dia.
- Si el hosting usa cron por archivo, programa `/usr/bin/php /home/sites/36b/5/5bebbea9cb/public_html/cron-boosts.php` una vez por hora.
