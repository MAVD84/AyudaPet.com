<?php
declare(strict_types=1);

session_start();

$configFile = __DIR__ . '/config.php';
if (is_file($configFile)) {
    require_once $configFile;
}

function load_dotenv_file(string $file): void {
    if (!is_file($file) || !is_readable($file)) return;
    $lines = file($file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if (!$lines) return;
    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || strpos($line, '#') === 0 || strpos($line, '=') === false) continue;
        [$key, $value] = explode('=', $line, 2);
        $key = trim($key);
        $value = trim($value);
        if ($key === '') continue;
        $first = substr($value, 0, 1);
        $last = substr($value, -1);
        if (($first === '"' && $last === '"') || ($first === "'" && $last === "'")) {
            $value = substr($value, 1, -1);
        }
        if (getenv($key) === false) {
            putenv($key . '=' . $value);
            $_ENV[$key] = $value;
            $_SERVER[$key] = $value;
        }
    }
}

load_dotenv_file(dirname(__DIR__) . '/.env');
load_dotenv_file(__DIR__ . '/.env');

const APP_NAME = 'AyudaPet';
const APP_DOMAIN = 'ayudapet.com';
const MAX_SECONDARY_IMAGES = 3;
const DEFAULT_PUBLIC_CONTACT = '+526564252167';
const OLD_PUBLIC_CONTACTS = ['+526567787712', '6567787712', '526567787712'];
const DEFAULT_ADMIN_PHONE = '6564252167';
const BOOST_DAYS = 10;
const BOOST_PRICE_CENTS = 130000;
const BOOST_PRICE_LABEL = '$1,300 M.N.';
const BOOST_PRODUCT_IMAGE_URL = 'https://ayudapet.com/uploads/images/product.jpeg';
const DEFAULT_OG_IMAGE = '/static/og-social.jpg';
const PET_OG_VERSION = 'v6';
const DEFAULT_DONATION_URL = 'https://www.paypal.com/ncp/payment/8PWUWFX8JZFUE';

date_default_timezone_set(getenv('APP_TIMEZONE') ?: 'America/Matamoros');

function starts_with(string $haystack, string $needle): bool {
    return $needle === '' || strpos($haystack, $needle) === 0;
}

function contains_text(string $haystack, string $needle): bool {
    return $needle === '' || strpos($haystack, $needle) !== false;
}

function first_letter(?string $value): string {
    $value = trim((string)$value);
    if ($value === '') return '?';
    if (function_exists('mb_substr') && function_exists('mb_strtoupper')) {
        return mb_strtoupper(mb_substr($value, 0, 1, 'UTF-8'), 'UTF-8');
    }
    return strtoupper(substr($value, 0, 1));
}

function lower_text(string $value): string {
    return function_exists('mb_strtolower') ? mb_strtolower($value, 'UTF-8') : strtolower($value);
}

function envv(string $key, ?string $default = null): ?string {
    if (defined($key)) {
        $value = constant($key);
        return $value === '' || $value === null ? $default : (string)$value;
    }
    $value = getenv($key);
    return $value === false || $value === '' ? $default : $value;
}

function boost_plans(): array {
    return [
        3 => [
            'name' => 'Reaccion rapida',
            'days' => 3,
            'price_cents' => 40500,
            'price_label' => '$405 MXN',
            'features' => ['Anuncios en Facebook e Instagram', 'Radio de 5 km a la redonda', 'Diseno de ficha profesional', 'Activacion en menos de 30 min'],
        ],
        7 => [
            'name' => 'Impacto semanal',
            'days' => 7,
            'price_cents' => 86000,
            'price_label' => '$860 MXN',
            'features' => ['Anuncios en Facebook e Instagram', 'Radio de 10 km intermedio', 'Diseno de ficha profesional', 'Asesoria contra extorsiones', 'Activacion en menos de 30 min'],
        ],
        10 => [
            'name' => 'Cobertura total',
            'days' => 10,
            'price_cents' => 130000,
            'price_label' => '$1,300 MXN',
            'features' => ['Anuncios en Facebook e Instagram', 'Radio de 15 km maximo', 'Diseno de ficha profesional', 'Asesoria contra extorsiones', 'Formato video/reel', 'Activacion en 30 min'],
        ],
    ];
}

function boost_plan_enabled(int $days): bool {
    if (!array_key_exists($days, boost_plans())) return false;
    $value = app_setting('boost_plan_' . $days . '_enabled');
    if ($value === null) $value = envv('BOOST_PLAN_' . $days . '_ENABLED', 'true');
    $value = lower_text(trim((string)$value));
    return !in_array($value, ['0', 'false', 'off', 'no'], true);
}

function visible_boost_plans(): array {
    $plans = array_filter(boost_plans(), fn($plan) => boost_plan_enabled((int)$plan['days']));
    return $plans ?: [BOOST_DAYS => boost_plan(BOOST_DAYS)];
}

function default_boost_plan_days(): int {
    $plans = visible_boost_plans();
    return isset($plans[BOOST_DAYS]) ? BOOST_DAYS : (int)array_key_first($plans);
}

function boost_plan(int $days): array {
    $plans = boost_plans();
    return $plans[$days] ?? $plans[BOOST_DAYS];
}

function boost_plan_days($value, bool $visibleOnly = true): int {
    $days = (int)$value;
    $plans = $visibleOnly ? visible_boost_plans() : boost_plans();
    return array_key_exists($days, $plans) ? $days : default_boost_plan_days();
}

function db(): PDO {
    static $pdo = null;
    if ($pdo instanceof PDO) return $pdo;

    $host = envv('MYSQL_HOST', envv('DB_HOST', 'localhost'));
    $port = envv('MYSQL_PORT', envv('DB_PORT', '3306'));
    $name = envv('MYSQL_DATABASE', envv('DB_DATABASE', 'ayudapet'));
    $user = envv('MYSQL_USER', envv('DB_USER', 'ayudapet'));
    $pass = envv('MYSQL_PASSWORD', envv('DB_PASSWORD', ''));
    $dsn = "mysql:host={$host};port={$port};dbname={$name};charset=utf8mb4";
    $pdo = new PDO($dsn, $user, $pass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    return $pdo;
}

function ensure_report_columns(): void {
    static $checked = false;
    if ($checked) return;
    $checked = true;
    $columns = db()->query('SHOW COLUMNS FROM mascotas')->fetchAll();
    $existing = [];
    foreach ($columns as $column) {
        $existing[$column['Field']] = true;
    }
    if (empty($existing['vistas'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN vistas INT UNSIGNED NOT NULL DEFAULT 0');
    }
    if (empty($existing['tipo_reporte'])) {
        db()->exec("ALTER TABLE mascotas ADD COLUMN tipo_reporte VARCHAR(30) NULL DEFAULT 'extravio'");
    }
    if (empty($existing['tipo_mascota'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN tipo_mascota VARCHAR(40) NULL');
    }
    if (empty($existing['ubicacion_lat'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN ubicacion_lat DECIMAL(9,6) NULL');
    }
    if (empty($existing['ubicacion_lng'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN ubicacion_lng DECIMAL(9,6) NULL');
    }
    if (empty($existing['direccion_completa'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN direccion_completa VARCHAR(700) NULL');
    }
    if (empty($existing['impulsado_hasta'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN impulsado_hasta DATETIME NULL');
    }
    if (empty($existing['paypal_order_id'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN paypal_order_id VARCHAR(255) NULL');
    }
    if (empty($existing['paypal_payment_status'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN paypal_payment_status VARCHAR(50) NULL');
    }
    if (empty($existing['paypal_boost_days'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN paypal_boost_days TINYINT UNSIGNED NULL');
    }
    if (empty($existing['boost_expired_notified_at'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN boost_expired_notified_at DATETIME NULL');
    }
}

function ensure_user_columns(): void {
    static $checked = false;
    if ($checked) return;
    $checked = true;
    $columns = db()->query('SHOW COLUMNS FROM usuarios')->fetchAll();
    $existing = [];
    foreach ($columns as $column) {
        $existing[$column['Field']] = true;
    }
    if (empty($existing['terminos_aceptados_at'])) {
        db()->exec('ALTER TABLE usuarios ADD COLUMN terminos_aceptados_at DATETIME NULL');
    }
    if (empty($existing['sms_marketing_aceptado_at'])) {
        db()->exec('ALTER TABLE usuarios ADD COLUMN sms_marketing_aceptado_at DATETIME NULL');
    }
}

function ensure_archive_table(): void {
    static $checked = false;
    if ($checked) return;
    $checked = true;
    ensure_report_columns();
    db()->exec("CREATE TABLE IF NOT EXISTS mascotas_archivadas (
        archive_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id CHAR(32) NOT NULL,
        reportado_por VARCHAR(10) NOT NULL,
        archivado_por VARCHAR(10) NULL,
        archivado_motivo VARCHAR(80) NOT NULL DEFAULT 'deleted_by_owner',
        tipo_reporte VARCHAR(30) NULL,
        tipo_mascota VARCHAR(40) NULL,
        nombre VARCHAR(160) NOT NULL,
        descripcion TEXT NULL,
        contacto VARCHAR(160) NULL,
        principal VARCHAR(500) NULL,
        secundarias JSON NULL,
        fecha VARCHAR(40) NULL,
        edad VARCHAR(120) NULL,
        raza VARCHAR(160) NULL,
        genero VARCHAR(80) NULL,
        color VARCHAR(120) NULL,
        collar VARCHAR(120) NULL,
        docil VARCHAR(120) NULL,
        direccion VARCHAR(500) NULL,
        direccion_completa VARCHAR(700) NULL,
        ubicacion_lat DECIMAL(9,6) NULL,
        ubicacion_lng DECIMAL(9,6) NULL,
        calles VARCHAR(240) NULL,
        dueno VARCHAR(160) NULL,
        recompensa VARCHAR(160) NULL,
        encontrado TINYINT(1) NOT NULL DEFAULT 0,
        vistas INT UNSIGNED NOT NULL DEFAULT 0,
        impulsado_hasta DATETIME NULL,
        paypal_order_id VARCHAR(255) NULL,
        paypal_payment_status VARCHAR(50) NULL,
        paypal_boost_days TINYINT UNSIGNED NULL,
        boost_expired_notified_at DATETIME NULL,
        creado_at TIMESTAMP NULL,
        actualizado_at TIMESTAMP NULL,
        archivado_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        snapshot_json JSON NULL,
        UNIQUE KEY uniq_archivadas_reporte (id),
        INDEX idx_archivadas_usuario (reportado_por),
        INDEX idx_archivadas_archivado_at (archivado_at),
        INDEX idx_archivadas_ubicacion (ubicacion_lat, ubicacion_lng)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    $columns = db()->query('SHOW COLUMNS FROM mascotas_archivadas')->fetchAll();
    $existing = [];
    foreach ($columns as $column) {
        $existing[$column['Field']] = true;
    }
    if (empty($existing['direccion_completa'])) {
        db()->exec('ALTER TABLE mascotas_archivadas ADD COLUMN direccion_completa VARCHAR(700) NULL AFTER direccion');
    }
    if (empty($existing['paypal_order_id'])) {
        db()->exec('ALTER TABLE mascotas_archivadas ADD COLUMN paypal_order_id VARCHAR(255) NULL AFTER impulsado_hasta');
    }
    if (empty($existing['paypal_payment_status'])) {
        db()->exec('ALTER TABLE mascotas_archivadas ADD COLUMN paypal_payment_status VARCHAR(50) NULL AFTER paypal_order_id');
    }
    if (empty($existing['paypal_boost_days'])) {
        db()->exec('ALTER TABLE mascotas_archivadas ADD COLUMN paypal_boost_days TINYINT UNSIGNED NULL AFTER paypal_payment_status');
    }
    $indexes = db()->query("SHOW INDEX FROM mascotas_archivadas WHERE Key_name = 'uniq_archivadas_reporte'")->fetchAll();
    if (!$indexes) {
        db()->exec('DELETE older FROM mascotas_archivadas older JOIN mascotas_archivadas newer ON older.id = newer.id AND older.archive_id < newer.archive_id');
        db()->exec('ALTER TABLE mascotas_archivadas ADD UNIQUE KEY uniq_archivadas_reporte (id)');
    }
}

function ensure_settings_table(): void {
    static $checked = false;
    if ($checked) return;
    $checked = true;
    db()->exec("CREATE TABLE IF NOT EXISTS app_settings (
        setting_key VARCHAR(80) NOT NULL PRIMARY KEY,
        setting_value TEXT NULL,
        actualizado_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
}

function app_setting(string $key): ?string {
    try {
        ensure_settings_table();
        $stmt = db()->prepare('SELECT setting_value FROM app_settings WHERE setting_key = ? LIMIT 1');
        $stmt->execute([$key]);
        $value = $stmt->fetchColumn();
        return $value === false ? null : (string)$value;
    } catch (Throwable $e) {
        error_log('No se pudo leer app_settings: ' . $e->getMessage());
        return null;
    }
}

function set_app_setting(string $key, string $value): void {
    ensure_settings_table();
    db()->prepare('INSERT INTO app_settings (setting_key, setting_value) VALUES (?, ?) ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)')
        ->execute([$key, $value]);
}

function e($value): string {
    return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
}

function money_display(?string $value): ?string {
    $raw = trim((string)$value);
    if ($raw === '') return null;
    $amount = preg_replace('/\D/', '', $raw);
    if ($amount === '' || (int)$amount <= 0) return null;
    return '$' . number_format((int)$amount, 0, '.', ',') . ' M.N.';
}

function reward_display(array $pet): ?string {
    if (report_type_value($pet['tipo_reporte'] ?? '') === 'resguardo') return null;
    return money_display($pet['recompensa'] ?? null) ?: 'Sin recompensa';
}

function is_boosted(array $pet): bool {
    $until = trim((string)($pet['impulsado_hasta'] ?? ''));
    return $until !== '' && strtotime($until) !== false && strtotime($until) > time();
}

function boosted_until_label(array $pet): ?string {
    if (!is_boosted($pet)) return null;
    $timestamp = strtotime((string)$pet['impulsado_hasta']);
    return $timestamp ? date('d/m/Y', $timestamp) : null;
}

function paypal_enabled(): bool {
    return (bool)(envv('PAYPAL_CLIENT_ID') && envv('PAYPAL_SECRET'));
}

function boost_button_enabled(): bool {
    $value = app_setting('boost_button_enabled');
    if ($value === null) $value = envv('BOOST_BUTTON_ENABLED', 'true');
    $value = lower_text(trim((string)$value));
    return !in_array($value, ['0', 'false', 'off', 'no'], true);
}

function donate_button_enabled(): bool {
    $value = app_setting('donate_button_enabled');
    if ($value === null) $value = envv('DONATE_BUTTON_ENABLED', 'true');
    $value = lower_text(trim((string)$value));
    return !in_array($value, ['0', 'false', 'off', 'no'], true);
}

function donation_modal_enabled(): bool {
    $value = app_setting('donation_modal_enabled');
    if ($value === null) $value = envv('DONATION_MODAL_ENABLED', 'true');
    $value = lower_text(trim((string)$value));
    return !in_array($value, ['0', 'false', 'off', 'no'], true);
}

function donation_url(): string {
    return envv('PAYPAL_DONATE_URL', DEFAULT_DONATION_URL) ?: DEFAULT_DONATION_URL;
}

function paypal_base_url(): string {
    return lower_text((string)envv('PAYPAL_MODE', 'live')) === 'sandbox'
        ? 'https://api-m.sandbox.paypal.com'
        : 'https://api-m.paypal.com';
}

function paypal_access_token(): string {
    $clientId = envv('PAYPAL_CLIENT_ID');
    $secret = envv('PAYPAL_SECRET');
    if (!$clientId || !$secret) throw new RuntimeException('Faltan PAYPAL_CLIENT_ID o PAYPAL_SECRET en el .env.');
    $ch = curl_init(paypal_base_url() . '/v1/oauth2/token');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => 'grant_type=client_credentials',
        CURLOPT_USERPWD => $clientId . ':' . $secret,
        CURLOPT_HTTPHEADER => ['Accept: application/json', 'Accept-Language: es_MX'],
        CURLOPT_TIMEOUT => 20,
    ]);
    $body = curl_exec($ch);
    $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    $json = json_decode((string)$body, true);
    if ($body === false || $status < 200 || $status >= 300 || empty($json['access_token'])) {
        $message = is_array($json) && isset($json['error_description']) ? $json['error_description'] : ($error ?: 'PayPal no pudo autenticar la solicitud.');
        throw new RuntimeException($message);
    }
    return (string)$json['access_token'];
}

function paypal_request(string $method, string $endpoint, array $payload = []): array {
    $ch = curl_init(paypal_base_url() . '/' . ltrim($endpoint, '/'));
    $headers = [
        'Authorization: Bearer ' . paypal_access_token(),
        'Content-Type: application/json',
        'PayPal-Request-Id: ' . bin2hex(random_bytes(16)),
    ];
    $options = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_TIMEOUT => 25,
    ];
    if ($payload) {
        $options[CURLOPT_POSTFIELDS] = json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    }
    curl_setopt_array($ch, $options);
    $body = curl_exec($ch);
    $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    $json = json_decode((string)$body, true);
    if ($body === false || $status < 200 || $status >= 300) {
        $message = is_array($json) && isset($json['message']) ? $json['message'] : ($error ?: 'PayPal no pudo procesar la solicitud.');
        throw new RuntimeException($message);
    }
    return is_array($json) ? $json : [];
}

function create_boost_checkout(array $pet, int $days = BOOST_DAYS): string {
    if (!boost_button_enabled()) throw new RuntimeException('El impulso automatico esta desactivado.');
    if (!paypal_enabled()) throw new RuntimeException('PayPal todavia no esta configurado.');
    $days = boost_plan_days($days);
    $plan = boost_plan($days);
    $days = (int)$plan['days'];
    $boostAmount = number_format(((int)$plan['price_cents']) / 100, 2, '.', '');
    $boostLabel = 'Impulsa tu anuncio por ' . $days . ' dias.';
    $boostImage = BOOST_PRODUCT_IMAGE_URL;
    $order = paypal_request('POST', 'v2/checkout/orders', [
        'intent' => 'CAPTURE',
        'purchase_units' => [[
            'reference_id' => $pet['id'],
            'custom_id' => $pet['id'] . ':' . $days,
            'description' => $boostLabel,
            'amount' => [
                'currency_code' => 'MXN',
                'value' => $boostAmount,
                'breakdown' => [
                    'item_total' => [
                        'currency_code' => 'MXN',
                        'value' => $boostAmount,
                    ],
                ],
            ],
            'items' => [[
                'name' => $boostLabel,
                'description' => $plan['name'] . ' para el reporte de ' . ($pet['nombre'] ?: 'mascota'),
                'image_url' => $boostImage,
                'quantity' => '1',
                'unit_amount' => [
                    'currency_code' => 'MXN',
                    'value' => $boostAmount,
                ],
                'category' => 'DIGITAL_GOODS',
            ]],
        ]],
        'payment_source' => [
            'paypal' => [
                'experience_context' => [
                    'brand_name' => 'AyudaPet',
                    'locale' => 'es-MX',
                    'landing_page' => 'LOGIN',
                    'shipping_preference' => 'NO_SHIPPING',
                    'user_action' => 'PAY_NOW',
                    'return_url' => full_url('/paypal/return?pet_id=' . urlencode($pet['id'])),
                    'cancel_url' => full_url('/paypal/cancel?pet_id=' . urlencode($pet['id'])),
                ],
            ],
        ],
    ]);
    $orderId = (string)($order['id'] ?? '');
    $approveUrl = '';
    foreach (($order['links'] ?? []) as $link) {
        if (in_array(($link['rel'] ?? ''), ['approve', 'payer-action'], true) && !empty($link['href'])) {
            $approveUrl = (string)$link['href'];
            break;
        }
    }
    if (!$orderId || !$approveUrl) throw new RuntimeException('PayPal no regreso una URL de aprobacion valida.');
    db()->prepare('UPDATE mascotas SET paypal_order_id = ?, paypal_payment_status = ?, paypal_boost_days = ? WHERE id = ?')
        ->execute([$orderId, (string)($order['status'] ?? 'CREATED'), $days, $pet['id']]);
    return $approveUrl;
}

function smtp_read($socket): string {
    $response = '';
    while (($line = fgets($socket, 515)) !== false) {
        $response .= $line;
        if (isset($line[3]) && $line[3] === ' ') break;
    }
    return $response;
}

function smtp_command($socket, string $command, array $expected): string {
    fwrite($socket, $command . "\r\n");
    $response = smtp_read($socket);
    $code = (int)substr($response, 0, 3);
    if (!in_array($code, $expected, true)) {
        throw new RuntimeException('SMTP error ' . trim($response));
    }
    return $response;
}

function mail_header_text(string $value): string {
    if (function_exists('mb_encode_mimeheader')) {
        return mb_encode_mimeheader($value, 'UTF-8');
    }
    return '=?UTF-8?B?' . base64_encode($value) . '?=';
}

function smtp_send_mail(string $to, string $subject, string $body, string $from, string $fromName): void {
    $host = envv('SMTP_HOST');
    $user = envv('SMTP_USER');
    $pass = envv('SMTP_PASS');
    if (!$host || !$user || !$pass) throw new RuntimeException('Faltan SMTP_HOST, SMTP_USER o SMTP_PASS.');
    $port = (int)envv('SMTP_PORT', '587');
    $secure = lower_text((string)envv('SMTP_SECURE', 'tls'));
    $remote = $secure === 'ssl' ? 'ssl://' . $host : $host;
    $socket = fsockopen($remote, $port, $errno, $errstr, 20);
    if (!$socket) throw new RuntimeException("SMTP conexion fallida: {$errstr}");
    stream_set_timeout($socket, 20);
    smtp_read($socket);
    smtp_command($socket, 'EHLO ' . APP_DOMAIN, [250]);
    if ($secure === 'tls') {
        smtp_command($socket, 'STARTTLS', [220]);
        if (!stream_socket_enable_crypto($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
            throw new RuntimeException('SMTP no pudo iniciar TLS.');
        }
        smtp_command($socket, 'EHLO ' . APP_DOMAIN, [250]);
    }
    smtp_command($socket, 'AUTH LOGIN', [334]);
    smtp_command($socket, base64_encode($user), [334]);
    smtp_command($socket, base64_encode($pass), [235]);
    smtp_command($socket, 'MAIL FROM:<' . $from . '>', [250]);
    smtp_command($socket, 'RCPT TO:<' . $to . '>', [250, 251]);
    smtp_command($socket, 'DATA', [354]);
    $headers = [
        'From: ' . mail_header_text($fromName) . ' <' . $from . '>',
        'To: <' . $to . '>',
        'Subject: ' . mail_header_text($subject),
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: 8bit',
    ];
    $message = implode("\r\n", $headers) . "\r\n\r\n" . str_replace(["\r\n", "\r"], "\n", $body);
    $message = str_replace("\n.", "\n..", $message);
    fwrite($socket, str_replace("\n", "\r\n", $message) . "\r\n.\r\n");
    $response = smtp_read($socket);
    $code = (int)substr($response, 0, 3);
    smtp_command($socket, 'QUIT', [221]);
    fclose($socket);
    if ($code !== 250) throw new RuntimeException('SMTP no acepto el mensaje: ' . trim($response));
}

function send_notification_email(string $subject, array $lines): array {
    $to = envv('BOOST_NOTIFY_EMAIL');
    if (!$to || !filter_var($to, FILTER_VALIDATE_EMAIL)) return [false, 'BOOST_NOTIFY_EMAIL no es valido o esta vacio.'];
    $from = envv('SMTP_FROM', envv('MAIL_FROM', 'no-reply@' . APP_DOMAIN));
    $fromName = envv('SMTP_FROM_NAME', 'AyudaPet');
    try {
        smtp_send_mail($to, $subject, implode("\n", $lines), $from, $fromName);
        return [true, 'Correo enviado por SMTP a ' . $to . '.'];
    } catch (Throwable $e) {
        error_log('No se pudo enviar correo SMTP de anuncio impulsado: ' . $e->getMessage());
        $headers = [
            'From: ' . $fromName . ' <' . $from . '>',
            'Reply-To: ' . $from,
            'Content-Type: text/plain; charset=UTF-8',
        ];
        if (mail($to, $subject, implode("\n", $lines), implode("\r\n", $headers))) {
            return [true, 'SMTP fallo, pero se envio con mail() de PHP a ' . $to . '. Error SMTP: ' . $e->getMessage()];
        }
        return [false, $e->getMessage()];
    }
}

function send_boost_notification(array $pet, string $paymentId, string $boostedUntil): void {
    $url = full_url('/mascotas/' . $pet['id']);
    [$sent, $message] = send_notification_email('Nuevo anuncio impulsado en AyudaPet', [
        'Se activo un anuncio impulsado en AyudaPet.',
        '',
        'Mascota: ' . ($pet['nombre'] ?? 'Sin nombre'),
        'Tipo de reporte: ' . report_type_label($pet['tipo_reporte'] ?? 'extravio'),
        'Telefono del usuario: ' . ($pet['reportado_por'] ?? ''),
        'Contacto publico: ' . public_contact_value($pet['contacto'] ?? null),
        'Direccion: ' . ($pet['direccion'] ?? ''),
        'Activo hasta: ' . $boostedUntil,
        'PayPal order: ' . $paymentId,
        '',
        'Ver reporte: ' . $url,
    ]);
    if (!$sent) error_log('Correo de anuncio impulsado no enviado: ' . $message);
}

function send_boost_expired_notification(array $pet): bool {
    $url = full_url('/mascotas/' . $pet['id']);
    [$sent, $message] = send_notification_email('Anuncio impulsado vencido en AyudaPet', [
        'Termino un anuncio impulsado en AyudaPet.',
        '',
        'Mascota: ' . ($pet['nombre'] ?? 'Sin nombre'),
        'Tipo de reporte: ' . report_type_label($pet['tipo_reporte'] ?? 'extravio'),
        'Telefono del usuario: ' . ($pet['reportado_por'] ?? ''),
        'Contacto publico: ' . public_contact_value($pet['contacto'] ?? null),
        'Direccion: ' . ($pet['direccion'] ?? ''),
        'Estuvo activo hasta: ' . ($pet['impulsado_hasta'] ?? ''),
        'PayPal order: ' . ($pet['paypal_order_id'] ?? ''),
        '',
        'Ver reporte: ' . $url,
    ]);
    if (!$sent) error_log('Correo de anuncio vencido no enviado: ' . $message);
    return $sent;
}

function process_expired_boosts(int $limit = 50): array {
    ensure_report_columns();
    $stmt = db()->prepare("SELECT * FROM mascotas WHERE impulsado_hasta IS NOT NULL AND impulsado_hasta <= NOW() AND paypal_payment_status IN ('COMPLETED', 'manual') AND boost_expired_notified_at IS NULL ORDER BY impulsado_hasta ASC LIMIT ?");
    $stmt->bindValue(1, max(1, min(100, $limit)), PDO::PARAM_INT);
    $stmt->execute();
    $pets = $stmt->fetchAll();
    $sent = 0;
    $failed = 0;
    foreach ($pets as $pet) {
        if (send_boost_expired_notification($pet)) {
            db()->prepare('UPDATE mascotas SET boost_expired_notified_at = NOW() WHERE id = ?')->execute([$pet['id']]);
            $sent++;
        } else {
            $failed++;
        }
    }
    return ['checked' => count($pets), 'sent' => $sent, 'failed' => $failed];
}

function activate_boost(string $petId, string $paymentId, string $provider = 'paypal', int $days = BOOST_DAYS): void {
    ensure_report_columns();
    $days = boost_plan_days($days, false);
    $pet = get_mascota($petId);
    if (!$pet) return;
    $alreadyNotified = is_boosted($pet) && (($pet['paypal_order_id'] ?? '') === $paymentId);
    db()->prepare('UPDATE mascotas SET impulsado_hasta = DATE_ADD(NOW(), INTERVAL ' . $days . ' DAY), paypal_order_id = ?, paypal_payment_status = ?, paypal_boost_days = ?, boost_expired_notified_at = NULL WHERE id = ?')
        ->execute([$paymentId, 'COMPLETED', $days, $petId]);
    if (!$alreadyNotified) {
        $updated = get_mascota($petId);
        send_boost_notification($updated ?: $pet, $paymentId, (string)(($updated['impulsado_hasta'] ?? null) ?: date('Y-m-d H:i:s', strtotime('+' . $days . ' days'))));
    }
}

function capture_paypal_boost(string $petId, string $orderId): bool {
    if (!paypal_enabled() || $orderId === '') return false;
    $pet = get_mascota($petId);
    if (!$pet || ($pet['paypal_order_id'] ?? '') !== $orderId) return false;
    $capture = paypal_request('POST', 'v2/checkout/orders/' . rawurlencode($orderId) . '/capture');
    if (($capture['status'] ?? '') !== 'COMPLETED') return false;
    $purchase = $capture['purchase_units'][0] ?? [];
    $customParts = explode(':', (string)($purchase['custom_id'] ?? ''), 2);
    $capturePetId = (string)($customParts[0] ?: ($purchase['reference_id'] ?? ''));
    if ($capturePetId !== $petId) return false;
    $days = boost_plan_days($pet['paypal_boost_days'] ?? ($customParts[1] ?? BOOST_DAYS), false);
    activate_boost($petId, $orderId, 'paypal', $days);
    return true;
}

function money_input_value(?string $value): string {
    $raw = trim((string)$value);
    if ($raw === '') return '';
    return preg_replace('/\D/', '', $raw) ?: '';
}

function age_display(?string $number, ?string $unit): ?string {
    $amount = (int)preg_replace('/\D/', '', (string)$number);
    if ($amount <= 0) return null;
    $unit = $unit === 'meses' ? 'meses' : 'anos';
    if ($unit === 'meses') return $amount . ' ' . ($amount === 1 ? 'mes' : 'meses');
    return $amount . ' ' . ($amount === 1 ? 'año' : 'años');
}

function age_input_parts(?string $value): array {
    $raw = lower_text(trim((string)$value));
    if ($raw === '') return ['', 'anos'];
    preg_match('/\d+/', $raw, $match);
    $amount = $match[0] ?? '';
    $unit = strpos($raw, 'mes') !== false ? 'meses' : 'anos';
    return [$amount, $unit];
}

function views_label($value): string {
    $count = max(0, (int)$value);
    return number_format($count, 0, '.', ',') . ' ' . ($count === 1 ? 'vista' : 'vistas');
}

function geo_value(?string $value, float $min, float $max): ?string {
    if ($value === null || trim($value) === '') return null;
    $number = (float)$value;
    if ($number < $min || $number > $max) return null;
    return number_format(round($number, 3), 3, '.', '');
}

function report_type_value(?string $value): string {
    return $value === 'resguardo' ? 'resguardo' : 'extravio';
}

function report_type_label(?string $value): string {
    return report_type_value($value) === 'resguardo' ? 'Resguardo' : 'Extravio';
}

function report_status_label(array $pet): string {
    $type = report_type_value($pet['tipo_reporte'] ?? '');
    $female = lower_text((string)($pet['genero'] ?? '')) === 'hembra';
    if (!empty($pet['encontrado'])) return 'En casa';
    return $type === 'resguardo' ? ($female ? 'Resguardada' : 'Resguardado') : ($female ? 'Perdida' : 'Perdido');
}

function report_status_class(array $pet): string {
    if (!empty($pet['encontrado'])) return 'found';
    return report_type_value($pet['tipo_reporte'] ?? '') === 'resguardo' ? 'rescue' : 'lost';
}

function path_only(): string {
    $path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
    return '/' . trim($path, '/');
}

function url(string $path = '/'): string {
    return $path === '/' ? '/' : '/' . ltrim($path, '/');
}

function full_url(string $path): string {
    return 'https://' . APP_DOMAIN . url($path);
}

function absolute_url(?string $value, string $fallback = '/'): string {
    $value = trim((string)$value);
    if ($value === '') return full_url($fallback);
    if (preg_match('#^https?://#i', $value)) return $value;
    if (starts_with($value, '//')) return 'https:' . $value;
    return full_url($value);
}

function meta_text(string $value, int $limit = 160): string {
    $value = trim(preg_replace('/\s+/', ' ', $value) ?? '');
    if (strlen($value) <= $limit) return $value;
    return rtrim(substr($value, 0, $limit - 1)) . '...';
}

function meta_image_info(string $url): array {
    $path = parse_url($url, PHP_URL_PATH);
    if (!$path) return [];
    $file = __DIR__ . '/' . ltrim($path, '/');
    if (!is_file($file)) return [];
    $info = @getimagesize($file);
    if (!$info) return [];
    return [
        'width' => (string)($info[0] ?? ''),
        'height' => (string)($info[1] ?? ''),
        'type' => (string)($info['mime'] ?? ''),
    ];
}

function local_public_path(?string $urlOrPath): ?string {
    $path = parse_url((string)$urlOrPath, PHP_URL_PATH);
    if (!$path) return null;
    $file = __DIR__ . '/' . ltrim($path, '/');
    $realBase = realpath(__DIR__);
    $realFile = is_file($file) ? realpath($file) : null;
    if (!$realBase || !$realFile || !starts_with($realFile, $realBase)) return null;
    return $realFile;
}

function orient_image_from_exif($image, string $source) {
    if (!function_exists('exif_read_data')) return $image;
    $info = @getimagesize($source);
    if (($info['mime'] ?? '') !== 'image/jpeg') return $image;
    $exif = @exif_read_data($source);
    $orientation = (int)($exif['Orientation'] ?? 1);
    if ($orientation === 3) return imagerotate($image, 180, 0) ?: $image;
    if ($orientation === 6) return imagerotate($image, -90, 0) ?: $image;
    if ($orientation === 8) return imagerotate($image, 90, 0) ?: $image;
    if ($orientation === 2 && function_exists('imageflip')) imageflip($image, IMG_FLIP_HORIZONTAL);
    if ($orientation === 4 && function_exists('imageflip')) imageflip($image, IMG_FLIP_VERTICAL);
    if ($orientation === 5 && function_exists('imageflip')) {
        imageflip($image, IMG_FLIP_HORIZONTAL);
        return imagerotate($image, 90, 0) ?: $image;
    }
    if ($orientation === 7 && function_exists('imageflip')) {
        imageflip($image, IMG_FLIP_HORIZONTAL);
        return imagerotate($image, -90, 0) ?: $image;
    }
    return $image;
}

function create_social_image(?string $sourceUrlOrPath, string $targetPublicPath): ?string {
    if (!function_exists('imagecreatefromstring') || !function_exists('imagejpeg')) return null;
    $source = local_public_path($sourceUrlOrPath);
    if (!$source || !is_readable($source)) return null;
    $target = __DIR__ . '/' . ltrim($targetPublicPath, '/');
    $dir = dirname($target);
    if (!is_dir($dir) && !mkdir($dir, 0755, true)) return null;
    $raw = @file_get_contents($source);
    if ($raw === false) return null;
    $image = @imagecreatefromstring($raw);
    if (!$image) return null;
    $oriented = orient_image_from_exif($image, $source);
    if ($oriented !== $image) {
        imagedestroy($image);
        $image = $oriented;
    }
    $canvasW = 1200;
    $canvasH = 630;
    $canvas = imagecreatetruecolor($canvasW, $canvasH);
    $white = imagecolorallocate($canvas, 255, 255, 255);
    imagefilledrectangle($canvas, 0, 0, $canvasW, $canvasH, $white);
    $srcW = imagesx($image);
    $srcH = imagesy($image);
    if ($srcW > 0 && $srcH > 0) {
        $scale = $canvasH / $srcH;
        $dstW = (int)round($srcW * $scale);
        $dstH = $canvasH;
        $dstX = (int)floor(($canvasW - $dstW) / 2);
        $dstY = (int)floor(($canvasH - $dstH) / 2);
        imagecopyresampled($canvas, $image, $dstX, $dstY, 0, 0, $dstW, $dstH, $srcW, $srcH);
    }
    $saved = imagejpeg($canvas, $target, 86);
    imagedestroy($image);
    imagedestroy($canvas);
    return $saved ? $targetPublicPath : null;
}

function pet_social_image(array $pet): string {
    $principal = trim((string)($pet['principal'] ?? ''));
    if ($principal === '') return full_url(DEFAULT_OG_IMAGE);
    $id = preg_replace('/[^a-f0-9]/i', '', (string)($pet['id'] ?? ''));
    if ($id) {
        $target = '/uploads/reportes/' . $id . '/og-' . PET_OG_VERSION . '.jpg';
        if (is_file(__DIR__ . $target) || create_social_image($principal, $target)) {
            return full_url($target);
        }
    }
    return absolute_url($principal, DEFAULT_OG_IMAGE);
}

function redirect_to(string $path): void {
    header('Location: ' . $path);
    exit;
}

function safe_next(?string $next): string {
    if (!$next || !starts_with($next, '/') || starts_with($next, '//')) {
        return '/';
    }
    return $next;
}

function flash(string $message, string $type = 'info'): void {
    $_SESSION['flash'][] = ['type' => $type, 'message' => $message];
}

function flashes(): array {
    $items = $_SESSION['flash'] ?? [];
    unset($_SESSION['flash']);
    return $items;
}

function current_user_phone(): ?string {
    return $_SESSION['tel'] ?? null;
}

function require_login(): void {
    if (!current_user_phone()) {
        flash('Inicia sesion para continuar.', 'warning');
        redirect_to('/login?next=' . urlencode($_SERVER['REQUEST_URI'] ?? '/'));
    }
}

function normalize_phone(?string $raw): ?string {
    $digits = preg_replace('/\D+/', '', $raw ?? '');
    if (starts_with($digits, '52') && strlen($digits) === 12) {
        $digits = substr($digits, 2);
    }
    return preg_match('/^[2-9][0-9]{9}$/', $digits) ? $digits : null;
}

function admin_phones(): array {
    $raw = envv('ADMIN_PHONES', envv('ADMIN_PHONE', DEFAULT_ADMIN_PHONE));
    $phones = [];
    foreach (preg_split('/[\s,;]+/', (string)$raw) as $phone) {
        $normalized = normalize_phone($phone);
        if ($normalized) $phones[] = $normalized;
    }
    return array_values(array_unique($phones));
}

function is_admin_user(): bool {
    $phone = current_user_phone();
    return $phone !== null && in_array($phone, admin_phones(), true);
}

function phone_digits(?string $raw): string {
    $digits = preg_replace('/\D+/', '', $raw ?? '');
    if (strlen($digits) === 12 && starts_with($digits, '52')) return substr($digits, 2);
    return $digits;
}

function phone_for_sms(?string $phone): string {
    $digits = preg_replace('/\D+/', '', $phone ?? '');
    $country = envv('LABSMOBILE_DEFAULT_COUNTRY_CODE', '52');
    return strlen($digits) === 10 && $country ? $country . $digits : $digits;
}

function whatsapp_digits(?string $phone): string {
    $digits = phone_digits($phone);
    return strlen($digits) === 10 ? phone_for_sms($digits) : $digits;
}

function public_contact_value(?string $contact): string {
    $normalized = normalize_phone($contact);
    $current = normalize_phone(DEFAULT_PUBLIC_CONTACT);
    $old = array_filter(array_map('normalize_phone', OLD_PUBLIC_CONTACTS));
    if (!$normalized || $normalized === $current || in_array($normalized, $old, true)) {
        return DEFAULT_PUBLIC_CONTACT;
    }
    return trim((string) $contact);
}

function is_system_public_contact(?string $contact): bool {
    return public_contact_value($contact) === DEFAULT_PUBLIC_CONTACT;
}

function post_value(string $name): ?string {
    $value = $_POST[$name] ?? null;
    if (!is_string($value)) return null;
    $value = trim($value);
    return $value === '' ? null : $value;
}

function send_sms(string $phone, string $code): bool {
    $api = envv('LABSMOBILE_API', 'https://api.labsmobile.com/json/send');
    $user = envv('LABSMOBILE_USER');
    $token = envv('LABSMOBILE_TOKEN');
    $sender = envv('LABSMOBILE_SENDER', 'AYUDAPET');
    if (!$api || !$user || !$token) {
        error_log('SMS no enviado: faltan variables de LabsMobile.');
        return false;
    }

    $payload = json_encode([
        'message' => "Tu codigo AyudaPet es {$code}. Expira en 5 minutos. ayudapet.com",
        'tpoa' => $sender,
        'recipient' => [['msisdn' => phone_for_sms($phone)]],
    ], JSON_UNESCAPED_SLASHES);

    $ch = curl_init($api);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $payload,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_USERPWD => $user . ':' . $token,
        CURLOPT_TIMEOUT => 12,
    ]);
    $body = curl_exec($ch);
    $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    if ($body === false || $status < 200 || $status >= 300) {
        error_log("LabsMobile error {$status}: {$error} {$body}");
        return false;
    }
    $json = json_decode((string)$body, true);
    $providerCode = (string)($json['code'] ?? '');
    if ($providerCode !== '' && !in_array($providerCode, ['0', '200', '201'], true)) {
        error_log("LabsMobile rechazo SMS: {$body}");
        return false;
    }
    return true;
}

function create_otp(string $phone): array {
    $code = str_pad((string)random_int(0, 999999), 6, '0', STR_PAD_LEFT);
    $expires = time() + (int)envv('OTP_TTL_SECONDS', '300');
    $stmt = db()->prepare(
        'INSERT INTO otps (telefono, code, expires)
         VALUES (?, ?, ?)
         ON DUPLICATE KEY UPDATE code = VALUES(code), expires = VALUES(expires)'
    );
    $stmt->execute([$phone, $code, $expires]);
    $sent = send_sms($phone, $code);
    return [$sent, envv('SHOW_OTP_IN_DEV') === 'true' ? $code : null];
}

function verify_otp(string $phone, string $code): bool {
    $stmt = db()->prepare('SELECT code, expires FROM otps WHERE telefono = ? LIMIT 1');
    $stmt->execute([$phone]);
    $otp = $stmt->fetch();
    if (!$otp) return false;
    $valid = (float)$otp['expires'] >= time() && hash_equals((string)$otp['code'], $code);
    if ($valid) {
        db()->prepare('DELETE FROM otps WHERE telefono = ?')->execute([$phone]);
    }
    return $valid;
}

function get_user(string $phone): ?array {
    ensure_user_columns();
    $stmt = db()->prepare('SELECT * FROM usuarios WHERE telefono = ? LIMIT 1');
    $stmt->execute([$phone]);
    return $stmt->fetch() ?: null;
}

function save_user(string $phone, string $password, ?string $name = null, bool $acceptedTerms = false, bool $acceptedSmsMarketing = false): void {
    ensure_user_columns();
    $hash = password_hash($password, PASSWORD_DEFAULT);
    if (get_user($phone)) {
        $stmt = db()->prepare('UPDATE usuarios SET password_hash = ?, nombre = COALESCE(?, nombre), activo = 1, terminos_aceptados_at = COALESCE(terminos_aceptados_at, ?), sms_marketing_aceptado_at = COALESCE(sms_marketing_aceptado_at, ?) WHERE telefono = ?');
        $stmt->execute([$hash, $name, $acceptedTerms ? date('Y-m-d H:i:s') : null, $acceptedSmsMarketing ? date('Y-m-d H:i:s') : null, $phone]);
        return;
    }
    $stmt = db()->prepare('INSERT INTO usuarios (telefono, creado, password_hash, nombre, activo, terminos_aceptados_at, sms_marketing_aceptado_at) VALUES (?, ?, ?, ?, 1, ?, ?)');
    $stmt->execute([$phone, time(), $hash, $name, $acceptedTerms ? date('Y-m-d H:i:s') : null, $acceptedSmsMarketing ? date('Y-m-d H:i:s') : null]);
}

function dedupe_reports(array $reports, int $limit = 2000): array {
    $clean = [];
    $seenIds = [];
    $seenKeys = [];
    foreach ($reports as $report) {
        $id = lower_text(trim((string)($report['id'] ?? '')));
        $name = lower_text(trim((string)($report['nombre'] ?? '')));
        $address = lower_text(trim((string)(($report['direccion_completa'] ?? '') ?: ($report['direccion'] ?? ''))));
        $image = trim((string)($report['principal'] ?? ''));
        $lat = round((float)($report['ubicacion_lat'] ?? 0), 4);
        $lng = round((float)($report['ubicacion_lng'] ?? 0), 4);
        $keys = [];
        if ($name !== '' && $image !== '') $keys[] = 'img|' . $name . '|' . $image;
        if ($name !== '' && $address !== '') $keys[] = 'addr|' . $name . '|' . $address;
        if ($name !== '' && ($lat || $lng)) $keys[] = 'geo|' . $name . '|' . $lat . '|' . $lng;
        if (!$keys) $keys[] = 'row|' . $id;
        $isDuplicate = $id !== '' && isset($seenIds[$id]);
        foreach ($keys as $key) {
            if (isset($seenKeys[$key])) {
                $isDuplicate = true;
                break;
            }
        }
        if ($isDuplicate) continue;
        if ($id !== '') $seenIds[$id] = true;
        foreach ($keys as $key) $seenKeys[$key] = true;
        $clean[] = $report;
        if (count($clean) >= $limit) break;
    }
    return $clean;
}

function recent_duplicate_report_id(array $data, string $phone, int $minutes = 5): ?string {
    ensure_report_columns();
    $name = lower_text(trim((string)($data['nombre'] ?? '')));
    $address = lower_text(trim((string)(($data['direccion_completa'] ?? '') ?: ($data['direccion'] ?? ''))));
    if ($phone === '' || $name === '' || $address === '') return null;
    $stmt = db()->prepare("SELECT id, nombre, direccion, direccion_completa, tipo_reporte, fecha
        FROM mascotas
        WHERE reportado_por = ?
          AND creado_at >= DATE_SUB(NOW(), INTERVAL ? MINUTE)
        ORDER BY creado_at DESC
        LIMIT 20");
    $stmt->execute([$phone, $minutes]);
    foreach ($stmt->fetchAll() as $report) {
        $sameName = lower_text(trim((string)($report['nombre'] ?? ''))) === $name;
        $sameType = report_type_value($report['tipo_reporte'] ?? '') === report_type_value($data['tipo_reporte'] ?? '');
        $sameDate = trim((string)($report['fecha'] ?? '')) === trim((string)($data['fecha'] ?? ''));
        $existingAddress = lower_text(trim((string)(($report['direccion_completa'] ?? '') ?: ($report['direccion'] ?? ''))));
        if ($sameName && $sameType && $sameDate && $existingAddress === $address) {
            return (string)$report['id'];
        }
    }
    return null;
}

function list_mascotas(): array {
    ensure_report_columns();
    $reports = db()->query("SELECT * FROM mascotas ORDER BY CASE WHEN impulsado_hasta IS NOT NULL AND impulsado_hasta > NOW() THEN 0 ELSE 1 END, creado_at DESC LIMIT 200")->fetchAll();
    return dedupe_reports($reports, 80);
}

function list_user_reports(string $phone): array {
    ensure_report_columns();
    $stmt = db()->prepare("SELECT * FROM mascotas WHERE reportado_por = ? ORDER BY CASE WHEN impulsado_hasta IS NOT NULL AND impulsado_hasta > NOW() THEN 0 ELSE 1 END, creado_at DESC");
    $stmt->execute([$phone]);
    return $stmt->fetchAll();
}

function get_mascota(string $id): ?array {
    ensure_report_columns();
    $stmt = db()->prepare('SELECT * FROM mascotas WHERE id = ? LIMIT 1');
    $stmt->execute([$id]);
    $pet = $stmt->fetch();
    return $pet ?: null;
}

function pet_short_code(array $pet): string {
    return substr((string)($pet['id'] ?? ''), 0, 8);
}

function get_mascota_by_short_code(string $code): ?array {
    if (!preg_match('/^[a-f0-9]{8,16}$/', $code)) return null;
    ensure_report_columns();
    $stmt = db()->prepare('SELECT * FROM mascotas WHERE id LIKE ? ORDER BY creado_at DESC LIMIT 2');
    $stmt->execute([$code . '%']);
    $pets = $stmt->fetchAll();
    return count($pets) === 1 ? $pets[0] : null;
}

function increment_report_views(string $id): void {
    ensure_report_columns();
    db()->prepare('UPDATE mascotas SET vistas = vistas + 1 WHERE id = ?')->execute([$id]);
}

function archive_report(array $pet, string $reason = 'deleted_by_owner'): void {
    ensure_archive_table();
    $fields = [
        'id', 'reportado_por', 'tipo_reporte', 'tipo_mascota', 'nombre', 'descripcion', 'contacto',
        'principal', 'secundarias', 'fecha', 'edad', 'raza', 'genero', 'color', 'collar', 'docil',
        'direccion', 'direccion_completa', 'ubicacion_lat', 'ubicacion_lng', 'calles', 'dueno', 'recompensa', 'encontrado',
        'vistas', 'impulsado_hasta', 'paypal_order_id', 'paypal_payment_status', 'paypal_boost_days',
        'boost_expired_notified_at', 'creado_at', 'actualizado_at'
    ];
    $columns = array_merge(['archivado_por', 'archivado_motivo'], $fields, ['snapshot_json']);
    $params = array_map(fn($column) => ':' . $column, $columns);
    $data = [
        'archivado_por' => current_user_phone(),
        'archivado_motivo' => $reason,
        'snapshot_json' => json_encode($pet, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
    ];
    foreach ($fields as $field) {
        $data[$field] = $pet[$field] ?? null;
    }
    $updates = [];
    foreach (array_diff($columns, ['id']) as $column) {
        $updates[] = "{$column} = VALUES({$column})";
    }
    $updates[] = 'archivado_at = CURRENT_TIMESTAMP';
    $sql = 'INSERT INTO mascotas_archivadas (' . implode(', ', $columns) . ') VALUES (' . implode(', ', $params) . ')
            ON DUPLICATE KEY UPDATE ' . implode(', ', $updates);
    db()->prepare($sql)->execute($data);
}

function sync_report_archives(int $limit = 500): array {
    ensure_archive_table();
    $stmt = db()->prepare('SELECT * FROM mascotas ORDER BY creado_at DESC LIMIT ?');
    $stmt->bindValue(1, max(1, min(2000, $limit)), PDO::PARAM_INT);
    $stmt->execute();
    $pets = $stmt->fetchAll();
    $synced = 0;
    $failed = 0;
    foreach ($pets as $pet) {
        try {
            archive_report($pet, 'cron_snapshot');
            $synced++;
        } catch (Throwable $e) {
            $failed++;
            error_log('No se pudo sincronizar el archivo del reporte ' . ($pet['id'] ?? '') . ': ' . $e->getMessage());
        }
    }
    return ['checked' => count($pets), 'synced' => $synced, 'failed' => $failed];
}

function backfill_missing_report_coordinates(int $limit = 25): void {
    if (!envv('API_KEY')) return;
    ensure_report_columns();
    $stmt = db()->prepare("SELECT id, direccion, direccion_completa FROM mascotas
        WHERE (ubicacion_lat IS NULL OR ubicacion_lng IS NULL)
          AND direccion IS NOT NULL AND direccion <> ''
        ORDER BY actualizado_at DESC
        LIMIT ?");
    $stmt->bindValue(1, $limit, PDO::PARAM_INT);
    $stmt->execute();
    foreach ($stmt->fetchAll() as $pet) {
        try {
            $geo = google_geocode_area((string)(($pet['direccion_completa'] ?? '') ?: ($pet['direccion'] ?? '')));
            if (!$geo) continue;
            db()->prepare('UPDATE mascotas SET ubicacion_lat = ?, ubicacion_lng = ?, direccion_completa = COALESCE(NULLIF(direccion_completa, \'\'), ?) WHERE id = ?')
                ->execute([
                    round((float)$geo['lat'], 6),
                    round((float)$geo['lng'], 6),
                    $geo['label'] ?? null,
                    $pet['id'],
                ]);
        } catch (Throwable $e) {
            error_log('No se pudo completar coordenadas para reporte ' . ($pet['id'] ?? '') . ': ' . $e->getMessage());
        }
    }
}

function heatmap_reports(): array {
    ensure_report_columns();
    ensure_archive_table();
    backfill_missing_report_coordinates();
    $stmt = db()->query("SELECT * FROM (
            SELECT id, nombre, tipo_reporte, tipo_mascota, direccion, direccion_completa, principal, ubicacion_lat, ubicacion_lng, encontrado, creado_at, actualizado_at AS orden_at, NULL AS archivado_at, 0 AS source_order
            FROM mascotas
            WHERE ubicacion_lat IS NOT NULL AND ubicacion_lng IS NOT NULL
            UNION ALL
            SELECT id, nombre, tipo_reporte, tipo_mascota, direccion, direccion_completa, principal, ubicacion_lat, ubicacion_lng, encontrado, creado_at, archivado_at AS orden_at, archivado_at, 1 AS source_order
            FROM mascotas_archivadas
            WHERE ubicacion_lat IS NOT NULL AND ubicacion_lng IS NOT NULL
        ) ubicaciones
        ORDER BY source_order ASC, orden_at DESC
        LIMIT 4000");
    $reports = dedupe_reports($stmt->fetchAll(), 2000);
    $stats = ['total' => count($reports), 'extravio' => 0, 'resguardo' => 0, 'en_casa' => 0];
    foreach ($reports as $report) {
        $type = report_type_value($report['tipo_reporte'] ?? '');
        if ($type === 'resguardo') $stats['resguardo']++;
        else $stats['extravio']++;
        if (!empty($report['encontrado'])) $stats['en_casa']++;
    }
    return ['reports' => $reports, 'stats' => $stats];
}

function google_geocode_area(string $query): ?array {
    $key = envv('API_KEY');
    if (!$key || trim($query) === '' || !function_exists('curl_init')) return null;
    $url = 'https://maps.googleapis.com/maps/api/geocode/json?' . http_build_query([
        'address' => $query . ', Mexico',
        'components' => 'country:MX',
        'key' => $key,
    ]);
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 8,
    ]);
    $body = curl_exec($ch);
    $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);
    if ($body === false || $status < 200 || $status >= 300) return null;
    $data = json_decode((string)$body, true);
    $result = $data['results'][0] ?? null;
    $location = $result['geometry']['location'] ?? null;
    if (($data['status'] ?? '') !== 'OK' || !$location || !isset($location['lat'], $location['lng'])) return null;
    $types = $result['types'] ?? [];
    $radius = 45;
    if (in_array('administrative_area_level_1', $types, true)) $radius = 360;
    elseif (in_array('administrative_area_level_2', $types, true)) $radius = 120;
    elseif (in_array('postal_code', $types, true) || in_array('neighborhood', $types, true)) $radius = 18;
    return [
        'lat' => (float)$location['lat'],
        'lng' => (float)$location['lng'],
        'radius_km' => $radius,
        'label' => (string)($result['formatted_address'] ?? $query),
    ];
}

function address_looks_exact(?string $address): bool {
    $address = lower_text(trim((string)$address));
    if ($address === '') return false;
    $firstPart = trim(explode(',', $address)[0] ?? $address);
    return (bool)preg_match('/\d|\b(c\.?|calle|av\.?|avenida|blvd\.?|boulevard|privada|priv\.?|calz\.?|calzada|cerrada|cda\.?|camino|carretera|prolongacion|prol\.?)\b/u', $firstPart);
}

function public_area_address(?string $address): ?string {
    $address = trim((string)$address);
    if ($address === '') return null;

    $parts = array_values(array_filter(array_map('trim', explode(',', $address)), fn($part) => $part !== ''));
    if (count($parts) > 1 && address_looks_exact($parts[0])) {
        array_shift($parts);
        $protected = trim(implode(', ', $parts));
        return $protected !== '' ? $protected : $address;
    }

    if (address_looks_exact($address)) {
        if (preg_match('/\b(col\.?|colonia|fracc\.?|fraccionamiento|residencial|unidad|barrio)\b\s*(.+)$/iu', $address, $matches)) {
            $protected = trim($matches[0]);
            return $protected !== '' ? $protected : 'Zona no especificada';
        }
        return 'Zona no especificada';
    }

    return $address;
}

function contact_rows_to_sms(array $rows): array {
    $seen = [];
    $contacts = [];
    $excluded = array_filter(array_merge([normalize_phone(DEFAULT_PUBLIC_CONTACT)], array_map('normalize_phone', OLD_PUBLIC_CONTACTS)));
    foreach ($rows as $row) {
        foreach ([$row['reportado_por'] ?? null, $row['contacto'] ?? null] as $rawPhone) {
            $phone = normalize_phone($rawPhone);
            if (!$phone || isset($seen[$phone]) || in_array($phone, $excluded, true)) continue;
            $seen[$phone] = true;
            $contacts[] = [
                'phone' => $phone,
                'sms' => phone_for_sms($phone),
                'direccion' => (string)(($row['direccion_completa'] ?? '') ?: ($row['direccion'] ?? '')),
                'reportes' => (int)($row['reportes'] ?? 0),
            ];
        }
    }
    return $contacts;
}

function location_term_aliases(string $term): array {
    $aliases = [
        'chihuahua' => ['chihuahua', 'chih'],
        'chih' => ['chih', 'chihuahua'],
        'tamaulipas' => ['tamaulipas', 'tamps'],
        'tamps' => ['tamps', 'tamaulipas'],
        'nuevo' => ['nuevo'],
        'leon' => ['leon'],
        'nuevo leon' => ['nuevo leon', 'nl', 'n l'],
        'coahuila' => ['coahuila', 'coah'],
        'sonora' => ['sonora', 'son'],
        'durango' => ['durango', 'dgo'],
        'sinaloa' => ['sinaloa', 'sin'],
        'jalisco' => ['jalisco', 'jal'],
    ];
    return array_values(array_unique($aliases[$term] ?? [$term]));
}

function heatmap_city_contacts(?string $city): array {
    ensure_archive_table();
    $city = trim((string)$city);
    if ($city === '') return ['city' => '', 'contacts' => [], 'sms' => '', 'source' => ''];
    $terms = preg_split('/\s+/', preg_replace('/[^\p{L}\p{N}]+/u', ' ', lower_text($city)) ?: '', -1, PREG_SPLIT_NO_EMPTY);
    $terms = array_values(array_filter($terms, fn($term) => !in_array($term, ['cd', 'ciudad', 'mx', 'mexico'], true)));
    if (!$terms) $terms = [$city];
    $postalCode = preg_match('/\b\d{5}\b/', $city, $m) ? $m[0] : null;
    if ($postalCode) $terms = [$postalCode];
    $groups = [];
    $params = [];
    foreach ($terms as $term) {
        $parts = [];
        foreach (location_term_aliases($term) as $alias) {
            $parts[] = '(direccion LIKE ? OR direccion_completa LIKE ?)';
            $params[] = '%' . $alias . '%';
            $params[] = '%' . $alias . '%';
        }
        $groups[] = '(' . implode(' OR ', $parts) . ')';
    }
    $where = implode(' AND ', $groups);
    $stmt = db()->prepare("SELECT reportado_por, contacto, direccion, direccion_completa, COUNT(*) AS reportes, MAX(archivado_at) AS ultimo
        FROM mascotas_archivadas
        WHERE {$where}
        GROUP BY reportado_por, contacto, direccion, direccion_completa
        ORDER BY ultimo DESC
        LIMIT 600");
    $stmt->execute($params);
    $contacts = contact_rows_to_sms($stmt->fetchAll());
    $source = 'texto';
    if (!$contacts && ($area = google_geocode_area($city))) {
        $stmt = db()->prepare("SELECT reportado_por, contacto, direccion, direccion_completa, COUNT(*) AS reportes, MAX(archivado_at) AS ultimo,
            (6371 * ACOS(LEAST(1, GREATEST(-1, COS(RADIANS(?)) * COS(RADIANS(ubicacion_lat)) * COS(RADIANS(ubicacion_lng) - RADIANS(?)) + SIN(RADIANS(?)) * SIN(RADIANS(ubicacion_lat)))))) AS distance_km
            FROM mascotas_archivadas
            WHERE ubicacion_lat IS NOT NULL AND ubicacion_lng IS NOT NULL
            GROUP BY reportado_por, contacto, direccion, direccion_completa, ubicacion_lat, ubicacion_lng
            HAVING distance_km <= ?
            ORDER BY distance_km ASC
            LIMIT 600");
        $stmt->execute([$area['lat'], $area['lng'], $area['lat'], $area['radius_km']]);
        $contacts = contact_rows_to_sms($stmt->fetchAll());
        $source = 'coordenadas: ' . $area['label'] . ' (' . $area['radius_km'] . ' km)';
    }
    return [
        'city' => $city,
        'contacts' => $contacts,
        'sms' => implode("\n", array_column($contacts, 'sms')),
        'source' => $source,
    ];
}

function pet_secondaries(array $pet): array {
    $items = json_decode((string)($pet['secundarias'] ?? '[]'), true);
    return is_array($items) ? array_values(array_filter($items, 'is_string')) : [];
}

function owns_report(?array $pet): bool {
    return $pet && current_user_phone() && $pet['reportado_por'] === current_user_phone();
}

function can_manage_report(?array $pet): bool {
    return owns_report($pet) || ($pet && is_admin_user());
}

function upload_image(array $file, string $reportId, string $label): ?string {
    if (($file['error'] ?? UPLOAD_ERR_NO_FILE) === UPLOAD_ERR_NO_FILE) return null;
    if (($file['error'] ?? UPLOAD_ERR_OK) !== UPLOAD_ERR_OK) {
        throw new RuntimeException('No se pudo subir la imagen.');
    }
    $allowed = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp', 'image/gif' => 'gif'];
    $mime = mime_content_type($file['tmp_name']) ?: '';
    if (!isset($allowed[$mime])) {
        throw new RuntimeException('Solo puedes subir imagenes JPG, PNG, WEBP o GIF.');
    }
    $dir = __DIR__ . '/uploads/reportes/' . $reportId;
    if (!is_dir($dir) && !mkdir($dir, 0775, true) && !is_dir($dir)) {
        throw new RuntimeException('No se pudo preparar la carpeta de imagenes.');
    }
    $name = $label . '-' . bin2hex(random_bytes(12)) . '.' . $allowed[$mime];
    $target = $dir . '/' . $name;
    if (!move_uploaded_file($file['tmp_name'], $target)) {
        throw new RuntimeException('No se pudo guardar la imagen.');
    }
    $publicPath = '/uploads/reportes/' . $reportId . '/' . $name;
    if ($label === 'principal') create_social_image($publicPath, '/uploads/reportes/' . $reportId . '/og-' . PET_OG_VERSION . '.jpg');
    return $publicPath;
}

function report_payload(string $id, ?array $existing = null): array {
    $existing = $existing ?? [];
    $reportType = report_type_value(post_value('tipo_reporte') ?: ($existing['tipo_reporte'] ?? 'extravio'));
    $name = post_value('nombre');
    if (!$name && $reportType === 'extravio') throw new RuntimeException('El nombre de la mascota es obligatorio.');
    if (!$name) $name = 'Sin nombre';
    $contacto = isset($_POST['usar_contacto_propio']) ? post_value('contacto') : null;
    $direccion = post_value('direccion');
    $direccionCompleta = post_value('direccion_completa');
    if (!$direccionCompleta && $direccion && $direccion === ($existing['direccion'] ?? null)) {
        $direccionCompleta = $existing['direccion_completa'] ?? null;
    }
    if (!$direccionCompleta && address_looks_exact($direccion)) {
        $direccionCompleta = $direccion;
    }
    $ubicacionLat = geo_value(post_value('ubicacion_lat'), -90, 90);
    $ubicacionLng = geo_value(post_value('ubicacion_lng'), -180, 180);
    if (($ubicacionLat === null || $ubicacionLng === null) && $direccion) {
        $geo = google_geocode_area($direccionCompleta ?: $direccion);
        if ($geo) {
            $ubicacionLat = round((float)$geo['lat'], 6);
            $ubicacionLng = round((float)$geo['lng'], 6);
            if (!$direccionCompleta || address_looks_exact($direccionCompleta)) {
                $direccionCompleta = $geo['label'] ?? $direccionCompleta;
            }
        }
    }
    $direccion = public_area_address($direccionCompleta ?: $direccion);

    $principal = !empty($_POST['remove_principal']) ? null : ($existing['principal'] ?? null);
    if (isset($_FILES['principal'])) {
        $principal = upload_image($_FILES['principal'], $id, 'principal') ?: $principal;
    }

    $secondaries = $existing ? pet_secondaries($existing) : [];
    $remove = $_POST['remove_secundarias'] ?? [];
    if (is_array($remove)) {
        $secondaries = array_values(array_filter($secondaries, function ($img) use ($remove) {
            return !in_array($img, $remove, true);
        }));
    }

    $files = $_FILES['secundarias'] ?? null;
    $incoming = [];
    if ($files && is_array($files['name'])) {
        foreach ($files['name'] as $i => $nameFile) {
            if (!$nameFile) continue;
            $incoming[] = [
                'name' => $files['name'][$i],
                'type' => $files['type'][$i],
                'tmp_name' => $files['tmp_name'][$i],
                'error' => $files['error'][$i],
                'size' => $files['size'][$i],
            ];
        }
    }
    if (count($secondaries) + count($incoming) > MAX_SECONDARY_IMAGES) {
        throw new RuntimeException('Solo puedes tener hasta 3 fotos adicionales.');
    }
    foreach ($incoming as $i => $file) {
        $uploaded = upload_image($file, $id, 'secundaria-' . ($i + 1));
        if ($uploaded) $secondaries[] = $uploaded;
    }

    return [
        'tipo_reporte' => $reportType,
        'tipo_mascota' => post_value('tipo_mascota'),
        'nombre' => $name,
        'descripcion' => post_value('descripcion'),
        'contacto' => $contacto ?: DEFAULT_PUBLIC_CONTACT,
        'principal' => $principal,
        'secundarias' => json_encode($secondaries, JSON_UNESCAPED_SLASHES),
        'fecha' => post_value('fecha'),
        'edad' => age_display(post_value('edad_numero'), post_value('edad_unidad')),
        'raza' => post_value('raza'),
        'genero' => post_value('genero'),
        'color' => post_value('color'),
        'collar' => post_value('collar'),
        'docil' => post_value('docil'),
        'direccion' => $direccion,
        'direccion_completa' => $direccionCompleta,
        'ubicacion_lat' => $ubicacionLat,
        'ubicacion_lng' => $ubicacionLng,
        'calles' => null,
        'dueno' => null,
        'recompensa' => $reportType === 'resguardo' ? null : money_display(post_value('recompensa')),
        'encontrado' => isset($_POST['encontrado']) ? 1 : 0,
    ];
}

function create_report(): string {
    ensure_report_columns();
    $id = bin2hex(random_bytes(16));
    $data = report_payload($id);
    $duplicateId = recent_duplicate_report_id($data, (string)current_user_phone());
    if ($duplicateId) {
        save_report_data($duplicateId, (string)current_user_phone(), $data);
        try {
            $pet = get_mascota($duplicateId);
            if ($pet) archive_report($pet, 'updated_duplicate_snapshot');
        } catch (Throwable $e) {
            error_log('No se pudo actualizar el archivo del reporte duplicado ' . $duplicateId . ': ' . $e->getMessage());
        }
        return $duplicateId;
    }
    $sql = 'INSERT INTO mascotas (id, reportado_por, tipo_reporte, tipo_mascota, nombre, descripcion, contacto, principal, secundarias, fecha, edad, raza, genero, color, collar, docil, direccion, direccion_completa, ubicacion_lat, ubicacion_lng, calles, dueno, recompensa, encontrado)
            VALUES (:id, :reportado_por, :tipo_reporte, :tipo_mascota, :nombre, :descripcion, :contacto, :principal, :secundarias, :fecha, :edad, :raza, :genero, :color, :collar, :docil, :direccion, :direccion_completa, :ubicacion_lat, :ubicacion_lng, :calles, :dueno, :recompensa, :encontrado)';
    $stmt = db()->prepare($sql);
    $stmt->execute(['id' => $id, 'reportado_por' => current_user_phone()] + $data);
    try {
        $pet = get_mascota($id);
        if ($pet) archive_report($pet, 'created_snapshot');
    } catch (Throwable $e) {
        error_log('No se pudo archivar el reporte creado ' . $id . ': ' . $e->getMessage());
    }
    return $id;
}

function save_report_data(string $id, string $owner, array $data): void {
    $sets = [];
    foreach ($data as $key => $_) $sets[] = "{$key} = :{$key}";
    $stmt = db()->prepare('UPDATE mascotas SET ' . implode(', ', $sets) . ' WHERE id = :id AND reportado_por = :reportado_por');
    $stmt->execute($data + ['id' => $id, 'reportado_por' => $owner]);
}

function update_report(string $id, array $existing): void {
    ensure_report_columns();
    $data = report_payload($id, $existing);
    save_report_data($id, (string)$existing['reportado_por'], $data);
    try {
        $pet = get_mascota($id);
        if ($pet) archive_report($pet, 'updated_snapshot');
    } catch (Throwable $e) {
        error_log('No se pudo actualizar el archivo del reporte ' . $id . ': ' . $e->getMessage());
    }
}

function remove_report_image(string $id, array $pet, string $target, ?string $image): void {
    if ($target === 'principal') {
        db()->prepare('UPDATE mascotas SET principal = NULL WHERE id = ? AND reportado_por = ?')->execute([$id, $pet['reportado_por']]);
        return;
    }
    if ($target === 'secundaria' && $image) {
        $secondaries = array_values(array_filter(pet_secondaries($pet), function ($img) use ($image) {
            return $img !== $image;
        }));
        db()->prepare('UPDATE mascotas SET secundarias = ? WHERE id = ? AND reportado_por = ?')->execute([json_encode($secondaries), $id, $pet['reportado_por']]);
        return;
    }
    throw new RuntimeException('Imagen invalida.');
}

function render(string $view, array $data = [], int $status = 200): void {
    http_response_code($status);
    extract($data, EXTR_SKIP);
    $currentUser = current_user_phone();
    $year = date('Y');
    $title = $title ?? APP_NAME;
    $metaTitle = $metaTitle ?? $title;
    $metaDescription = meta_text($metaDescription ?? 'AyudaPet conecta reportes de mascotas perdidas y localizadas para que vuelvan a casa mas rapido.');
    $metaUrl = absolute_url($metaUrl ?? '/', '/');
    $canonicalUrl = absolute_url($canonicalUrl ?? $metaUrl, '/');
    $metaImage = absolute_url($metaImage ?? DEFAULT_OG_IMAGE, DEFAULT_OG_IMAGE);
    $metaImageAlt = meta_text($metaImageAlt ?? $metaTitle, 120);
    $metaImageInfo = meta_image_info($metaImage);
    $ogType = $ogType ?? 'website';
    $active = function (string $path): string {
        return path_only() === $path ? 'active' : '';
    };
    ?>
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><?= e($title) ?></title>
  <meta name="description" content="<?= e($metaDescription) ?>">
  <link rel="canonical" href="<?= e($canonicalUrl) ?>">
  <meta property="og:type" content="<?= e($ogType) ?>">
  <meta property="og:locale" content="es_MX">
  <meta property="og:site_name" content="AyudaPet">
  <meta property="og:title" content="<?= e($metaTitle) ?>">
  <meta property="og:description" content="<?= e($metaDescription) ?>">
  <meta property="og:url" content="<?= e($metaUrl) ?>">
  <meta property="og:image" content="<?= e($metaImage) ?>">
  <meta property="og:image:url" content="<?= e($metaImage) ?>">
  <meta property="og:image:secure_url" content="<?= e($metaImage) ?>">
  <meta property="og:image:alt" content="<?= e($metaImageAlt) ?>">
  <?php if (!empty($metaImageInfo['width']) && !empty($metaImageInfo['height'])): ?><meta property="og:image:width" content="<?= e($metaImageInfo['width']) ?>">
  <meta property="og:image:height" content="<?= e($metaImageInfo['height']) ?>"><?php endif; ?>
  <?php if (!empty($metaImageInfo['type'])): ?><meta property="og:image:type" content="<?= e($metaImageInfo['type']) ?>"><?php endif; ?>
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:url" content="<?= e($metaUrl) ?>">
  <meta name="twitter:title" content="<?= e($metaTitle) ?>">
  <meta name="twitter:description" content="<?= e($metaDescription) ?>">
  <meta name="twitter:image" content="<?= e($metaImage) ?>">
  <meta name="twitter:image:alt" content="<?= e($metaImageAlt) ?>">
  <meta itemprop="image" content="<?= e($metaImage) ?>">
  <link rel="icon" type="image/png" href="/static/logo.png">
  <link rel="apple-touch-icon" href="/static/logo.png">
  <style><?= css() ?></style>
  <style>.switch input{width:1px!important;height:1px!important;min-width:0!important;min-height:0!important;padding:0!important;margin:0!important;border:0!important}.switch input:checked~.switch-ui{background:var(--green)}.switch input:checked~.switch-ui:before{transform:translateX(22px)}.switch-text{min-width:0;overflow-wrap:anywhere}.menu-setting{margin:0}.menu-setting .switch{min-height:58px}.inline-fields{display:grid;grid-template-columns:88px minmax(0,132px);gap:8px;align-items:center}.inline-fields select,.inline-fields input{min-width:0}.pet-body{padding-right:20px}.btn.facebook{background:#1877f2;color:#fff;border-color:#1877f2}.btn.facebook:hover{background:#145dbd}.btn.donate{background:#22607a;color:#fff;border-color:#22607a}.btn.donate:hover{background:#18475c}.btn.boost{background:#f6a623;color:#18212f;border-color:#f6a623}.btn.boost:hover{background:#e99612}.badge.rescue{background:#fff8e8;color:var(--amber)}.boost-badge{width:max-content;background:#fff4d8;color:#8a570b}.pet-card.boosted{border-color:#f0c56f;box-shadow:0 16px 42px rgba(164,102,20,.16)}.boost-panel,.boost-copy{margin-bottom:16px;padding:14px;border:1px solid #f0c56f;border-radius:8px;background:#fffaf0}.boost-panel{display:flex;align-items:center;gap:10px;flex-wrap:wrap;min-width:0;max-width:100%}.boost-panel>*{min-width:0}.boost-panel .switch{width:100%;min-width:0}.boost-panel strong{overflow-wrap:anywhere}.admin-views-panel{align-items:end}.admin-views-panel .field{flex:1;min-width:150px}.admin-views-panel .btn{min-height:44px}.boost-copy h2{margin:0 0 8px;font-size:1.15rem}.boost-copy p{margin:0 0 10px;color:var(--muted);line-height:1.5}.filter-dropdown{position:relative}.filter-dropdown summary{list-style:none;display:flex;align-items:center;justify-content:space-between;gap:14px;padding-right:32px;cursor:pointer;font-weight:900}.filter-dropdown summary::-webkit-details-marker{display:none}.filter-dropdown summary:after{content:"+";position:absolute;top:0;right:0;color:var(--muted);font-size:1.25rem;line-height:1}.filter-dropdown[open] summary:after{content:"-"}.filter-dropdown .search-form{margin-top:16px}.modal-page{min-height:calc(100vh - 170px);display:grid;place-items:center;padding:clamp(16px,4vw,34px)}.report-type-modal{width:min(680px,100%);padding:clamp(20px,4vw,34px)}.report-type-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:20px}.report-type-option{display:grid;gap:8px;padding:18px;border:1px solid var(--line);border-radius:8px;background:#fbfdff}.report-type-option:hover{border-color:var(--brand);box-shadow:0 12px 28px rgba(20,32,48,.08)}.report-type-option strong{font-size:1.05rem}.report-type-option span{color:var(--muted);line-height:1.45}.donation-modal{position:fixed;inset:0;z-index:90;display:none;place-items:center;padding:18px;background:rgba(10,16,24,.48)}.donation-modal.open{display:grid}.donation-dialog{position:relative;width:min(460px,100%);padding:24px;border:1px solid var(--line);border-radius:8px;background:#fff;box-shadow:0 24px 80px rgba(20,32,48,.22)}.donation-close{position:absolute;top:10px;right:10px;width:40px;height:40px;padding:0;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--muted);font-size:1.35rem;line-height:1;box-shadow:0 8px 22px rgba(20,32,48,.12)}.donation-close:hover{color:var(--ink);border-color:#cfd7e3}.donation-dialog h2{margin:0;font-size:1.6rem}.donation-dialog p:not(.eyebrow){color:var(--muted);line-height:1.55}.detail-media .views-badge,.detail-media .photo-badge{top:10px;min-width:86px;min-height:28px;padding:0 10px;font-size:.78rem;line-height:1;align-items:center;justify-content:center;text-align:center}.views-badge{position:absolute;left:10px;box-shadow:0 10px 24px rgba(20,32,48,.16);background:rgba(255,255,255,.94);color:var(--ink)}@media(max-width:640px){.report-type-actions{grid-template-columns:1fr}}@media(max-width:420px){.pet-body{padding-right:12px}.filter-dropdown summary{align-items:flex-start;flex-direction:column}.detail-media .views-badge,.detail-media .photo-badge{top:7px;min-width:80px;min-height:24px;padding:0 8px;font-size:.68rem}.views-badge{left:7px}}</style>
  <style>.btn{font-size:.92rem;line-height:1}.btn.logout,.btn.back-report{background:#b93824;color:#fff;border-color:#b93824}.btn.logout:hover,.btn.back-report:hover{background:#922b1b}.btn.call{background:#0d83f2;color:#fff;border-color:#0d83f2}.btn.call:hover{background:#096dce}.btn.whatsapp{background:#128C7E;color:#fff;border-color:#128C7E}.btn.whatsapp:hover{background:#0f766b}.btn.share{background:#25d366;color:#fff;border-color:#25d366}.btn.share:hover{background:#20b858}.detail-owner-actions{display:flex;justify-content:flex-end;gap:10px;margin:0 0 14px}.detail-owner-actions form{display:flex;margin:0}.detail-owner-actions .btn{min-height:38px;padding:0 14px;border:1px solid var(--line);color:#fff}.detail-owner-actions .btn.edit{background:#176b87;border-color:#176b87}.detail-owner-actions .btn.edit:hover{background:#10546c}.detail-owner-actions .btn.delete{background:#b93824;border-color:#b93824}.detail-owner-actions .btn.delete:hover{background:#922b1b}.boost-copy{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:16px;padding:16px 18px}.boost-copy form{margin:0}.boost-copy .btn.boost{min-width:190px;min-height:48px;box-shadow:0 12px 28px rgba(246,166,35,.22)}@media(max-width:840px){.detail-owner-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.detail-owner-actions .btn,.detail-owner-actions form{width:100%}.boost-copy{grid-template-columns:1fr;gap:14px}.boost-copy .btn.boost,.boost-copy form{width:100%}}@media(max-width:420px){.detail-owner-actions .btn{min-height:42px}.boost-copy{padding:14px}.boost-copy h2{font-size:1.05rem}.boost-copy .btn.boost{min-height:46px}}</style>
  <style>.side-menu{max-height:100dvh;overflow:hidden}.menu-head,.menu-foot{flex:0 0 auto}.menu-links{flex:1 1 auto;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding-bottom:18px;scrollbar-width:thin}.menu-links::-webkit-scrollbar{width:8px}.menu-links::-webkit-scrollbar-thumb{background:#cfd9e4;border-radius:999px}.menu-links::-webkit-scrollbar-track{background:transparent}.menu-foot{background:#fff}</style>
  <style>.admin-page{max-width:1120px;margin:0 auto}.admin-page .section-head{align-items:center}.admin-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.admin-card{display:grid;gap:16px;align-content:start}.admin-card h2{margin:0;font-size:1.3rem}.admin-card .meta{margin:.45rem 0 0;line-height:1.5}.admin-controls{display:grid;gap:10px}.admin-card .menu-setting{display:block}.admin-card .switch{width:100%}@media(max-width:980px){.admin-grid{grid-template-columns:1fr 1fr}}@media(max-width:640px){.admin-page .section-head{align-items:stretch;flex-direction:column}.admin-page .section-head .btn{width:100%}.admin-grid{grid-template-columns:1fr}}</style>
  <style>.legal-checks{display:grid;gap:10px;margin-top:16px}.legal-check{display:grid;grid-template-columns:18px minmax(0,1fr);gap:10px;align-items:start;color:var(--muted);font-size:.92rem;line-height:1.45}.legal-check input{width:16px!important;min-width:16px!important;height:16px!important;min-height:16px!important;margin-top:3px;padding:0}.legal-check strong,.legal-check a{color:var(--ink);font-weight:900}.terms-page{max-width:820px;margin:0 auto}.terms-page h1{font-size:clamp(2rem,5vw,3.4rem);margin-bottom:14px}.terms-block{display:grid;gap:16px}.terms-block h2{font-size:1.15rem;margin:8px 0 0}.terms-block p{margin:0;color:var(--muted);line-height:1.65}</style>
  <style>.boost-checkout-wrap{max-width:1240px}.boost-checkout-panel{display:grid;grid-template-columns:minmax(240px,320px) minmax(0,1fr);gap:28px;align-items:start}.boost-product-media{overflow:hidden;border:1px solid var(--line);border-radius:8px;background:#fff;box-shadow:0 16px 36px rgba(20,32,48,.08)}.boost-product-media img{width:100%;aspect-ratio:1;object-fit:cover;display:block}.boost-product-info h1{font-size:clamp(2rem,4vw,3.4rem)}.boost-product-info .meta{font-size:1.02rem;line-height:1.58}.boost-product-pet{margin:18px 0 0;color:var(--muted)}.boost-info-box{margin:18px 0 20px;padding:24px 18px;border:1px solid #f0c56f;border-radius:8px;background:#fffaf0;color:var(--muted);text-align:center;line-height:1.45}.boost-plans{display:grid;grid-template-columns:repeat(3,minmax(210px,1fr));gap:14px;margin:18px 0;align-items:stretch}.boost-plan{position:relative;display:grid;grid-template-rows:auto auto auto 1fr auto;gap:10px;padding:16px;border:1px solid var(--line);border-radius:8px;background:#fff;cursor:pointer;min-height:330px}.boost-plan input{position:absolute;opacity:0;pointer-events:none}.boost-plan-name{width:max-content;max-width:100%;padding:7px 11px;border-radius:999px;background:#e8f1ff;color:#254f8f;font-size:.72rem;font-weight:900;text-transform:uppercase}.boost-plan:nth-child(2) .boost-plan-name{background:#efe7f6;color:#442069}.boost-plan:nth-child(3) .boost-plan-name{background:#fde7f0;color:#8e2452}.boost-plan-days{font-size:1.65rem;font-weight:900}.boost-plan-price{font-size:1.45rem;font-weight:900}.boost-plan-price small{font-size:.78rem;color:var(--muted)}.boost-plan ul{display:grid;align-content:start;gap:7px;margin:4px 0 0;padding:0;list-style:none;color:var(--muted);font-size:.82rem;line-height:1.25}.boost-plan li{overflow-wrap:anywhere}.boost-plan li:before{content:"✓";margin-right:7px;color:#7b35b5;font-weight:900}.boost-plan-cta{align-self:end;margin-top:auto;min-height:40px;border-radius:8px;border:1px solid var(--line);background:#edf3f7;color:var(--ink);display:inline-flex;align-items:center;justify-content:center;font-weight:900;font-size:.86rem;text-align:center}.boost-plan input:checked~*{color:inherit}.boost-plan:has(input:checked){border-color:#f0a51f;box-shadow:0 16px 34px rgba(164,102,20,.16);background:#fffaf0}.boost-plan:has(input:checked) .boost-plan-cta{background:#22607a;border-color:#22607a;color:#fff}.boost-plan:has(input:checked) .boost-plan-cta:before{content:"✓ ";margin-right:5px}.boost-checkout-panel .actions{align-items:stretch}.boost-checkout-panel .actions form{display:grid;gap:12px}.boost-checkout-panel .btn{min-height:48px}@media(max-width:1120px){.boost-checkout-panel{grid-template-columns:1fr}.boost-product-media{max-width:340px;margin:0 auto}.boost-plans{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:860px){.boost-plans{grid-template-columns:1fr}.boost-plan{min-height:0}.boost-checkout-panel .actions{display:grid;grid-template-columns:1fr}.boost-checkout-panel .actions form,.boost-checkout-panel .actions .btn{width:100%}}@media(max-width:420px){.boost-checkout-panel{padding:16px}.boost-product-info h1{font-size:2rem}.boost-info-box{padding:18px 14px}.boost-plan-days{font-size:1.5rem}.boost-plan-price{font-size:1.35rem}}</style>
  <style>.heatmap-page{display:grid;gap:18px}.heatmap-stats{grid-template-columns:repeat(4,minmax(0,1fr));margin:0}.heatmap-panel{padding:0;overflow:hidden}.heatmap-canvas{width:100%;height:min(72vh,720px);min-height:460px}.heatmap-list{margin-top:4px}.heatmap-list .mini-list{gap:12px}.heatmap-list .mini-report{grid-template-columns:64px minmax(0,1fr);align-items:center;gap:14px;padding:10px;min-width:0}.heatmap-list .mini-report>span:not(.mini-thumb){min-width:0;display:block}.heatmap-list .mini-report img,.heatmap-list .mini-thumb{width:64px;height:64px;min-width:64px;border-radius:8px;object-fit:cover}.heatmap-list .mini-report strong{display:block;line-height:1.2}.heatmap-list .mini-report .meta{display:block;margin-top:3px;line-height:1.35;overflow-wrap:anywhere}.map-popup{width:190px;display:grid;gap:7px;color:#18212f}.map-popup-img{width:190px;height:140px;object-fit:cover;border-radius:8px;display:block;background:#edf3f7}.map-popup strong{font-size:.95rem;line-height:1.2}.map-popup span{color:#617084;line-height:1.3;overflow-wrap:anywhere}.sms-search{grid-template-columns:minmax(0,1fr) auto}.sms-copy-box{margin-top:14px;min-height:150px;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;line-height:1.5}.sms-contact-list{display:grid;gap:8px;margin-top:14px}.sms-contact{display:grid;gap:3px;padding:10px;border:1px solid var(--line);border-radius:8px;background:#fbfdff}.sms-contact span{color:var(--muted);overflow-wrap:anywhere}@media(max-width:820px){.heatmap-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.heatmap-canvas{height:68vh;min-height:420px}.sms-search{grid-template-columns:1fr}}@media(max-width:480px){.heatmap-stats{grid-template-columns:1fr}.heatmap-canvas{height:62vh;min-height:360px}.heatmap-list .mini-report{grid-template-columns:58px minmax(0,1fr);gap:12px}.heatmap-list .mini-report img,.heatmap-list .mini-thumb{width:58px;height:58px;min-width:58px}.map-popup,.map-popup-img{width:160px}.map-popup-img{height:118px}}</style>
  <style>.pet-card{grid-template-columns:clamp(112px,28%,220px) minmax(0,1fr);align-items:stretch;min-height:0}.pet-media{position:relative;width:100%;height:100%;min-height:100%;background:#edf3f7;display:grid;place-items:center;overflow:hidden}.pet-media:before{content:"";position:absolute;inset:-12px;background-image:var(--pet-image);background-size:cover;background-position:center;filter:blur(14px);transform:scale(1.08);opacity:.55}.pet-media:after{content:"";position:absolute;inset:0;background:rgba(255,255,255,.18)}.pet-media img{position:relative;z-index:1;width:100%;height:100%;object-fit:contain;object-position:center center;display:block;margin:auto}.pet-media .photo-badge{z-index:2}.pet-body{position:relative;min-height:0;align-content:start;padding-top:20px}.pet-body .meta{margin:0;line-height:1.35}.pet-body .boost-badge{position:absolute;top:12px;right:12px}.pet-body.has-boost{padding-top:20px}.pet-body.has-boost h3{padding-right:120px}@media(max-width:520px){.pet-card{grid-template-columns:clamp(104px,30%,140px) minmax(0,1fr);align-items:stretch}.pet-media{width:100%;height:100%;min-height:100%}.pet-media:before{inset:-10px;filter:blur(12px)}.pet-body{min-height:0;padding-top:12px}.pet-body .boost-badge{top:10px;right:10px}.pet-body.has-boost h3{padding-right:112px;padding-top:0}}</style>
  <style>.id-plates-panel{scroll-margin-top:92px;margin:-6px 0 24px;padding:18px;border:1px solid var(--line);border-radius:8px;background:#fff;box-shadow:0 10px 34px rgba(20,32,48,.06);display:grid;grid-template-columns:160px minmax(0,1fr) auto;gap:20px;align-items:center}.id-plates-visual{width:160px;aspect-ratio:1;border-radius:8px;background:#edf3f7;overflow:hidden;box-shadow:0 14px 30px rgba(34,96,122,.16)}.id-plates-visual img{width:100%;height:100%;object-fit:cover;display:block}.id-plates-copy h2{margin:0;font-size:clamp(1.45rem,3vw,2.2rem);line-height:1.05}.id-plates-copy p:not(.eyebrow){margin:10px 0 0;color:var(--muted);line-height:1.55;max-width:760px}.id-plates-panel .btn{min-height:48px;white-space:nowrap}@media(max-width:900px){.id-plates-panel{grid-template-columns:124px minmax(0,1fr);align-items:center}.id-plates-visual{width:124px}.id-plates-panel .btn{grid-column:1/-1;width:100%}}@media(max-width:520px){.id-plates-panel{grid-template-columns:96px minmax(0,1fr);gap:14px;padding:14px}.id-plates-visual{width:96px}.id-plates-copy h2{font-size:1.35rem}.id-plates-copy p:not(.eyebrow){font-size:.92rem}}@media(max-width:390px){.id-plates-panel{grid-template-columns:1fr}.id-plates-visual{width:100%;max-width:220px}}</style>
  <style>.profile-layout{max-width:1120px;margin:0 auto;grid-template-columns:minmax(280px,340px) minmax(0,1fr);gap:18px}.profile-card{padding:24px}.profile-card h1{font-size:clamp(1.8rem,2.5vw,2.6rem);line-height:1.08;max-width:760px}.profile-layout .profile-card:first-child h1{font-size:clamp(2rem,3vw,2.9rem);line-height:1.02}.profile-card .avatar{width:96px;height:96px;font-size:2rem}.profile-card .form-grid{gap:14px}.profile-card .actions{margin-top:16px}.profile-layout+.profile-card{max-width:1120px;margin:18px auto 0!important}.profile-layout+.profile-card .section-head{align-items:center;margin-bottom:16px}.profile-layout+.profile-card .section-head p{margin:.35rem 0 0;color:var(--muted)}.profile-layout+.profile-card .mini-list{gap:12px}.profile-layout+.profile-card .mini-report{grid-template-columns:64px minmax(0,1fr);min-height:84px}.profile-layout+.profile-card .mini-report img,.profile-layout+.profile-card .mini-thumb{width:64px;height:64px}@media(min-width:841px){.profile-layout .profile-card:nth-child(2){padding:30px}.profile-layout .profile-card:nth-child(2) .actions{justify-content:flex-start}.profile-layout .profile-card:nth-child(2) .btn{min-width:210px}}@media(max-width:840px){.profile-layout{max-width:680px;grid-template-columns:1fr}.profile-layout+.profile-card{max-width:680px}.profile-card h1,.profile-layout .profile-card:first-child h1{font-size:clamp(1.7rem,8vw,2.35rem)}}@media(max-width:520px){.profile-card{padding:16px}.profile-card .form-grid{grid-template-columns:1fr}.profile-layout+.profile-card .section-head{align-items:stretch;flex-direction:column}.profile-layout+.profile-card .section-head .btn{width:100%}.profile-layout+.profile-card .mini-report{grid-template-columns:58px minmax(0,1fr)}.profile-layout+.profile-card .mini-report img,.profile-layout+.profile-card .mini-thumb{width:58px;height:58px}}</style>
  <style>.profile-layout{grid-template-areas:"account security" "account reports";align-items:start}.profile-account{grid-area:account}.profile-security{grid-area:security}.profile-reports{grid-area:reports;margin:0}.profile-reports .section-head{align-items:center;margin-bottom:16px}.profile-reports .section-head p{margin:.35rem 0 0;color:var(--muted)}.profile-reports .mini-list{gap:12px}.profile-reports .mini-report{grid-template-columns:64px minmax(0,1fr);min-height:84px}.profile-reports .mini-report img,.profile-reports .mini-thumb{width:64px;height:64px}@media(max-width:840px){.profile-layout{grid-template-areas:"account" "security" "reports"}.profile-reports{margin:0}}@media(max-width:520px){.profile-reports .section-head{align-items:stretch;flex-direction:column}.profile-reports .section-head .btn{width:100%}.profile-reports .mini-report{grid-template-columns:58px minmax(0,1fr)}.profile-reports .mini-report img,.profile-reports .mini-thumb{width:58px;height:58px}}</style>
  <style>html{scroll-behavior:smooth;overflow-x:hidden}body{overflow-x:hidden}.detail-wrap,.detail-info{min-width:0}.detail-info{overflow-wrap:anywhere}.page-floating{position:fixed;z-index:25;bottom:22px;display:inline-flex;align-items:center;justify-content:center;min-height:52px;border-radius:999px;box-shadow:0 14px 34px rgba(20,32,48,.18);font-weight:900;text-decoration:none}.float-top{left:18px;width:52px;height:52px;background:#fff;color:var(--ink);border:1px solid var(--line);font-size:1.45rem;opacity:0;pointer-events:none;transform:translateY(10px);transition:opacity .2s ease,transform .2s ease}.float-top.show{opacity:1;pointer-events:auto;transform:translateY(0)}.float-wa{right:18px;min-width:132px;padding:0 18px;gap:8px;background:#128C7E;color:#fff;border:1px solid #128C7E}.float-wa svg{width:20px;height:20px;display:block;flex:0 0 auto}.float-wa:hover{background:#0f766b;color:#fff}.float-top:hover{transform:translateY(-1px)}@media(max-width:520px){.page-floating{bottom:14px;min-height:46px}.float-top{left:12px;width:46px;height:46px}.float-wa{right:12px;min-width:112px;padding:0 14px}}</style>
</head>
<body id="top">
  <header class="topbar">
    <nav class="nav">
      <button class="menu-toggle" type="button" data-menu-open aria-label="Abrir menu"><span></span></button>
      <a class="brand" href="/"><img class="mark" src="/static/logo.png" alt="AyudaPet"><span>AyudaPet</span></a>
      <span class="nav-spacer" aria-hidden="true"></span>
    </nav>
  </header>
  <div class="menu-backdrop" data-menu-close></div>
  <aside class="side-menu" aria-label="Menu principal">
    <div class="menu-head">
      <a class="brand" href="/"><img class="mark" src="/static/logo.png" alt="AyudaPet"><span>AyudaPet</span></a>
      <button class="menu-close" type="button" data-menu-close aria-label="Cerrar menu">&times;</button>
    </div>
    <div class="menu-links">
      <?php if ($currentUser): ?>
        <a class="btn ghost <?= $active('/perfil') ?>" href="/perfil">Mi perfil</a>
        <a class="btn ghost <?= $active('/reportar') ?>" href="/reportar">Reportar mascota</a>
        <a class="btn ghost <?= $active('/') ?>" href="/#reportes-recientes">Reportes</a>
        <a class="btn ghost" href="/#plaquitas">Plaquitas QR</a>
        <?php if (is_admin_user()): ?><a class="btn ghost <?= $active('/admin') ?>" href="/admin">Administrar</a><?php endif; ?>
        <a class="btn facebook" href="https://www.facebook.com/AyudaPet26" target="_blank" rel="noopener">Facebook</a>
        <a class="btn ghost" href="https://ayudapet-nfts.vercel.app/" target="_blank" rel="noopener">AyudaPet Memorial</a>
        <?php if (donate_button_enabled()): ?><a class="btn donate" href="<?= e(donation_url()) ?>" target="_blank" rel="noopener">Donar</a><?php endif; ?>
        <a class="btn logout" href="/logout">Cerrar sesion</a>
      <?php else: ?>
        <a class="btn ghost <?= $active('/login') ?>" href="/login">Entrar</a>
        <a class="btn ghost <?= $active('/registro') ?>" href="/registro">Crear cuenta</a>
        <a class="btn ghost <?= $active('/') ?>" href="/#reportes-recientes">Reportes</a>
        <a class="btn ghost" href="/#plaquitas">Plaquitas QR</a>
        <a class="btn facebook" href="https://www.facebook.com/AyudaPet26" target="_blank" rel="noopener">Facebook</a>
        <a class="btn ghost" href="https://ayudapet-nfts.vercel.app/" target="_blank" rel="noopener">AyudaPet Memorial</a>
        <?php if (donate_button_enabled()): ?><a class="btn donate" href="<?= e(donation_url()) ?>" target="_blank" rel="noopener">Donar</a><?php endif; ?>
      <?php endif; ?>
    </div>
    <div class="menu-foot">Registro exclusivo con telefono mexicano.</div>
  </aside>
  <main class="shell">
    <?php foreach (flashes() as $flash): ?>
      <div class="flash <?= e($flash['type']) ?>"><?= e($flash['message']) ?></div>
    <?php endforeach; ?>
    <?php view($view, get_defined_vars()); ?>
  </main>
  <a class="page-floating float-top" href="#top" aria-label="Volver arriba" data-scroll-top-button>&uarr;</a>
  <a class="page-floating float-wa" href="https://wa.me/526564252167" target="_blank" rel="noopener" aria-label="WhatsApp AyudaPet"><svg viewBox="0 0 32 32" aria-hidden="true" focusable="false"><path fill="currentColor" d="M16.04 3.2A12.74 12.74 0 0 0 5.22 22.7L3.6 28.8l6.25-1.6a12.73 12.73 0 0 0 6.18 1.57h.01A12.79 12.79 0 0 0 16.04 3.2Zm7.53 18.05c-.31.88-1.82 1.68-2.55 1.79-.65.1-1.48.14-2.39-.15-.55-.17-1.26-.41-2.17-.8-3.82-1.65-6.31-5.5-6.5-5.75-.19-.26-1.55-2.06-1.55-3.93s.98-2.79 1.33-3.17c.35-.38.76-.48 1.02-.48h.73c.23.01.55-.09.86.66.31.76 1.06 2.6 1.15 2.79.09.19.16.41.03.67-.13.26-.19.41-.38.63-.19.22-.4.49-.57.66-.19.19-.39.4-.17.78.22.38.97 1.6 2.08 2.59 1.43 1.27 2.64 1.67 3.02 1.86.38.19.6.16.82-.1.22-.25.95-1.11 1.2-1.49.25-.38.51-.32.86-.19.35.13 2.22 1.05 2.6 1.24.38.19.63.29.73.45.09.16.09.92-.22 1.8Z"/></svg><span>WhatsApp</span></a>
  <?php if (donation_modal_enabled()): ?><div class="donation-modal" data-donation-modal aria-hidden="true">
    <section class="donation-dialog" role="dialog" aria-modal="true" aria-labelledby="donation-title">
      <button class="donation-close" type="button" aria-label="Cerrar" data-donation-close>&times;</button>
      <p class="eyebrow" style="color:var(--brand);">AyudaPet</p>
      <h2 id="donation-title">¿Quieres apoyar con un donativo?</h2>
      <p>Tu apoyo ayuda a mantener activa la plataforma para reportes de mascotas perdidas y en resguardo.</p>
      <div class="actions"><a class="btn primary" href="<?= e(donation_url()) ?>" data-donation-yes>Sí, donar</a><button class="btn" type="button" data-donation-no>No gracias</button></div>
    </section>
  </div><?php endif; ?>
  <footer>AyudaPet &copy; <?= e($year) ?> | ayudapet.com</footer>
  <div class="lightbox" data-lightbox aria-hidden="true">
    <button class="lightbox-close" type="button" data-lightbox-close aria-label="Cerrar imagen">&times;</button>
    <img src="" alt="">
  </div>
  <script><?= js() ?></script>
</body>
</html>
<?php
}

function view(string $view, array $vars): void {
    extract($vars, EXTR_SKIP);
    if ($view === 'index') { view_index($mascotas, $stats, $filters); return; }
    if ($view === 'detalle') { view_detalle($mascota, $isOwner, $canManage, $share, $mapUrl); return; }
    if ($view === 'registro') { view_registro(); return; }
    if ($view === 'terminos') { view_terminos(); return; }
    if ($view === 'verificar') { view_verificar($phone); return; }
    if ($view === 'set_password') { view_set_password($phone, $recovering); return; }
    if ($view === 'login') { view_login(); return; }
    if ($view === 'recuperar') { view_recuperar(); return; }
    if ($view === 'perfil') { view_perfil($user, $reportes); return; }
    if ($view === 'tipo_reporte') { view_tipo_reporte(); return; }
    if ($view === 'reportar') { view_reportar($mascota, $editing, $mapsApiKey); return; }
    if ($view === 'impulsar') { view_impulsar($mascota); return; }
    if ($view === 'admin') { view_admin_panel(); return; }
    if ($view === 'mapa_calor') { view_mapa_calor($reports, $stats, $mapsApiKey, $cityContacts); return; }
    if ($view === 'error') { view_error($title, $message); return; }
}

function css(): string {
    return <<<'CSS'
:root{--ink:#18212f;--muted:#617084;--line:#dfe7ef;--paper:#fff;--wash:#f5f7fb;--brand:#e85035;--brand-dark:#b93824;--blue:#176b87;--green:#287c5a;--amber:#a46614;--shadow:0 18px 48px rgba(20,32,48,.10)}*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);background:var(--wash)}a{color:inherit;text-decoration:none}.topbar{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{max-width:1440px;margin:0 auto;min-height:70px;padding:0 clamp(12px,4vw,22px);display:flex;align-items:center;justify-content:space-between;gap:20px}.menu-toggle{width:42px;height:42px;border:1px solid var(--line);border-radius:8px;background:#fff;display:inline-grid;place-items:center;cursor:pointer}.menu-toggle span,.menu-toggle span:before,.menu-toggle span:after{width:19px;height:2px;display:block;background:var(--ink);content:"";border-radius:99px}.menu-toggle span:before{transform:translateY(-6px)}.menu-toggle span:after{transform:translateY(4px)}.brand{display:flex;align-items:center;gap:12px;font-weight:900;letter-spacing:.02em}.mark{width:44px;height:44px;border-radius:999px;object-fit:cover;border:2px solid #fff;box-shadow:0 10px 24px rgba(20,32,48,.18)}.nav-spacer{width:42px}.menu-backdrop{position:fixed;inset:0;z-index:30;background:rgba(10,16,24,.42);opacity:0;pointer-events:none;transition:opacity .18s ease}.side-menu{position:fixed;inset:0 auto 0 0;z-index:40;width:min(330px,88vw);background:#fff;border-right:1px solid var(--line);box-shadow:var(--shadow);transform:translateX(-100%);transition:transform .2s ease;display:flex;flex-direction:column}body.menu-open .menu-backdrop{opacity:1;pointer-events:auto}body.menu-open .side-menu{transform:translateX(0)}.menu-head{min-height:72px;padding:16px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:12px}.menu-close{width:38px;height:38px;border:1px solid var(--line);border-radius:8px;background:#fff;font-size:1.4rem;cursor:pointer}.menu-links{padding:14px;display:grid;gap:8px}.menu-links .btn{width:100%;justify-content:flex-start;min-height:48px}.menu-links .btn.active{background:var(--brand);color:#fff;border-color:var(--brand)}.menu-foot{margin-top:auto;padding:16px 18px;color:var(--muted);border-top:1px solid var(--line);font-size:.9rem}.shell{max-width:1440px;margin:0 auto;padding:clamp(16px,4vw,34px) clamp(12px,4vw,22px) 48px}.hero{display:grid;grid-template-columns:minmax(0,1.7fr) 340px;gap:20px;margin-bottom:30px}.hero-main{min-height:300px;padding:42px;border-radius:8px;color:#fff;background:linear-gradient(110deg,rgba(24,33,47,.94),rgba(23,107,135,.82)),url("https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=1600&q=80");background-size:cover;background-position:center;box-shadow:var(--shadow);display:flex;flex-direction:column;justify-content:flex-end}.eyebrow{margin:0 0 12px;font-weight:800;color:#ffd9c7;text-transform:uppercase;font-size:.78rem}h1{margin:0;font-size:clamp(2rem,5vw,4.1rem);line-height:1;letter-spacing:0}.hero-main p{max-width:650px;color:rgba(255,255,255,.88);font-size:1.08rem;line-height:1.6;margin:18px 0 0}.panel,.pet-card,.form-panel{background:var(--paper);border:1px solid var(--line);border-radius:8px;box-shadow:0 10px 34px rgba(20,32,48,.06)}.panel{padding:22px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:18px}.stat{padding:16px;border:1px solid var(--line);border-radius:8px;background:#fbfdff}.stat strong{display:block;font-size:1.8rem}.stat span,.meta,.hint{color:var(--muted)}.stats-dropdown summary{list-style:none;display:flex;align-items:center;justify-content:space-between;gap:12px;cursor:pointer;font-weight:900}.stats-dropdown summary::-webkit-details-marker{display:none}.stats-dropdown summary:after{content:"+";color:var(--muted);font-size:1.25rem}.stats-dropdown[open] summary:after{content:"-"}.search-panel{margin:0 0 24px}.search-form{display:grid;grid-template-columns:minmax(0,1fr) 190px auto;gap:10px;align-items:end}.field{display:grid;gap:7px;min-width:0}.field.full{grid-column:1/-1}.search-form label,label{font-weight:800;font-size:.92rem}.filter-meta{margin:12px 0 0;color:var(--muted)}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}.actions form{display:flex;min-width:132px}.btn{border:0;border-radius:8px;min-height:42px;padding:0 16px;display:inline-flex;align-items:center;justify-content:center;gap:8px;font-weight:800;cursor:pointer;background:#e8edf3;color:var(--ink);text-align:center;max-width:100%}.btn.primary{color:#fff;background:var(--brand)}.btn.primary:hover{background:var(--brand-dark)}.btn.ghost{background:transparent;border:1px solid var(--line)}.section-head{display:flex;align-items:end;justify-content:space-between;gap:18px;margin:26px 0 14px}.section-head h2{margin:0;font-size:1.35rem}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:20px}.pet-card{position:relative;overflow:hidden;display:grid;grid-template-columns:220px minmax(0,1fr);min-height:220px;align-items:start;color:inherit}.pet-card:hover{transform:translateY(-2px);transition:transform .16s ease}.pet-media{position:relative;width:220px;height:220px;aspect-ratio:1;background:linear-gradient(135deg,rgba(232,80,53,.20),rgba(23,107,135,.20)),#edf3f7;display:grid;place-items:center;font-size:2rem;font-weight:900;color:var(--blue)}.pet-media img{width:100%;height:100%;object-fit:cover;display:block}.pet-body{min-height:220px;padding:20px 60px 20px 20px;border-left:1px solid var(--line);display:grid;gap:10px;align-content:start;min-width:0}.pet-body h3{margin:0;font-size:1.15rem}.pet-summary{margin:0;color:var(--muted);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.badge{display:inline-flex;align-items:center;min-height:28px;padding:0 10px;border-radius:999px;background:#eef5f7;color:var(--blue);font-weight:800;font-size:.78rem}.badge.lost{background:#fff2ef;color:var(--brand-dark)}.badge.found{background:#e9f7f0;color:var(--green)}.photo-badge{position:absolute;top:10px;right:10px;box-shadow:0 10px 24px rgba(20,32,48,.16)}.view-cue{position:absolute;top:12px;right:12px;width:34px;height:34px;display:grid;place-items:center;border-radius:999px;background:rgba(255,255,255,.94);border:1px solid rgba(20,32,48,.10);box-shadow:0 10px 24px rgba(20,32,48,.16);pointer-events:none}.view-cue svg{width:18px;height:18px;stroke:currentColor;stroke-width:2.2;fill:none;stroke-linecap:round;stroke-linejoin:round}.form-wrap{max-width:1040px;margin:0 auto}.form-panel{padding:clamp(20px,4vw,34px)}.form-panel h1{color:var(--ink);font-size:clamp(1.8rem,4vw,2.7rem)}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:20px}.login-form{grid-template-columns:repeat(2,minmax(0,1fr));align-items:start}.login-actions{grid-column:1/-1;margin-top:6px}input,textarea,select{width:100%;min-width:0;max-width:100%;border:1px solid #cfd9e4;border-radius:8px;min-height:44px;padding:10px 12px;background:#fff;color:var(--ink);font:inherit}textarea{min-height:118px;resize:vertical}input:focus,textarea:focus,select:focus{outline:3px solid rgba(23,107,135,.16);border-color:var(--blue)}.phone-box{display:grid;grid-template-columns:auto 1fr;align-items:center;border:1px solid #cfd9e4;border-radius:8px;background:#fff;overflow:hidden}.phone-prefix{min-height:44px;padding:0 12px;display:inline-flex;align-items:center;gap:8px;border-right:1px solid var(--line);background:#f8fafc;font-weight:900;white-space:nowrap}.phone-box input{border:0;border-radius:0}.switch{display:flex;align-items:center;justify-content:space-between;gap:14px;min-height:54px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:#fbfdff;cursor:pointer}.switch input{position:absolute;opacity:0;pointer-events:none}.switch-text{display:grid;gap:2px;font-weight:900}.switch-text small{font-weight:700;color:var(--muted)}.switch-ui{width:52px;height:30px;border-radius:999px;background:#cfd9e4;position:relative;flex:0 0 auto;transition:background .18s ease}.switch-ui:before{content:"";position:absolute;top:4px;left:4px;width:22px;height:22px;border-radius:999px;background:#fff;box-shadow:0 4px 12px rgba(20,32,48,.2);transition:transform .18s ease}.switch input:checked+.switch-ui{background:var(--green)}.switch input:checked+.switch-ui:before{transform:translateX(22px)}.contact-own{display:none}.contact-own.show{display:grid}.detail-wrap{display:grid;grid-template-columns:360px minmax(0,1fr);gap:28px;max-width:1120px;margin-inline:auto;align-items:start}.detail-photos{display:grid;gap:12px;max-width:360px}.detail-photo{overflow:hidden;padding:0;aspect-ratio:1;border-radius:8px;background:#edf3f7}.detail-media{position:relative;height:100%;aspect-ratio:1;display:grid;place-items:center;color:var(--blue);font-size:3rem;font-weight:900;background:linear-gradient(135deg,rgba(232,80,53,.18),rgba(23,107,135,.18)),#edf3f7}.detail-media img{width:100%;height:100%;object-fit:contain;display:block;background:#edf3f7}.info-list{display:grid;gap:0;margin-top:22px;border-top:1px solid var(--line)}.info-row{padding:12px 0;border-bottom:1px solid var(--line);display:grid;gap:3px}.info-row strong{font-size:.82rem;text-transform:uppercase;color:var(--muted)}.split-info{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 18px;margin-top:18px;border-top:1px solid var(--line)}.map-frame{width:100%;aspect-ratio:16/9;margin-top:22px;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#edf3f7}.map-frame iframe{width:100%;height:100%;border:0;display:block}.contact-actions,.share-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:18px}.share-title{grid-column:1/-1;margin:0;color:var(--muted);font-weight:900;text-transform:uppercase;font-size:.82rem}.btn.whatsapp{background:#25d366;color:#fff}.wa-icon{width:20px;height:20px;display:inline-block;flex:0 0 auto}.gallery{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:16px}.gallery img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:8px;border:1px solid var(--line)}.profile-layout{display:grid;grid-template-columns:420px minmax(0,1fr);gap:22px;align-items:start}.profile-card{padding:clamp(20px,4vw,32px)}.avatar{width:112px;height:112px;border-radius:999px;object-fit:cover;border:4px solid #fff;box-shadow:var(--shadow);background:#edf3f7;display:grid;place-items:center;color:var(--blue);font-size:2.4rem;font-weight:900;overflow:hidden}.avatar img{width:100%;height:100%;object-fit:cover;display:block}.mini-list{display:grid;gap:10px;margin-top:16px}.mini-report{display:grid;grid-template-columns:72px 1fr;gap:12px;align-items:center;padding:10px;border:1px solid var(--line);border-radius:8px;background:#fff}.mini-report img,.mini-thumb{width:72px;height:72px;object-fit:cover;border-radius:8px;background:#edf3f7;display:grid;place-items:center;color:var(--blue);font-weight:900}.edit-image-grid,.edit-images{display:flex;flex-wrap:wrap;gap:10px}.edit-image-item{position:relative;width:104px;height:104px;border:1px solid var(--line);border-radius:8px;background:#fbfdff;display:grid;overflow:hidden}.edit-image-item.removing{display:none}.edit-image-item img{width:100%;height:100%;object-fit:cover;display:block}.remove-image-check{position:absolute;top:8px;right:8px;width:34px;height:34px;border-radius:999px;display:grid;place-items:center;background:rgba(184,56,36,.95);color:#fff;font-weight:900;box-shadow:0 10px 24px rgba(20,32,48,.20);cursor:pointer}.remove-image-check input{position:absolute;opacity:0;pointer-events:none}.zoomable{cursor:zoom-in}.lightbox{position:fixed;inset:0;z-index:80;display:none;align-items:center;justify-content:center;padding:24px;background:rgba(6,10,16,.88)}.lightbox.open{display:flex}.lightbox img{max-width:min(1100px,94vw);max-height:88vh;object-fit:contain;border-radius:8px;box-shadow:0 24px 80px rgba(0,0,0,.42);background:#111}.lightbox-close{position:absolute;top:16px;right:16px;width:42px;height:42px;border:1px solid rgba(255,255,255,.25);border-radius:8px;background:rgba(255,255,255,.12);color:#fff;font-size:1.6rem;cursor:pointer}.flash{border-radius:8px;padding:12px 14px;border:1px solid var(--line);background:#fff;font-weight:700;margin-bottom:10px}.flash.success{border-color:#bde5d0;background:#effaf4;color:var(--green)}.flash.error{border-color:#f1b8aa;background:#fff2ef;color:var(--brand-dark)}.flash.warning{border-color:#edd398;background:#fff8e8;color:var(--amber)}.empty{padding:34px;text-align:center;color:var(--muted);border:1px dashed #c6d2de;border-radius:8px;background:#fff}footer{color:var(--muted);text-align:center;padding:20px}@media(max-width:840px){.hero,.grid,.form-grid,.login-form,.detail-wrap,.profile-layout{grid-template-columns:1fr}.contact-actions{grid-template-columns:1fr}.search-form{grid-template-columns:1fr}.actions{flex-direction:column;align-items:stretch}.actions .btn,.actions form{width:100%}.stats{grid-template-columns:1fr}.detail-photos{max-width:none}}@media(max-width:420px){.pet-card{grid-template-columns:104px minmax(0,1fr);min-height:104px}.pet-media{width:104px;height:104px;font-size:1.55rem}.pet-body{min-height:104px;padding:12px 44px 12px 12px;gap:7px}.pet-body h3{font-size:1rem}.pet-summary{-webkit-line-clamp:1}.photo-badge{top:7px;right:7px;min-height:24px;padding:0 8px;font-size:.68rem}.view-cue{top:8px;right:8px;width:28px;height:28px}.hero-main{min-height:260px}.form-panel,.profile-card,.panel{padding:16px}}
CSS;
}

function js(): string {
    return <<<'JS'
function escapeHtml(value){return String(value||"").replace(/[&<>"']/g,(char)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]))}
function formatLocalPhone(value){const digits=value.replace(/\D/g,"").slice(0,10);if(digits.length<=3)return digits;if(digits.length<=6)return `(${digits.slice(0,3)}) ${digits.slice(3)}`;return `(${digits.slice(0,3)}) ${digits.slice(3,6)}-${digits.slice(6)}`}
document.querySelectorAll("[data-phone-input]").forEach((input)=>{input.addEventListener("input",()=>{input.value=formatLocalPhone(input.value)});input.form?.addEventListener("submit",()=>{input.value=input.value.replace(/\D/g,"").slice(0,10)})});
document.querySelectorAll("[data-menu-open]").forEach((button)=>button.addEventListener("click",()=>document.body.classList.add("menu-open")));
document.querySelectorAll("[data-menu-close]").forEach((button)=>button.addEventListener("click",()=>document.body.classList.remove("menu-open")));
document.querySelectorAll(".menu-links a").forEach((link)=>link.addEventListener("click",()=>document.body.classList.remove("menu-open")));
document.addEventListener("keydown",(event)=>{if(event.key==="Escape")document.body.classList.remove("menu-open")});
(()=>{const button=document.querySelector("[data-scroll-top-button]");if(!button)return;const sync=()=>{button.classList.toggle("show",window.scrollY>Math.max(420,window.innerHeight*.55))};window.addEventListener("scroll",sync,{passive:true});window.addEventListener("resize",sync);sync()})();
document.querySelectorAll("[data-responsive-open]").forEach((details)=>{const query=window.matchMedia("(min-width: 841px)");const sync=()=>{details.open=query.matches};sync();query.addEventListener?.("change",sync)});
const lightbox=document.querySelector("[data-lightbox]");const lightboxImage=lightbox?.querySelector("img");function closeLightbox(){if(!lightbox||!lightboxImage)return;lightbox.classList.remove("open");lightbox.setAttribute("aria-hidden","true");lightboxImage.src="";lightboxImage.alt=""}
document.querySelectorAll("[data-zoom-src]").forEach((image)=>image.addEventListener("click",(event)=>{if(!lightbox||!lightboxImage)return;event.preventDefault();event.stopPropagation();lightboxImage.src=image.dataset.zoomSrc;lightboxImage.alt=image.alt||"Imagen ampliada";lightbox.classList.add("open");lightbox.setAttribute("aria-hidden","false")}));
document.querySelectorAll("[data-lightbox-close]").forEach((button)=>button.addEventListener("click",closeLightbox));lightbox?.addEventListener("click",(event)=>{if(event.target===lightbox)closeLightbox()});document.addEventListener("keydown",(event)=>{if(event.key==="Escape")closeLightbox()});
document.querySelectorAll("[data-remove-image]").forEach((button)=>button.addEventListener("click",async(event)=>{event.preventDefault();const input=button.querySelector("input");const item=button.closest(".edit-image-item");if(input)input.checked=true;item?.classList.add("removing");if(!button.dataset.removeUrl)return;try{const response=await fetch(button.dataset.removeUrl,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({target:button.dataset.removeTarget,image:button.dataset.removeImageUrl||null})});if(!response.ok)throw new Error("remove failed")}catch(error){if(input)input.checked=false;item?.classList.remove("removing");alert("No se pudo eliminar la imagen. Intenta de nuevo.")}}));
document.querySelectorAll("[data-copy-url]").forEach((button)=>button.addEventListener("click",async()=>{const url=button.dataset.copyUrl;if(!url)return;try{await navigator.clipboard.writeText(url)}catch(error){const input=document.createElement("input");input.value=url;document.body.appendChild(input);input.select();document.execCommand("copy");input.remove()}const original=button.textContent;button.textContent="Copiado";window.setTimeout(()=>{button.textContent=original},1600)}));
document.addEventListener("click",async(event)=>{const button=event.target.closest("[data-copy-sms]");if(!button)return;const box=document.querySelector("[data-sms-copy]");const text=box?.value||"";if(!text)return;try{await navigator.clipboard.writeText(text)}catch(error){box?.focus();box?.select();document.execCommand("copy")}const original=button.textContent;button.textContent="Copiado";window.setTimeout(()=>{button.textContent=original},1600)});
document.querySelectorAll("[data-sms-search]").forEach((form)=>form.addEventListener("submit",async(event)=>{event.preventDefault();const input=form.querySelector("[name='ciudad']");const results=document.querySelector("[data-sms-results]");const city=(input?.value||"").trim();if(!results||!city)return;const button=form.querySelector("button[type='submit']");const original=button?.textContent||"";if(button){button.disabled=true;button.textContent="Buscando"}results.innerHTML='<div class="empty">Buscando telefonos...</div>';try{const response=await fetch(`/mapa-calor/contactos?ciudad=${encodeURIComponent(city)}`,{headers:{"Accept":"application/json"}});const data=await response.json();if(!response.ok||!data.ok)throw new Error(data.message||"Error");const count=(data.contacts||[]).length;let html=`<p class="filter-meta">${count} telefono${count===1?"":"s"} para ${escapeHtml(data.city)}${data.source?` · ${escapeHtml(data.source)}`:""}.</p>`;if(count){html+=`<textarea class="sms-copy-box" readonly data-sms-copy>${escapeHtml(data.sms||"")}</textarea><div class="actions"><button class="btn share" type="button" data-copy-sms>Copiar telefonos para SMS</button></div><div class="sms-contact-list">`;html+=(data.contacts||[]).slice(0,80).map((contact)=>`<div class="sms-contact"><strong>${escapeHtml(contact.sms)}</strong><span>${escapeHtml(contact.direccion)}</span></div>`).join("");html+="</div>"}else{html+='<div class="empty">No encontre telefonos asociados a esa ciudad.</div>'}results.innerHTML=html;history.replaceState(null,"",`/mapa-calor?ciudad=${encodeURIComponent(city)}`)}catch(error){results.innerHTML='<div class="empty">No se pudo buscar. Intenta de nuevo.</div>'}finally{if(button){button.disabled=false;button.textContent=original}}}));
document.querySelectorAll("[data-report-filter-form]").forEach((form)=>form.addEventListener("submit",(event)=>{event.preventDefault();const params=new URLSearchParams(new FormData(form));for(const [key,value] of Array.from(params.entries())){if(!String(value).trim()||(key==="estado"&&value==="todos"))params.delete(key)}const query=params.toString();window.location.href=`/${query?`?${query}`:""}#reportes-recientes`}));
document.querySelectorAll("[data-native-share-button]").forEach((button)=>button.addEventListener("click",async()=>{const shareData={title:button.dataset.shareTitle||document.title,text:button.dataset.shareText||"",url:button.dataset.shareUrl||window.location.href};if(navigator.share){try{await navigator.share(shareData);return}catch(error){if(error?.name==="AbortError")return}}const original=button.textContent;button.textContent="Usa copiar enlace";window.setTimeout(()=>{button.textContent=original},1800)}));
document.querySelectorAll("[data-max-files]").forEach((input)=>input.addEventListener("change",()=>{const maxFiles=Number(input.dataset.maxFiles||0);if(input.files.length>maxFiles){input.value="";alert(maxFiles>0?`Solo puedes seleccionar hasta ${maxFiles} imagenes.`:"Ya tienes el maximo de 3 fotos adicionales.")}}));
document.querySelectorAll("[data-report-form]").forEach((form)=>form.addEventListener("submit",(event)=>{if(form.dataset.submitting==="1"){event.preventDefault();return}form.dataset.submitting="1";form.querySelectorAll("button[type='submit']").forEach((button)=>{button.disabled=true;button.textContent=button.textContent.includes("Guardar")?"Guardando...":"Publicando..."})}));
document.querySelectorAll("[data-contact-toggle]").forEach((toggle)=>{const box=document.querySelector("[data-contact-own]");const input=document.querySelector("[data-contact-input]");const sync=()=>{if(!box)return;box.classList.toggle("show",toggle.checked);if(input){input.disabled=!toggle.checked;if(toggle.checked&&!input.value)input.value=input.dataset.registeredPhone||"";if(!toggle.checked)input.value=""}};toggle.addEventListener("change",sync);sync()});
document.querySelectorAll("[data-money-input]").forEach((input)=>{const preview=document.querySelector("[data-money-preview]");const sync=()=>{if(!preview)return;const amount=Number(String(input.value||"").replace(/\D/g,""));preview.textContent=amount>0?`$${amount.toLocaleString("es-MX")} M.N.`:"Se mostrara como $1,000 M.N."};input.addEventListener("input",sync);sync()});
document.querySelectorAll("[data-boost-whatsapp]").forEach((link)=>{const scope=link.closest(".boost-product-info")||document;const sync=()=>{const checked=scope.querySelector('input[name="plan_dias"]:checked');if(checked?.dataset.whatsappUrl)link.href=checked.dataset.whatsappUrl};scope.querySelectorAll('input[name="plan_dias"]').forEach((input)=>input.addEventListener("change",sync));sync()});
(()=>{const modal=document.querySelector("[data-donation-modal]");if(!modal)return;const key="ayudapet_donation_prompt";const delays=[12,24,36];const read=()=>{try{return JSON.parse(localStorage.getItem(key)||"{}")}catch(error){return {}}};const write=(value)=>{try{localStorage.setItem(key,JSON.stringify(value))}catch(error){}};const state=read();if(state.donated)return;if(Number(state.nextAt||0)>Date.now())return;const close=()=>{modal.classList.remove("open");modal.setAttribute("aria-hidden","true")};window.setTimeout(()=>{modal.classList.add("open");modal.setAttribute("aria-hidden","false")},45000);modal.querySelector("[data-donation-close]")?.addEventListener("click",close);modal.querySelector("[data-donation-no]")?.addEventListener("click",()=>{const current=read();const count=Number(current.noCount||0);const hours=delays[Math.min(count,delays.length-1)];write({noCount:count+1,nextAt:Date.now()+hours*60*60*1000});close()});modal.querySelector("[data-donation-yes]")?.addEventListener("click",()=>write({donated:true,donatedAt:Date.now()}));})();
JS;
}

function view_index(array $mascotas, array $stats, array $filters): void { ?>
  <?php $activeFilter = trim((string)$filters['q']) !== '' || $filters['estado'] !== 'todos'; ?>
  <section class="hero">
    <div class="hero-main">
      <p class="eyebrow">Red de reportes comunitarios</p>
      <h1>Mascotas perdidas y encontradas</h1>
      <p>Publica reportes completos, concentra datos de contacto y ayuda a que cada mascota vuelva a casa mas rapido.</p>
      <div class="actions"><a class="btn primary" href="/reportar">Crear reporte</a><a class="btn" href="/registro">Unirme</a></div>
    </div>
    <aside class="panel">
      <details class="stats-dropdown" data-responsive-open>
        <summary><span class="badge">Panel activo</span><span><?= e($stats['activos']) ?> activos</span></summary>
        <div class="stats">
          <div class="stat"><strong><?= e($stats['total']) ?></strong><span>reportes</span></div>
          <div class="stat"><strong><?= e($stats['activos']) ?></strong><span>activos</span></div>
          <div class="stat"><strong><?= e($stats['encontrados']) ?></strong><span>resueltos</span></div>
        </div>
        <p class="meta" style="margin-top:18px;">Los reportes mas recientes aparecen primero para facilitar busquedas por direccion y contacto.</p>
      </details>
    </aside>
  </section>
  <section class="id-plates-panel" id="plaquitas">
    <div class="id-plates-visual"><img src="/static/plaquitas.png" alt="Plaquitas inteligentes con codigo QR para mascotas"></div>
    <div class="id-plates-copy">
      <p class="eyebrow" style="color:var(--brand);">Plaquitas inteligentes</p>
      <h2>Nunca pierdas de vista a tu mascota</h2>
      <p>Con nuestra Placa Inteligente para Mascotas con Codigo QR, cualquier persona puede escanearla y acceder a la informacion vital de tu mascota en segundos.</p>
    </div>
    <a class="btn primary" href="https://articulo.mercadolibre.com.mx/MLM-2221510741-placas-ubican-id-_JM" target="_blank" rel="noopener">Comprar en Mercado Libre</a>
  </section>
  <section class="panel search-panel"><details class="filter-dropdown" <?= $activeFilter ? 'open' : '' ?>><summary><span>Buscar y filtrar</span></summary><form class="search-form" method="get" action="/" data-report-filter-form><div class="field"><label for="q">Buscar</label><input id="q" name="q" value="<?= e($filters['q']) ?>" placeholder="Nombre, direccion o contacto"></div><div class="field"><label for="estado">Estado</label><select id="estado" name="estado"><?php foreach (['todos'=>'Todos','perdidos'=>'Perdidos','resguardo'=>'Resguardados','en_casa'=>'En casa'] as $value => $label): ?><option value="<?= e($value) ?>" <?= $filters['estado'] === $value ? 'selected' : '' ?>><?= e($label) ?></option><?php endforeach; ?></select></div><button class="btn primary" type="submit">Buscar</button></form><p class="filter-meta"><?= e($filters['resultados']) ?> resultado<?= $filters['resultados'] == 1 ? '' : 's' ?></p></details></section>
  <div class="section-head" id="reportes-recientes"><div><h2>Reportes recientes</h2><p>Informacion publica enviada por la comunidad.</p></div></div>
  <?php if ($mascotas): ?><section class="grid">
    <?php foreach ($mascotas as $pet): ?>
      <a class="pet-card <?= is_boosted($pet) ? 'boosted' : '' ?>" href="/mascotas/<?= e($pet['id']) ?>">
        <div class="pet-media" <?= $pet['principal'] ? 'style="--pet-image:url(\'' . e($pet['principal']) . '\')"' : '' ?>>
          <?php if ($pet['principal']): ?><img src="<?= e($pet['principal']) ?>" alt="<?= e($pet['nombre']) ?>"><?php else: ?><?= e(first_letter($pet['nombre'] ?: '?')) ?><?php endif; ?>
          <span class="badge photo-badge <?= e(report_status_class($pet)) ?>"><?= e(report_status_label($pet)) ?></span>
        </div>
        <div class="pet-body <?= is_boosted($pet) ? 'has-boost' : '' ?>">
          <?php if (is_boosted($pet)): ?><span class="badge boost-badge">Impulsado</span><?php endif; ?>
          <h3><?= e($pet['nombre']) ?></h3>
          <p class="meta"><?php if ($pet['direccion']): ?><strong>Direccion:</strong> <?= e($pet['direccion']) ?><br><?php endif; ?></p>
        </div>
      </a>
    <?php endforeach; ?>
  </section><?php else: ?><div class="empty">Todavia no hay reportes publicados.</div><?php endif; ?>
<?php }

function view_detalle(array $mascota, bool $isOwner, bool $canManage, array $share, ?string $mapUrl): void {
    $secundarias = pet_secondaries($mascota);
    $publicContact = public_contact_value($mascota['contacto'] ?? null);
    $callPhone = phone_digits($publicContact);
    $waPhone = whatsapp_digits($publicContact);
    $direccionLabel = report_type_value($mascota['tipo_reporte'] ?? '') === 'resguardo' ? 'Direccion donde se encontro' : 'Direccion de extravio';
    $boostedUntil = boosted_until_label($mascota);
    $reportOwner = is_admin_user() ? get_user((string)($mascota['reportado_por'] ?? '')) : null;
    ?>
  <section class="detail-wrap">
    <div class="detail-photos">
      <div class="detail-photo"><div class="detail-media">
        <?php if ($mascota['principal']): ?><img class="zoomable" src="<?= e($mascota['principal']) ?>" alt="<?= e($mascota['nombre']) ?>" data-zoom-src="<?= e($mascota['principal']) ?>"><?php else: ?><?= e(first_letter($mascota['nombre'] ?: '?')) ?><?php endif; ?>
        <span class="badge views-badge"><?= e(views_label($mascota['vistas'] ?? 0)) ?></span>
        <span class="badge photo-badge <?= e(report_status_class($mascota)) ?>"><?= e(report_status_label($mascota)) ?></span>
      </div></div>
      <?php if ($secundarias): ?><div class="gallery"><?php foreach ($secundarias as $image): ?><img class="zoomable" src="<?= e($image) ?>" alt="Foto de <?= e($mascota['nombre']) ?>" data-zoom-src="<?= e($image) ?>"><?php endforeach; ?></div><?php endif; ?>
    </div>
    <article class="detail-info">
      <?php if ($canManage): ?><div class="detail-owner-actions"><a class="btn edit" href="/mascotas/<?= e($mascota['id']) ?>/editar">Editar</a><form method="post" action="/mascotas/<?= e($mascota['id']) ?>/eliminar" onsubmit="return confirm('Eliminar este reporte?');"><button class="btn delete" type="submit">Eliminar</button></form></div><?php endif; ?>
      <?php if (is_admin_user()): ?><div class="boost-panel"><div><span class="badge">Solo admin</span><div class="info-list" style="margin-top:12px;"><?php info_row('Usuario', ($reportOwner['nombre'] ?? '') ?: 'Sin nombre'); info_row('Telefono registrado', $mascota['reportado_por'] ?? ''); info_row('Direccion real', ($mascota['direccion_completa'] ?? '') ?: ($mascota['direccion'] ?? '')); ?></div></div></div><?php endif; ?>
      <?php if (is_admin_user()): ?><form class="boost-panel" method="post" action="/mascotas/<?= e($mascota['id']) ?>/impulso-manual"><input type="hidden" name="enabled" value="0"><?php if (!$boostedUntil): ?><select name="dias" aria-label="Dias de impulso"><?php foreach (visible_boost_plans() as $plan): $d = (int)$plan['days']; ?><option value="<?= e((string)$d) ?>" <?= $d === default_boost_plan_days() ? 'selected' : '' ?>><?= e((string)$d) ?> dias</option><?php endforeach; ?></select><?php endif; ?><label class="switch"><span class="switch-text"><span>Impulso manual</span><small><?= $boostedUntil ? 'Activo hasta ' . e($boostedUntil) : 'Selecciona dias y activa' ?></small></span><input type="checkbox" name="enabled" value="1" <?= $boostedUntil ? 'checked' : '' ?> onchange="this.form.submit()"><span class="switch-ui" aria-hidden="true"></span></label></form><?php endif; ?>
      <?php if (is_admin_user()): ?><form class="boost-panel admin-views-panel" method="post" action="/mascotas/<?= e($mascota['id']) ?>/vistas"><div class="field"><label for="admin_vistas">Vistas</label><input id="admin_vistas" name="vistas" type="number" min="0" step="1" value="<?= e((string)max(0, (int)($mascota['vistas'] ?? 0))) ?>"></div><button class="btn primary" type="submit">Guardar vistas</button></form><?php endif; ?>
      <?php if ($boostedUntil): ?><div class="boost-panel"><span class="badge boost-badge">Impulsado</span><strong>Activo hasta <?= e($boostedUntil) ?></strong></div><?php endif; ?>
      <?php if ($canManage && !$boostedUntil): ?><div class="boost-copy"><div><h2>Impulsa tu anuncio.</h2><p>Lo destacamos en AyudaPet y tambien enviamos tu reporte directo a celulares de personas cercanas a la zona donde se perdio tu mascota.</p></div><a class="btn <?= boost_button_enabled() ? 'boost' : 'whatsapp' ?>" href="/mascotas/<?= e($mascota['id']) ?>/impulsar"><?= boost_button_enabled() ? 'Impulsar ahora' : 'Activar por WhatsApp' ?></a></div><?php endif; ?>
      <div class="info-list"><?php info_row('Tipo de reporte', report_type_label($mascota['tipo_reporte'] ?? 'extravio')); info_row('Fecha', $mascota['fecha']); info_row('Nombre de mascota', $mascota['nombre']); info_row('Descripcion', $mascota['descripcion']); ?></div>
      <div class="split-info"><?php foreach ([['Tipo de mascota','tipo_mascota'],['Edad','edad'],['Raza','raza'],['Genero','genero'],['Color','color'],['Collar','collar'],['Docil','docil']] as [$label,$key]) info_row($label, $mascota[$key]); ?></div>
      <?php if ($mapUrl): ?><div class="map-frame"><iframe src="<?= e($mapUrl) ?>" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen title="Mapa de direccion de extravio"></iframe></div><?php endif; ?>
      <div class="info-list"><?php info_row($direccionLabel, $mascota['direccion']); ?></div>
      <div class="split-info"><?php info_row('Recompensa', reward_display($mascota)); ?></div>
      <?php if ($callPhone && empty($mascota['encontrado'])): ?><div class="contact-actions"><a class="btn call" href="tel:<?= e($callPhone) ?>">Llamar</a><a class="btn whatsapp" href="https://wa.me/<?= e($waPhone) ?>" target="_blank" rel="noopener">WhatsApp</a></div><?php endif; ?>
      <div class="share-actions" aria-label="Compartir reporte"><p class="share-title">Comparte:</p><button class="btn share" type="button" data-native-share-button data-share-title="<?= e($share['text']) ?>" data-share-text="<?= e($share['message']) ?>" data-share-url="<?= e($share['url']) ?>">Compartir</button><button class="btn" type="button" data-copy-url="<?= e($share['url']) ?>">Copiar enlace</button></div>
      <div class="actions"><a class="btn back-report" href="/#reportes-recientes">Volver a reportes</a></div>
    </article>
  </section>
<?php }

function info_row(string $label, $value): void {
    if ($value === null || $value === '') return;
    echo '<div class="info-row"><strong>' . e($label) . '</strong><span>' . e($value) . '</span></div>';
}

function phone_field(string $id = 'tel', string $name = 'tel'): void { ?>
  <div class="phone-box"><span class="phone-prefix"><span>MX</span><span>+52</span></span><input id="<?= e($id) ?>" name="<?= e($name) ?>" inputmode="numeric" autocomplete="tel" placeholder="(656) 778-7712" maxlength="14" pattern="\(?[0-9]{3}\)?[\s-]?[0-9]{3}-?[0-9]{4}" data-phone-input required></div>
<?php }

function view_registro(): void { ?>
  <section class="form-wrap"><form class="form-panel" method="post"><p class="eyebrow" style="color:var(--brand);">Registro seguro</p><h1>Crea tu cuenta</h1><p class="meta">Solo aceptamos números mexicanos de 10 dígitos.</p><div class="form-grid"><div class="field full"><label for="tel">Teléfono mexicano</label><?php phone_field(); ?></div></div><div class="legal-checks">
    <label class="legal-check"><input type="checkbox" name="acepta_terminos" value="1" required><span>Acepto los <a href="/terminos" target="_blank" rel="noopener">Términos y condiciones</a>.</span></label>
  </div><div class="actions"><button class="btn primary" type="submit">Enviar codigo</button></div></form></section>
<?php }

function view_terminos(): void { ?>
  <section class="form-panel terms-page"><p class="eyebrow" style="color:var(--brand);">AyudaPet</p><h1>Términos y condiciones</h1><div class="terms-block">
    <p>Al crear una cuenta y publicar reportes en AyudaPet, aceptas que la plataforma funciona como una herramienta comunitaria para difundir información de mascotas extraviadas, resguardadas o en casa.</p>
    <h2>Responsabilidad de la información</h2>
    <p>La información, fotografías, teléfonos, direcciones aproximadas y cualquier dato publicado son proporcionados por los usuarios. Cada usuario es responsable de verificar que la información sea correcta y de contar con autorización para publicarla.</p>
    <h2>Deslinde de AyudaPet</h2>
    <p>AyudaPet no garantiza la recuperación, entrega, ubicación, estado físico, salud o propiedad legal de ninguna mascota. AyudaPet no se hace responsable por acuerdos, llamadas, mensajes, entregas, recompensas, conflictos o interacciones entre usuarios o terceros.</p>
    <h2>Mensajes SMS</h2>
    <p>Autorizas a AyudaPet a enviarte SMS relacionados con tu cuenta, códigos de verificación, reportes, alertas, seguimiento, avisos importantes e información publicitaria de AyudaPet. Puedes solicitar dejar de recibir mensajes promocionales contactando a AyudaPet.</p>
    <h2>Privacidad</h2>
    <p>AyudaPet no vende ni comparte tu información personal con terceros para que ellos la comercialicen. La información se usa para operar la plataforma, validar cuentas, mostrar reportes, contactar usuarios y apoyar la difusión de mascotas reportadas.</p>
    <h2>Uso adecuado</h2>
    <p>No se permite publicar información falsa, ofensiva, fraudulenta, peligrosa o que afecte derechos de otras personas. AyudaPet puede editar, ocultar o eliminar reportes que considere indebidos o riesgosos para la comunidad.</p>
  </div><div class="actions"><a class="btn primary" href="/registro">Volver al registro</a></div></section>
<?php }

function view_verificar(string $phone): void { ?>
  <section class="form-wrap"><form class="form-panel" method="post"><p class="eyebrow" style="color:var(--brand);">Verificacion</p><h1>Confirma tu telefono</h1><p class="meta">Enviamos un codigo a <?= e($phone) ?>. Expira en pocos minutos.</p><div class="form-grid"><div class="field full"><label for="code">Codigo</label><input id="code" name="code" inputmode="numeric" maxlength="6" placeholder="000000" required></div></div><div class="actions"><button class="btn primary" type="submit">Verificar</button></div></form></section>
<?php }

function view_set_password(string $phone, bool $recovering): void { ?>
  <section class="form-wrap"><form class="form-panel" method="post"><p class="eyebrow" style="color:var(--brand);">Cuenta</p><h1><?= $recovering ? 'Restablecer contrasena' : 'Protege tu acceso' ?></h1><p class="meta">Telefono verificado: <?= e($phone) ?></p><div class="form-grid"><?php if (!$recovering): ?><div class="field"><label for="nombre">Nombre</label><input id="nombre" name="nombre" autocomplete="name" placeholder="Tu nombre"></div><?php endif; ?><div class="field"><label for="pwd"><?= $recovering ? 'Nueva contrasena' : 'Contrasena' ?></label><input id="pwd" name="pwd" type="password" autocomplete="new-password" minlength="8" required></div></div><div class="actions"><button class="btn primary" type="submit"><?= $recovering ? 'Guardar contrasena' : 'Guardar cuenta' ?></button></div></form></section>
<?php }

function view_login(): void { ?>
  <section class="form-wrap"><form class="form-panel" method="post"><p class="eyebrow" style="color:var(--brand);">Acceso</p><h1>Entra a AyudaPet</h1><div class="form-grid login-form"><div class="field"><label for="tel">Telefono mexicano</label><?php phone_field(); ?><span class="hint">Usa el numero mexicano con el que creaste tu cuenta.</span></div><div class="field"><label for="pwd">Contrasena</label><input id="pwd" name="pwd" type="password" autocomplete="current-password" required></div><div class="actions login-actions"><button class="btn primary" type="submit">Entrar</button><a class="btn" href="/registro">Crear cuenta</a><a class="btn ghost" href="/recuperar">Restablecer contrasena</a></div></div></form></section>
<?php }

function view_recuperar(): void { ?>
  <section class="form-wrap"><form class="form-panel" method="post"><p class="eyebrow" style="color:var(--brand);">Recuperacion</p><h1>Restablecer contrasena</h1><p class="meta">Enviaremos un codigo al telefono registrado.</p><div class="form-grid"><div class="field full"><label for="tel">Telefono mexicano</label><?php phone_field(); ?></div></div><div class="actions"><button class="btn primary" type="submit">Enviar codigo</button></div></form></section>
<?php }

function view_perfil(array $user, array $reportes): void { ?>
  <section class="profile-layout">
    <div class="panel profile-card profile-account"><p class="eyebrow" style="color:var(--brand);">Cuenta</p><div class="avatar"><?php if ($user['foto']): ?><img src="<?= e($user['foto']) ?>" alt="<?= e($user['nombre'] ?: 'Perfil') ?>"><?php else: ?><?= e(first_letter($user['nombre'] ?: $user['telefono'])) ?><?php endif; ?></div><h1><?= e($user['nombre'] ?: 'Mi perfil') ?></h1><p class="meta"><strong>Telefono registrado:</strong><br><?= e($user['telefono']) ?></p><form method="post" enctype="multipart/form-data" class="form-grid"><div class="field full"><label for="nombre">Nombre</label><input id="nombre" name="nombre" value="<?= e($user['nombre'] ?? '') ?>"></div><div class="field full"><label for="foto">Foto de perfil</label><input id="foto" name="foto" type="file" accept="image/*"></div><div class="actions"><button class="btn primary" type="submit">Guardar perfil</button></div></form></div>
    <div class="panel profile-card profile-security"><p class="eyebrow" style="color:var(--brand);">Seguridad</p><h1>Cambiar contrase&ntilde;a</h1><form method="post" action="/perfil/password" class="form-grid"><div class="field full"><label for="current_password">Contrase&ntilde;a actual</label><input id="current_password" name="current_password" type="password" autocomplete="current-password" required></div><div class="field"><label for="new_password">Nueva contrase&ntilde;a</label><input id="new_password" name="new_password" type="password" autocomplete="new-password" minlength="8" required></div><div class="field"><label for="confirm_password">Confirmar contrase&ntilde;a</label><input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" minlength="8" required></div><div class="actions"><button class="btn primary" type="submit">Actualizar contrase&ntilde;a</button></div></form></div>
    <section class="panel profile-card profile-reports"><div class="section-head" style="margin-top:0;"><div><h2>Mis reportes</h2><p>Reportes publicados con tu numero registrado.</p></div><a class="btn primary" href="/reportar">Nuevo reporte</a></div><?php if ($reportes): ?><div class="mini-list"><?php foreach ($reportes as $pet): ?><a class="mini-report" href="/mascotas/<?= e($pet['id']) ?>"><?php if ($pet['principal']): ?><img src="<?= e($pet['principal']) ?>" alt="<?= e($pet['nombre']) ?>"><?php else: ?><span class="mini-thumb"><?= e(first_letter($pet['nombre'] ?: '?')) ?></span><?php endif; ?><span><strong><?= e($pet['nombre']) ?></strong><br><span class="meta"><?= e(report_status_label($pet)) ?></span></span></a><?php endforeach; ?></div><?php else: ?><div class="empty">Todavia no tienes reportes publicados.</div><?php endif; ?></section>
  </section>
<?php }

function boost_plan_whatsapp_url(array $plan, string $shareUrl): string {
    $message = 'Hola me interesa impulsar mi reporte con el plan de ' . $plan['days'] . ' dias ' . $plan['price_label'] . ': ' . $shareUrl;
    return 'https://wa.me/526564252167?text=' . urlencode($message);
}

function render_boost_plan_options(string $shareUrl = ''): void { ?>
  <div class="boost-plans">
    <?php $defaultDays = default_boost_plan_days(); foreach (visible_boost_plans() as $plan): ?>
    <label class="boost-plan">
      <input type="radio" name="plan_dias" value="<?= e((string)$plan['days']) ?>" <?= (int)$plan['days'] === $defaultDays ? 'checked' : '' ?> <?= $shareUrl !== '' ? 'data-whatsapp-url="' . e(boost_plan_whatsapp_url($plan, $shareUrl)) . '"' : '' ?>>
      <span class="boost-plan-name"><?= e($plan['name']) ?></span>
      <span class="boost-plan-days"><?= e((string)$plan['days']) ?> dias</span>
      <span class="boost-plan-price"><?= e($plan['price_label']) ?></span>
      <ul><?php foreach ($plan['features'] as $feature): ?><li><?= e($feature) ?></li><?php endforeach; ?></ul>
      <span class="boost-plan-cta">Seleccionar plan</span>
    </label>
    <?php endforeach; ?>
  </div>
<?php }

function render_admin_boost_plan_switches(): void {
    foreach (boost_plans() as $plan):
        $days = (int)$plan['days'];
        ?>
        <form class="menu-setting" method="post" action="/admin/boost-plan">
            <input type="hidden" name="days" value="<?= e((string)$days) ?>">
            <input type="hidden" name="enabled" value="0">
            <input type="hidden" name="next" value="<?= e($_SERVER['REQUEST_URI'] ?? '/') ?>">
            <label class="switch">
                <span class="switch-text"><span>Plan <?= e((string)$days) ?> dias</span><small><?= boost_plan_enabled($days) ? 'Visible' : 'Oculto' ?></small></span>
                <input type="checkbox" name="enabled" value="1" <?= boost_plan_enabled($days) ? 'checked' : '' ?> onchange="this.form.submit()">
                <span class="switch-ui" aria-hidden="true"></span>
            </label>
        </form>
        <?php
    endforeach;
}

function view_admin_panel(): void { ?>
  <section class="admin-page">
    <div class="section-head"><div><p class="eyebrow" style="color:var(--brand);">Privado</p><h1>Administrar</h1><p>Controles internos de AyudaPet.</p></div><a class="btn ghost" href="/mapa-calor">Mapa de calor</a></div>
    <div class="admin-grid">
      <section class="panel admin-card">
        <div><h2>Impulso</h2><p class="meta">Controla si los usuarios pagan directo por PayPal o solicitan el impulso por WhatsApp.</p></div>
        <form class="menu-setting" method="post" action="/admin/boost-button"><input type="hidden" name="enabled" value="0"><input type="hidden" name="next" value="/admin"><label class="switch"><span class="switch-text"><span>Impulso automatico</span><small><?= boost_button_enabled() ? 'PayPal activo' : 'WhatsApp manual' ?></small></span><input type="checkbox" name="enabled" value="1" <?= boost_button_enabled() ? 'checked' : '' ?> onchange="this.form.submit()"><span class="switch-ui" aria-hidden="true"></span></label></form>
      </section>
      <section class="panel admin-card">
        <div><h2>Planes visibles</h2><p class="meta">Elige cuales planes aparecen en la pantalla de impulso.</p></div>
        <div class="admin-controls"><?php render_admin_boost_plan_switches(); ?></div>
      </section>
      <section class="panel admin-card">
        <div><h2>Donativos</h2><p class="meta">Controla el boton de donar y el modal de apoyo.</p></div>
        <form class="menu-setting" method="post" action="/admin/donate-button"><input type="hidden" name="enabled" value="0"><input type="hidden" name="next" value="/admin"><label class="switch"><span class="switch-text"><span>Boton donar</span><small><?= donate_button_enabled() ? 'Visible' : 'Oculto' ?></small></span><input type="checkbox" name="enabled" value="1" <?= donate_button_enabled() ? 'checked' : '' ?> onchange="this.form.submit()"><span class="switch-ui" aria-hidden="true"></span></label></form>
        <form class="menu-setting" method="post" action="/admin/donation-modal"><input type="hidden" name="enabled" value="0"><input type="hidden" name="next" value="/admin"><label class="switch"><span class="switch-text"><span>Modal donativo</span><small><?= donation_modal_enabled() ? 'Activo' : 'Apagado' ?></small></span><input type="checkbox" name="enabled" value="1" <?= donation_modal_enabled() ? 'checked' : '' ?> onchange="this.form.submit()"><span class="switch-ui" aria-hidden="true"></span></label></form>
      </section>
    </div>
  </section>
<?php }

function view_impulsar(array $mascota): void {
    $petName = trim((string)($mascota['nombre'] ?? ''));
    $title = 'Impulsa tu anuncio';
    $shareUrl = full_url('/m/' . pet_short_code($mascota));
    $whatsappUrl = boost_plan_whatsapp_url(boost_plan(default_boost_plan_days()), $shareUrl);
    ?>
    <section class="form-wrap boost-checkout-wrap">
        <div class="form-panel boost-checkout-panel">
            <div class="boost-product-media"><img src="<?= e(BOOST_PRODUCT_IMAGE_URL) ?>" alt="Impulsa tu anuncio en AyudaPet"></div>
            <div class="boost-product-info">
                <p class="eyebrow" style="color:var(--brand);">Impulso</p>
                <h1><?= e($title) ?></h1>
                <p class="meta">Destaca tu reporte en AyudaPet y aumenta su alcance enviandolo directamente a los dispositivos de personas en la zona afectada.</p>
                
                <?php if ($petName !== ''): ?><p class="boost-product-pet">Reporte: <strong><?= e($petName) ?></strong></p><?php endif; ?>
                <div class="boost-info-box">Elige el plan que mas se ajuste a tus necesidades.</div>

                <div class="actions">
                    <?php if (boost_button_enabled()): ?>
                    <form method="post" action="/mascotas/<?= e($mascota['id']) ?>/impulsar">
                        <input type="hidden" name="confirmar" value="1">
                        <?php render_boost_plan_options(); ?>
                        <button class="btn boost" type="submit">Continuar a PayPal</button>
                    </form>
                    <?php else: ?>
                    <?php render_boost_plan_options($shareUrl); ?>
                    <a class="btn whatsapp" href="<?= e($whatsappUrl) ?>" target="_blank" rel="noopener" data-boost-whatsapp>Pagar por WhatsApp</a>
                    <?php endif; ?>
                    <a class="btn ghost" href="/mascotas/<?= e($mascota['id']) ?>">Cancelar</a>
                </div>
            </div>
        </div>
    </section>
<?php }

function view_tipo_reporte(): void { ?>
  <div class="modal-page">
    <section class="panel report-type-modal" role="dialog" aria-modal="true" aria-labelledby="tipo-reporte-title">
      <p class="eyebrow" style="color:var(--brand);">Nuevo reporte</p>
      <h1 id="tipo-reporte-title">Que tipo de reporte quieres crear?</h1>
      <div class="report-type-actions">
        <a class="report-type-option" href="/reportar?reporte=extravio">
          <strong>Reporte de extravio</strong>
          <span>Mi mascota se perdio y necesito ayuda para encontrarla.</span>
        </a>
        <a class="report-type-option" href="/reportar?reporte=resguardo">
          <strong>Reporte de resguardo</strong>
          <span>Encontre una mascota y la tengo resguardada o ubicada, aunque no sepa su nombre.</span>
        </a>
      </div>
      <div class="actions"><a class="btn" href="/">Cancelar</a></div>
    </section>
  </div>
<?php }

function view_reportar(array $mascota, bool $editing, ?string $mapsApiKey): void {
    $secundarias = $editing ? pet_secondaries($mascota) : [];
    $slots = max(0, MAX_SECONDARY_IMAGES - count($secundarias));
    $tipoReporte = report_type_value($mascota['tipo_reporte'] ?? ($_GET['reporte'] ?? 'extravio'));
    $isResguardo = $tipoReporte === 'resguardo';
    $formTitle = $editing ? 'Editar reporte' : ($isResguardo ? 'Reporte de resguardo' : 'Reporte de extravio');
    $fechaLabel = $isResguardo ? 'Fecha de resguardo' : 'Fecha de extravio';
    $direccionLabel = $isResguardo ? 'Direccion donde se encontro' : 'Direccion de extravio';
    $nombrePlaceholder = $isResguardo ? 'Si no se sabe, dejalo en blanco' : '';
    $estadoLabel = 'En casa';
    $estadoHint = $isResguardo ? 'Activalo cuando la mascota ya fue entregada a su familia' : 'Activalo cuando la mascota ya volvio a casa';
    [$edadNumero, $edadUnidad] = age_input_parts($mascota['edad'] ?? '');
    $recompensaInput = money_input_value($mascota['recompensa'] ?? '');
    $collarActual = lower_text($mascota['collar'] ?? '');
    $docilActual = lower_text($mascota['docil'] ?? '');
    ?>
  <section class="form-wrap"><form class="form-panel" method="post" enctype="multipart/form-data" data-report-form><input type="hidden" name="tipo_reporte" value="<?= e($tipoReporte) ?>"><p class="eyebrow" style="color:var(--brand);"><?= $editing ? report_type_label($tipoReporte) : 'Nuevo reporte' ?></p><h1><?= e($formTitle) ?></h1><div class="form-grid">
    <div class="field full"><label for="principal">Foto principal</label><?php if ($editing && $mascota['principal']): ?><div class="edit-images"><div class="edit-image-item"><img src="<?= e($mascota['principal']) ?>" alt="Foto principal actual"><label class="remove-image-check" title="Quitar" data-remove-image data-remove-url="/mascotas/<?= e($mascota['id']) ?>/imagenes/eliminar" data-remove-target="principal"><input type="checkbox" name="remove_principal"><span>&times;</span></label></div></div><?php endif; ?><input id="principal" name="principal" type="file" accept="image/*"></div>
    <div class="field full"><label>Fotos adicionales</label><?php if ($secundarias): ?><div class="edit-image-grid"><?php foreach ($secundarias as $image): ?><div class="edit-image-item"><img src="<?= e($image) ?>" alt="Foto secundaria actual"><label class="remove-image-check" title="Quitar" data-remove-image data-remove-url="/mascotas/<?= e($mascota['id']) ?>/imagenes/eliminar" data-remove-target="secundaria" data-remove-image-url="<?= e($image) ?>"><input type="checkbox" name="remove_secundarias[]" value="<?= e($image) ?>"><span>&times;</span></label></div><?php endforeach; ?></div><?php endif; ?><input name="secundarias[]" type="file" accept="image/*" multiple data-max-files="<?= e($slots) ?>"><span class="hint">Puedes seleccionar hasta 3 imagenes adicionales.</span></div>
    <div class="field"><label for="fecha"><?= e($fechaLabel) ?></label><input id="fecha" name="fecha" type="date" value="<?= e($mascota['fecha'] ?? '') ?>"></div>
    <div class="field"><label for="nombre">Nombre de mascota</label><input id="nombre" name="nombre" value="<?= e(($isResguardo && ($mascota['nombre'] ?? '') === 'Sin nombre') ? '' : ($mascota['nombre'] ?? '')) ?>" placeholder="<?= e($nombrePlaceholder) ?>" <?= $isResguardo ? '' : 'required' ?>></div>
    <div class="field"><label for="tipo_mascota">Tipo de mascota</label><select id="tipo_mascota" name="tipo_mascota"><option value="">Seleccionar</option><?php foreach (['Perro','Gato','Otro'] as $opt): ?><option <?= ($mascota['tipo_mascota'] ?? '') === $opt ? 'selected' : '' ?>><?= e($opt) ?></option><?php endforeach; ?></select></div>
    <div class="field full"><label for="descripcion">Descripcion</label><textarea id="descripcion" name="descripcion" placeholder="Senales particulares, temperamento, ultima vez visto"><?= e($mascota['descripcion'] ?? '') ?></textarea></div>
    <div class="field"><label for="edad_numero">Edad</label><div class="inline-fields"><input id="edad_numero" name="edad_numero" type="number" min="1" step="1" inputmode="numeric" value="<?= e($edadNumero) ?>" placeholder="1"><select name="edad_unidad" aria-label="Unidad de edad"><option value="meses" <?= $edadUnidad === 'meses' ? 'selected' : '' ?>>Meses</option><option value="anos" <?= $edadUnidad === 'anos' ? 'selected' : '' ?>>Años</option></select></div></div>
    <?php input_field('raza','Raza',$mascota); ?>
    <div class="field"><label for="genero">Genero</label><select id="genero" name="genero"><option value="">Seleccionar</option><?php foreach (['Macho','Hembra','No se sabe'] as $opt): ?><option <?= ($mascota['genero'] ?? '') === $opt ? 'selected' : '' ?>><?= e($opt) ?></option><?php endforeach; ?></select></div>
    <?php input_field('color','Color',$mascota); ?>
    <div class="field"><label for="collar">Collar</label><select id="collar" name="collar"><option value="">Seleccionar</option><?php foreach (['Si','No'] as $opt): ?><option <?= $collarActual === lower_text($opt) || ($opt === 'Si' && $collarActual === 'sí') ? 'selected' : '' ?>><?= e($opt) ?></option><?php endforeach; ?></select></div>
    <div class="field"><label for="docil">Docil</label><select id="docil" name="docil"><option value="">Seleccionar</option><?php foreach (['Si','No'] as $opt): ?><option <?= $docilActual === lower_text($opt) || ($opt === 'Si' && $docilActual === 'sí') ? 'selected' : '' ?>><?= e($opt) ?></option><?php endforeach; ?></select></div>
    <div class="field full"><label for="direccion"><?= e($direccionLabel) ?></label><input id="direccion" name="direccion" value="<?= e($mascota['direccion'] ?? '') ?>" autocomplete="off" data-address-autocomplete><input type="hidden" name="direccion_completa" value="<?= e($mascota['direccion_completa'] ?? '') ?>" data-address-full><input type="hidden" name="ubicacion_lat" value="<?= e($mascota['ubicacion_lat'] ?? '') ?>" data-address-lat><input type="hidden" name="ubicacion_lng" value="<?= e($mascota['ubicacion_lng'] ?? '') ?>" data-address-lng></div>
    <?php if (!$isResguardo): ?><div class="field"><label for="recompensa">Recompensa</label><input id="recompensa" name="recompensa" type="number" min="0" step="1" inputmode="numeric" value="<?= e($recompensaInput) ?>" placeholder="1000" data-money-input><span class="hint" data-money-preview><?= e(money_display($recompensaInput) ?: 'Se mostrara como $1,000 M.N.') ?></span></div><?php endif; ?>
    <?php $usesOwnContact = !empty($mascota['contacto']) && !is_system_public_contact($mascota['contacto']); ?>
    <?php $registeredContactPhone = (string)(($mascota['reportado_por'] ?? '') ?: (current_user_phone() ?? '')); ?>
    <div class="field">
      <label>Contacto publico</label>
      <label class="switch">
        <span class="switch-text"><span>Usar mi contacto</span><small>Si esta apagado se usa AyudaPet <?= e(DEFAULT_PUBLIC_CONTACT) ?></small></span>
        <input type="checkbox" name="usar_contacto_propio" data-contact-toggle <?= $usesOwnContact ? 'checked' : '' ?>>
        <span class="switch-ui" aria-hidden="true"></span>
      </label>
    </div>
    <div class="field contact-own <?= $usesOwnContact ? 'show' : '' ?>" data-contact-own>
      <label for="contacto">Tu contacto</label>
      <input id="contacto" name="contacto" value="<?= e($usesOwnContact ? ($mascota['contacto'] ?? '') : '') ?>" placeholder="Telefono, WhatsApp o correo" data-contact-input data-registered-phone="<?= e($registeredContactPhone) ?>">
    </div>
    <div class="field">
      <label>Estado del reporte</label>
      <label class="switch">
        <span class="switch-text"><span><?= e($estadoLabel) ?></span><small><?= e($estadoHint) ?></small></span>
        <input type="checkbox" name="encontrado" <?= !empty($mascota['encontrado']) ? 'checked' : '' ?>>
        <span class="switch-ui" aria-hidden="true"></span>
      </label>
    </div>
  </div><div class="actions"><button class="btn primary" type="submit"><?= $editing ? 'Guardar cambios' : 'Publicar reporte' ?></button><a class="btn" href="<?= $editing ? '/mascotas/' . e($mascota['id']) : '/' ?>">Cancelar</a></div></form>
  <?php if ($mapsApiKey): ?><script>
    window.initAddressAutocomplete = function () {
      const input = document.querySelector("[data-address-autocomplete]");
      const fullInput = document.querySelector("[data-address-full]");
      const latInput = document.querySelector("[data-address-lat]");
      const lngInput = document.querySelector("[data-address-lng]");
      if (!input || !window.google?.maps?.places) return;
      const autocomplete = new google.maps.places.Autocomplete(input, {
        componentRestrictions: { country: "mx" },
        fields: ["address_components", "formatted_address", "geometry", "name"],
        types: ["address"],
      });
      input.addEventListener("input", () => {
        if (fullInput) fullInput.value = "";
      });

      const getPart = (parts, type, shortName = false) => {
        const item = parts.find((part) => part.types.includes(type));
        return item ? (shortName ? item.short_name : item.long_name) : "";
      };

      const stripExactAddress = (value) => {
        const raw = String(value || "").trim();
        if (!raw) return "";
        const parts = raw.split(",").map((part) => part.trim()).filter(Boolean);
        const exactPattern = /\d|\b(c\.?|calle|av\.?|avenida|blvd\.?|boulevard|privada|priv\.?|calz\.?|calzada|cerrada|cda\.?|camino|carretera|prolongacion|prol\.?)\b/i;
        const firstPartIsExact = exactPattern.test(parts[0] || raw);
        if (parts.length > 1 && firstPartIsExact) return parts.slice(1).join(", ");
        const areaMatch = raw.match(/\b(col\.?|colonia|fracc\.?|fraccionamiento|residencial|unidad|barrio)\b\s*(.+)$/i);
        if (areaMatch) return areaMatch[0].trim();
        return firstPartIsExact ? "" : raw;
      };

      const privateAddress = (place) => {
        const parts = place.address_components || [];
        const neighborhood =
          getPart(parts, "sublocality_level_1") ||
          getPart(parts, "sublocality") ||
          getPart(parts, "neighborhood") ||
          getPart(parts, "political");
        const postalCode = getPart(parts, "postal_code");
        const city =
          getPart(parts, "locality") ||
          getPart(parts, "administrative_area_level_2");
        const state = getPart(parts, "administrative_area_level_1", true);
        const country = getPart(parts, "country");
        const cityLine = [postalCode, city].filter(Boolean).join(" ");
        const safeParts = [neighborhood, cityLine, state, country].filter(Boolean);
        if (safeParts.length >= 2) return safeParts.join(", ");
        const formattedParts = (place.formatted_address || "").split(",").map((part) => part.trim()).filter(Boolean);
        if (formattedParts.length > 2) return formattedParts.slice(1).join(", ");
        return stripExactAddress(place.name || input.value) || stripExactAddress(place.formatted_address) || input.value;
      };

      const closeSuggestions = () => {
        input.blur();
        document.querySelectorAll(".pac-container").forEach((container) => {
          container.style.display = "none";
        });
      };

      const openSuggestions = () => {
        document.querySelectorAll(".pac-container").forEach((container) => {
          container.style.display = "";
        });
      };

      const setCoordinates = (place) => {
        if (!latInput || !lngInput) return;
        const location = place.geometry?.location;
        if (!location) {
          latInput.value = "";
          lngInput.value = "";
          return;
        }
        latInput.value = Number(location.lat()).toFixed(3);
        lngInput.value = Number(location.lng()).toFixed(3);
      };

      let selectedPrivateAddress = input.value;

      const applySelectedPlace = () => {
        const place = autocomplete.getPlace();
        if (!place || (!place.address_components && !place.formatted_address && !place.name)) {
          closeSuggestions();
          return;
        }
        const fullAddress = place.formatted_address || place.name || input.value || "";
        const safeAddress = privateAddress(place);
        if (fullInput) {
          fullInput.value = fullAddress;
        }
        selectedPrivateAddress = safeAddress;
        input.value = safeAddress;
        setCoordinates(place);
        window.setTimeout(() => {
          if (fullInput) fullInput.value = fullAddress;
          input.value = safeAddress;
          closeSuggestions();
        }, 80);
        input.dispatchEvent(new Event("change", { bubbles: true }));
        closeSuggestions();
      };

      autocomplete.addListener("place_changed", applySelectedPlace);
      input.addEventListener("input", () => {
        if (input.value !== selectedPrivateAddress) {
          if (latInput) latInput.value = "";
          if (lngInput) lngInput.value = "";
          openSuggestions();
        }
      });
      input.addEventListener("focus", openSuggestions);
      input.addEventListener("blur", () => {
        window.setTimeout(() => {
          document.querySelectorAll(".pac-container").forEach((container) => {
            container.style.display = "none";
          });
        }, 120);
      });
    };
  </script><script src="https://maps.googleapis.com/maps/api/js?key=<?= urlencode($mapsApiKey) ?>&libraries=places&callback=initAddressAutocomplete" async defer></script><?php endif; ?>
  </section>
<?php }

function view_mapa_calor(array $reports, array $stats, ?string $mapsApiKey, array $cityContacts): void {
    $points = [];
    foreach ($reports as $report) {
        $lat = (float)$report['ubicacion_lat'];
        $lng = (float)$report['ubicacion_lng'];
        if (!$lat || !$lng) continue;
        $points[] = [
            'lat' => $lat,
            'lng' => $lng,
            'nombre' => (string)($report['nombre'] ?? 'Reporte'),
            'direccion' => (string)(($report['direccion_completa'] ?? '') ?: ($report['direccion'] ?? '')),
            'imagen' => (string)($report['principal'] ?? ''),
            'tipo' => report_type_value($report['tipo_reporte'] ?? ''),
        ];
    }
    $centerLat = $points ? array_sum(array_column($points, 'lat')) / count($points) : 31.6904;
    $centerLng = $points ? array_sum(array_column($points, 'lng')) / count($points) : -106.4245;
    ?>
  <section class="heatmap-page">
    <div class="section-head"><div><p class="eyebrow" style="color:var(--brand);">Privado</p><h1>Mapa de calor</h1><p>Incidencias guardadas desde reportes activos y archivados.</p></div></div>
    <section class="stats heatmap-stats">
      <div class="stat"><strong><?= e($stats['total']) ?></strong><span>puntos</span></div>
      <div class="stat"><strong><?= e($stats['extravio']) ?></strong><span>extravios</span></div>
      <div class="stat"><strong><?= e($stats['resguardo']) ?></strong><span>resguardos</span></div>
      <div class="stat"><strong><?= e($stats['en_casa']) ?></strong><span>en casa</span></div>
    </section>
    <section class="panel heatmap-panel">
      <?php if ($mapsApiKey && $points): ?><div id="heatmap" class="heatmap-canvas"></div><?php elseif (!$mapsApiKey): ?><div class="empty">Falta API_KEY en el .env para cargar Google Maps.</div><?php else: ?><div class="empty">Todavia no hay reportes con coordenadas para mostrar.</div><?php endif; ?>
    </section>
    <section class="panel heatmap-list">
      <div class="section-head" style="margin-top:0;"><div><h2>Ultimas ubicaciones</h2><p>Datos privados para seguimiento interno.</p></div></div>
      <?php if ($reports): ?><div class="mini-list"><?php foreach (array_slice($reports, 0, 40) as $report): ?><div class="mini-report"><?php if (!empty($report['principal'])): ?><img src="<?= e($report['principal']) ?>" alt="<?= e($report['nombre'] ?: 'Reporte') ?>"><?php else: ?><span class="mini-thumb"><?= e(first_letter($report['nombre'] ?? '?')) ?></span><?php endif; ?><span><strong><?= e($report['nombre'] ?: 'Reporte') ?></strong><span class="meta"><?= e(report_type_value($report['tipo_reporte'] ?? '') === 'resguardo' ? 'Resguardo' : 'Extravio') ?> · <?= e(($report['direccion_completa'] ?? '') ?: ($report['direccion'] ?? 'Sin direccion')) ?></span></span></div><?php endforeach; ?></div><?php else: ?><div class="empty">Todavia no hay ubicaciones archivadas.</div><?php endif; ?>
    </section>
    <section class="panel sms-panel">
      <div class="section-head" style="margin-top:0;"><div><h2>Telefonos por zona</h2><p>Busca numeros registrados por ciudad, estado, colonia o codigo postal.</p></div></div>
      <form class="search-form sms-search" method="get" action="/mapa-calor" data-sms-search>
        <div class="field"><label for="ciudad">Ciudad, estado, colonia o CP</label><input id="ciudad" name="ciudad" value="<?= e($cityContacts['city'] ?? '') ?>" placeholder="Ej. Juarez, Chihuahua, 32177"></div>
        <button class="btn primary" type="submit">Buscar telefonos</button>
      </form>
      <div data-sms-results>
      <?php if (($cityContacts['city'] ?? '') !== ''): ?>
        <p class="filter-meta"><?= count($cityContacts['contacts']) ?> telefono<?= count($cityContacts['contacts']) === 1 ? '' : 's' ?> para <?= e($cityContacts['city']) ?><?= !empty($cityContacts['source']) ? ' · ' . e($cityContacts['source']) : '' ?>.</p>
        <?php if ($cityContacts['contacts']): ?>
          <textarea class="sms-copy-box" readonly data-sms-copy><?= e($cityContacts['sms']) ?></textarea>
          <div class="actions"><button class="btn share" type="button" data-copy-sms>Copiar telefonos para SMS</button></div>
          <div class="sms-contact-list"><?php foreach (array_slice($cityContacts['contacts'], 0, 80) as $contact): ?><div class="sms-contact"><strong><?= e($contact['sms']) ?></strong><span><?= e($contact['direccion']) ?></span></div><?php endforeach; ?></div>
        <?php else: ?><div class="empty">No encontre telefonos asociados a esa ciudad.</div><?php endif; ?>
      <?php endif; ?>
      </div>
    </section>
  </section>
  <?php if ($mapsApiKey && $points): ?><script>
    window.initHeatmap = function () {
      const points = <?= json_encode($points, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) ?>;
      const escapeHtml = (value) => String(value || "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
      const map = new google.maps.Map(document.getElementById("heatmap"), {
        center: { lat: <?= json_encode($centerLat) ?>, lng: <?= json_encode($centerLng) ?> },
        zoom: points.length > 1 ? 12 : 14,
        mapTypeId: "roadmap",
        streetViewControl: false,
        fullscreenControl: true,
      });
      const popupFor = (point) => {
        const image = point.imagen ? `<img class="map-popup-img" src="${escapeHtml(point.imagen)}" alt="${escapeHtml(point.nombre)}">` : "";
        return new google.maps.InfoWindow({
          content: `<div class="map-popup">${image}<strong>${escapeHtml(point.nombre)}</strong><span>${escapeHtml(point.direccion)}</span></div>`,
          maxWidth: 230,
        });
      };
      let activeInfo = null;
      let activeCircle = null;
      points.slice(0, 120).forEach((point, index) => {
        const marker = new google.maps.Marker({
          position: { lat: point.lat, lng: point.lng },
          map,
          title: point.nombre,
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 7,
            fillColor: "#e85035",
            fillOpacity: 1,
            strokeColor: "#ffffff",
            strokeWeight: 2,
          },
        });
        const info = popupFor(point);
        info.addListener("closeclick", () => {
          if (activeInfo === info) activeInfo = null;
          if (activeCircle) {
            activeCircle.setMap(null);
            activeCircle = null;
          }
        });
        marker.addListener("click", () => {
          if (activeInfo) activeInfo.close();
          if (activeCircle) activeCircle.setMap(null);
          activeCircle = new google.maps.Circle({
            strokeColor: "#e85035",
            strokeOpacity: 0.45,
            strokeWeight: 1,
            fillColor: "#e85035",
            fillOpacity: 0.22,
            map,
            center: { lat: point.lat, lng: point.lng },
            radius: 1600,
          });
          activeInfo = info;
          info.open({ anchor: marker, map });
        });
      });
    };
  </script><script src="https://maps.googleapis.com/maps/api/js?key=<?= urlencode($mapsApiKey) ?>&callback=initHeatmap" async defer></script><?php endif; ?>
<?php }

function input_field(string $name, string $label, array $data, string $placeholder = ''): void {
    echo '<div class="field"><label for="' . e($name) . '">' . e($label) . '</label><input id="' . e($name) . '" name="' . e($name) . '" value="' . e($data[$name] ?? '') . '" placeholder="' . e($placeholder) . '"></div>';
}

function view_error(string $title, string $message): void { ?>
  <section class="form-wrap"><div class="form-panel"><p class="eyebrow" style="color:var(--brand);">Aviso</p><h1><?= e($title) ?></h1><p class="meta"><?= e($message) ?></p><div class="actions"><a class="btn primary" href="/">Volver al inicio</a></div></div></section>
<?php }

function render_mascota_detail_page(array $pet, bool $skipViewIncrement = false): void {
    if (!$skipViewIncrement) {
        increment_report_views($pet['id']);
        $pet['vistas'] = ((int)($pet['vistas'] ?? 0)) + 1;
    }
    $status = report_status_label($pet);
    $detailUrl = full_url('/mascotas/' . $pet['id']);
    $shareUrl = full_url('/m/' . pet_short_code($pet));
    $mapUrl = null;
    $mapAddress = (is_admin_user() && !empty($pet['direccion_completa'])) ? $pet['direccion_completa'] : ($pet['direccion'] ?? '');
    if (envv('API_KEY') && $mapAddress) {
        $mapUrl = 'https://www.google.com/maps/embed/v1/place?key=' . urlencode(envv('API_KEY')) . '&q=' . urlencode($mapAddress . ', Mexico');
    }
    render('detalle', [
        'title' => "{$pet['nombre']} - {$status} | AyudaPet",
        'metaTitle' => "{$pet['nombre']} - {$status} | AyudaPet",
        'metaDescription' => ($pet['descripcion'] ?: 'Reporte de mascota en AyudaPet.') . ($pet['direccion'] ? ' Ubicacion: ' . $pet['direccion'] . '.' : ''),
        'metaUrl' => $shareUrl,
        'canonicalUrl' => $detailUrl,
        'metaImage' => pet_social_image($pet),
        'metaImageAlt' => 'Foto de ' . ($pet['nombre'] ?: 'mascota') . ' en AyudaPet',
        'ogType' => 'article',
        'mascota' => $pet,
        'isOwner' => owns_report($pet),
        'canManage' => can_manage_report($pet),
        'mapUrl' => $mapUrl,
        'share' => ['url' => $shareUrl, 'text' => "{$status}: {$pet['nombre']} en AyudaPet", 'message' => "{$status}: {$pet['nombre']} en AyudaPet"],
    ]);
}

function route(): void {
    $method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
    $path = path_only();

    try {
        if ($path === '/cron/boosts') {
            $secret = envv('CRON_SECRET');
            $token = (string)($_GET['token'] ?? '');
            if (!$secret || !$token || !hash_equals($secret, $token)) {
                render('error', ['title' => 'Sin permiso', 'message' => 'Token de cron invalido.'], 403);
                return;
            }
            $result = process_expired_boosts();
            $archives = sync_report_archives();
            header('Content-Type: text/plain; charset=UTF-8');
            echo 'boost_checked=' . $result['checked'] . ' boost_sent=' . $result['sent'] . ' boost_failed=' . $result['failed']
                . ' archive_checked=' . $archives['checked'] . ' archive_synced=' . $archives['synced'] . ' archive_failed=' . $archives['failed'];
            return;
        }

        if ($path === '/mapa-calor') {
            require_login();
            if (!is_admin_user()) {
                render('error', ['title' => 'Sin permiso', 'message' => 'Esta pagina es privada.'], 403);
                return;
            }
            sync_report_archives();
            $heatmap = heatmap_reports();
            render('mapa_calor', [
                'title' => 'Mapa de calor',
                'reports' => $heatmap['reports'],
                'stats' => $heatmap['stats'],
                'mapsApiKey' => envv('API_KEY'),
                'cityContacts' => heatmap_city_contacts($_GET['ciudad'] ?? ''),
            ]);
            return;
        }

        if ($path === '/mapa-calor/contactos') {
            require_login();
            header('Content-Type: application/json; charset=UTF-8');
            if (!is_admin_user()) {
                http_response_code(403);
                echo json_encode(['ok' => false, 'message' => 'Sin permiso']);
                return;
            }
            $contacts = heatmap_city_contacts($_GET['ciudad'] ?? '');
            echo json_encode(['ok' => true] + $contacts, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
            return;
        }

        if ($path === '/admin') {
            require_login();
            if (!is_admin_user()) {
                render('error', ['title' => 'Sin permiso', 'message' => 'Esta pagina es privada.'], 403);
                return;
            }
            render('admin', ['title' => 'Administrar AyudaPet']);
            return;
        }

        if ($path === '/') {
            $pets = list_mascotas();
            $q = trim((string)($_GET['q'] ?? ''));
            $estado = strtolower(trim((string)($_GET['estado'] ?? 'todos')));
            if ($estado === 'localizados') $estado = 'en_casa';
            if (!in_array($estado, ['todos', 'perdidos', 'resguardo', 'en_casa'], true)) $estado = 'todos';
            $stats = [
                'total' => count($pets),
                'activos' => count(array_filter($pets, function ($p) { return !$p['encontrado']; })),
                'encontrados' => count(array_filter($pets, function ($p) { return $p['encontrado']; })),
            ];
            if ($estado === 'perdidos') {
                $pets = array_values(array_filter($pets, function ($p) { return !$p['encontrado'] && report_type_value($p['tipo_reporte'] ?? '') === 'extravio'; }));
            }
            if ($estado === 'resguardo') {
                $pets = array_values(array_filter($pets, function ($p) { return !$p['encontrado'] && report_type_value($p['tipo_reporte'] ?? '') === 'resguardo'; }));
            }
            if ($estado === 'en_casa') {
                $pets = array_values(array_filter($pets, function ($p) { return $p['encontrado']; }));
            }
            if ($q !== '') {
                $needle = lower_text($q);
                $pets = array_values(array_filter($pets, function ($p) use ($needle) {
                    return contains_text(lower_text(implode(' ', [$p['nombre'], $p['tipo_mascota'] ?? '', $p['descripcion'], $p['direccion'], $p['calles'], $p['contacto']])), $needle);
                }));
            }
            render('index', ['title' => APP_NAME, 'mascotas' => $pets, 'stats' => $stats, 'filters' => ['q' => $q, 'estado' => $estado, 'resultados' => count($pets)]]);
            return;
        }

        if ($path === '/terminos') {
            render('terminos', [
                'title' => 'Términos y condiciones',
                'metaTitle' => 'Términos y condiciones de AyudaPet',
                'metaDescription' => 'Consulta los términos, condiciones, privacidad y consentimiento SMS de AyudaPet.',
                'canonicalUrl' => '/terminos',
                'metaUrl' => '/terminos',
            ]);
            return;
        }

        if ($path === '/registro') {
            if ($method === 'POST') {
                $phone = normalize_phone($_POST['tel'] ?? '');
                if (!$phone) { flash('Escribe un numero mexicano valido.', 'error'); redirect_to('/registro'); }
                if (($_POST['acepta_terminos'] ?? '') !== '1') {
                    flash('Debes aceptar los terminos y condiciones para crear tu cuenta.', 'error');
                    redirect_to('/registro');
                }
                [$sent, $dev] = create_otp($phone);
                $_SESSION['pending_tel'] = $phone;
                $_SESSION['pending_terms_accepted'] = true;
                $_SESSION['pending_sms_consent'] = true;
                if (!$sent) flash('No se pudo enviar el SMS. Revisa LabsMobile en Coolify.', 'error');
                if ($dev) flash("Codigo de desarrollo: {$dev}", 'info');
                redirect_to('/verificar');
            }
            render('registro', ['title' => 'Crear cuenta']);
            return;
        }

        if ($path === '/verificar') {
            $phone = $_SESSION['pending_tel'] ?? null;
            if (!$phone) redirect_to('/registro');
            if ($method === 'POST') {
                if (verify_otp($phone, (string)($_POST['code'] ?? ''))) {
                    $_SESSION['verified_tel'] = $phone;
                    redirect_to('/set_password');
                }
                flash('Codigo invalido o expirado.', 'error');
            }
            render('verificar', ['title' => 'Verificar', 'phone' => $phone]);
            return;
        }

        if ($path === '/recuperar') {
            if ($method === 'POST') {
                $phone = normalize_phone($_POST['tel'] ?? '');
                if (!$phone || !get_user($phone)) { flash('Ese telefono no esta registrado.', 'error'); redirect_to('/recuperar'); }
                [$sent, $dev] = create_otp($phone);
                $_SESSION['pending_tel'] = $phone;
                if (!$sent) flash('No se pudo enviar el SMS. Revisa LabsMobile en Coolify.', 'error');
                if ($dev) flash("Codigo de desarrollo: {$dev}", 'info');
                redirect_to('/verificar');
            }
            render('recuperar', ['title' => 'Restablecer contrasena']);
            return;
        }

        if ($path === '/set_password') {
            $phone = $_SESSION['verified_tel'] ?? null;
            if (!$phone) redirect_to('/registro');
            $recovering = (bool)get_user($phone);
            if ($method === 'POST') {
                $pwd = (string)($_POST['pwd'] ?? '');
                if (strlen($pwd) < 8) { flash('La contrasena debe tener al menos 8 caracteres.', 'error'); redirect_to('/set_password'); }
                save_user($phone, $pwd, $recovering ? null : post_value('nombre'), !$recovering && !empty($_SESSION['pending_terms_accepted']), !$recovering && !empty($_SESSION['pending_sms_consent']));
                unset($_SESSION['pending_tel'], $_SESSION['verified_tel'], $_SESSION['pending_terms_accepted'], $_SESSION['pending_sms_consent']);
                $_SESSION['tel'] = $phone;
                flash($recovering ? 'Contrasena actualizada.' : 'Cuenta creada correctamente.', 'success');
                redirect_to('/');
            }
            render('set_password', ['title' => 'Cuenta', 'phone' => $phone, 'recovering' => $recovering]);
            return;
        }

        if ($path === '/login') {
            if ($method === 'POST') {
                $phone = normalize_phone($_POST['tel'] ?? '');
                $user = $phone ? get_user($phone) : null;
                if (!$user || !password_verify((string)($_POST['pwd'] ?? ''), $user['password_hash'])) {
                    flash('Telefono o contrasena incorrectos.', 'error'); redirect_to('/login');
                }
                $_SESSION['tel'] = $phone;
                redirect_to(safe_next($_GET['next'] ?? '/'));
            }
            render('login', ['title' => 'Entrar']);
            return;
        }

        if ($path === '/logout') {
            session_destroy();
            session_start();
            flash('Sesion cerrada.', 'success');
            redirect_to('/');
        }

        if ($path === '/admin/boost-button' && $method === 'POST') {
            require_login();
            if (!is_admin_user()) {
                render('error', ['title' => 'Sin permiso', 'message' => 'Esta accion es privada.'], 403);
                return;
            }
            $enabled = ($_POST['enabled'] ?? '0') === '1';
            set_app_setting('boost_button_enabled', $enabled ? 'true' : 'false');
            flash($enabled ? 'Boton de impulso activado.' : 'Boton de impulso desactivado.', 'success');
            redirect_to(safe_next($_POST['next'] ?? '/'));
        }

        if ($path === '/admin/boost-plan' && $method === 'POST') {
            require_login();
            if (!is_admin_user()) {
                render('error', ['title' => 'Sin permiso', 'message' => 'Esta accion es privada.'], 403);
                return;
            }
            $days = (int)($_POST['days'] ?? 0);
            if (!array_key_exists($days, boost_plans())) {
                flash('Plan no valido.', 'error');
                redirect_to(safe_next($_POST['next'] ?? '/'));
            }
            $enabled = ($_POST['enabled'] ?? '0') === '1';
            if (!$enabled && boost_plan_enabled($days) && count(visible_boost_plans()) <= 1) {
                flash('Debe quedar al menos un plan visible.', 'warning');
                redirect_to(safe_next($_POST['next'] ?? '/'));
            }
            set_app_setting('boost_plan_' . $days . '_enabled', $enabled ? 'true' : 'false');
            flash($enabled ? 'Plan de ' . $days . ' dias visible.' : 'Plan de ' . $days . ' dias oculto.', 'success');
            redirect_to(safe_next($_POST['next'] ?? '/'));
        }

        if ($path === '/admin/donate-button' && $method === 'POST') {
            require_login();
            if (!is_admin_user()) {
                render('error', ['title' => 'Sin permiso', 'message' => 'Esta accion es privada.'], 403);
                return;
            }
            $enabled = ($_POST['enabled'] ?? '0') === '1';
            set_app_setting('donate_button_enabled', $enabled ? 'true' : 'false');
            flash($enabled ? 'Boton de donar activado.' : 'Boton de donar oculto.', 'success');
            redirect_to(safe_next($_POST['next'] ?? '/'));
        }

        if ($path === '/admin/donation-modal' && $method === 'POST') {
            require_login();
            if (!is_admin_user()) {
                render('error', ['title' => 'Sin permiso', 'message' => 'Esta accion es privada.'], 403);
                return;
            }
            $enabled = ($_POST['enabled'] ?? '0') === '1';
            set_app_setting('donation_modal_enabled', $enabled ? 'true' : 'false');
            flash($enabled ? 'Modal de donativos activado.' : 'Modal de donativos apagado.', 'success');
            redirect_to(safe_next($_POST['next'] ?? '/'));
        }

        if ($path === '/perfil') {
            require_login();
            $user = get_user(current_user_phone());
            if ($method === 'POST') {
                $foto = null;
                if (isset($_FILES['foto'])) $foto = upload_image($_FILES['foto'], 'perfiles/' . current_user_phone(), 'perfil');
                db()->prepare('UPDATE usuarios SET nombre = ?, foto = COALESCE(?, foto) WHERE telefono = ?')->execute([post_value('nombre'), $foto, current_user_phone()]);
                flash('Perfil actualizado.', 'success'); redirect_to('/perfil');
            }
            render('perfil', ['title' => 'Mi perfil', 'user' => $user, 'reportes' => list_user_reports(current_user_phone())]);
            return;
        }

        if ($path === '/perfil/password' && $method === 'POST') {
            require_login();
            $user = get_user(current_user_phone());
            if (!$user || !password_verify((string)($_POST['current_password'] ?? ''), $user['password_hash'])) { flash('La contrasena actual no coincide.', 'error'); redirect_to('/perfil'); }
            if (($_POST['new_password'] ?? '') !== ($_POST['confirm_password'] ?? '') || strlen((string)($_POST['new_password'] ?? '')) < 8) { flash('Revisa la nueva contrasena.', 'error'); redirect_to('/perfil'); }
            db()->prepare('UPDATE usuarios SET password_hash = ? WHERE telefono = ?')->execute([password_hash((string)$_POST['new_password'], PASSWORD_DEFAULT), current_user_phone()]);
            flash('Contrasena actualizada.', 'success'); redirect_to('/perfil');
        }

        if ($path === '/correo/prueba') {
            require_login();
            [$sent, $message] = send_notification_email('Prueba de correo AyudaPet', [
                'Esta es una prueba de correo desde AyudaPet.',
                '',
                'Usuario de prueba: ' . current_user_phone(),
                'Fecha: ' . date('Y-m-d H:i:s'),
            ]);
            render('error', [
                'title' => $sent ? 'Correo enviado' : 'Correo no enviado',
                'message' => $message,
            ], $sent ? 200 : 500);
            return;
        }

        if ($path === '/paypal/return') {
            require_login();
            $petId = (string)($_GET['pet_id'] ?? '');
            $orderId = (string)($_GET['token'] ?? '');
            if (!$petId || !$orderId) {
                flash('PayPal no regreso los datos completos del pago.', 'error');
                redirect_to('/');
            }
            $pet = get_mascota($petId);
            if (!$pet || !can_manage_report($pet)) {
                render('error', ['title' => 'Sin permiso', 'message' => 'No puedes confirmar este impulso.'], 403);
                return;
            }
            try {
                $confirmed = capture_paypal_boost($petId, $orderId);
                flash($confirmed ? 'Tu anuncio ya esta impulsado.' : 'No se pudo confirmar el pago de PayPal.', $confirmed ? 'success' : 'error');
            } catch (Throwable $e) {
                error_log('No se pudo capturar impulso PayPal: ' . $e->getMessage());
                flash('No se pudo confirmar el pago de PayPal. Intenta de nuevo o contactanos.', 'error');
            }
            redirect_to('/mascotas/' . $petId);
        }

        if ($path === '/paypal/cancel') {
            require_login();
            $petId = (string)($_GET['pet_id'] ?? '');
            flash('Pago cancelado. Tu reporte no fue impulsado.', 'warning');
            redirect_to($petId ? '/mascotas/' . $petId : '/');
        }

        if ($path === '/reportar') {
            require_login();
            if ($method === 'POST') {
                $postType = report_type_value(post_value('tipo_reporte'));
                try { create_report(); flash('Reporte publicado correctamente.', 'success'); redirect_to('/'); }
                catch (RuntimeException $e) { flash($e->getMessage(), 'error'); redirect_to('/reportar?reporte=' . $postType); }
            }
            $reportType = $_GET['reporte'] ?? '';
            if (!in_array($reportType, ['extravio', 'resguardo'], true)) {
                render('tipo_reporte', ['title' => 'Nuevo reporte']);
                return;
            }
            render('reportar', ['title' => 'Reportar mascota', 'mascota' => ['tipo_reporte' => $reportType], 'editing' => false, 'mapsApiKey' => envv('API_KEY')]);
            return;
        }

        if (preg_match('#^/mascotas/([a-fA-F0-9]{32})/vistas$#', $path, $m) && $method === 'POST') {
            require_login();
            if (!is_admin_user()) { render('error', ['title' => 'Sin permiso', 'message' => 'Esta accion es privada.'], 403); return; }
            $petId = strtolower($m[1]);
            $pet = get_mascota($petId);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El reporte solicitado no existe.'], 404); return; }
            $views = max(0, (int)preg_replace('/\D/', '', (string)($_POST['vistas'] ?? '0')));
            db()->prepare('UPDATE mascotas SET vistas = ? WHERE id = ?')->execute([$views, $pet['id']]);
            flash('Vistas actualizadas.', 'success');
            redirect_to('/mascotas/' . $pet['id'] . '?sin_contar_vista=1');
        }
        if (preg_match('#^/m/([a-f0-9]{8,16})$#', $path, $m)) {
            $pet = get_mascota_by_short_code($m[1]);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El enlace corto no existe o ya no esta disponible.'], 404); return; }
            render_mascota_detail_page($pet);
            return;
        }

        if (preg_match('#^/mascotas/([a-f0-9]{32})$#', $path, $m)) {
            $pet = get_mascota($m[1]);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El reporte solicitado no existe.'], 404); return; }
            $skipViewIncrement = is_admin_user() && (($_GET['sin_contar_vista'] ?? '') === '1');
            render_mascota_detail_page($pet, $skipViewIncrement);
            return;
        }

        if (preg_match('#^/mascotas/([a-f0-9]{32})/impulsar$#', $path, $m)) {
            require_login();
            $pet = get_mascota($m[1]);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El reporte solicitado no existe.'], 404); return; }
            if (!can_manage_report($pet)) { render('error', ['title' => 'Sin permiso', 'message' => 'Solo puedes impulsar reportes que administras.'], 403); return; }
            if (is_boosted($pet)) { flash('Este reporte ya esta impulsado.', 'success'); redirect_to('/mascotas/' . $pet['id']); }
            if ($method !== 'POST' || ($_POST['confirmar'] ?? '') !== '1') {
                render('impulsar', [
                    'title' => 'Impulsa tu anuncio',
                    'mascota' => $pet,
                    'metaImage' => BOOST_PRODUCT_IMAGE_URL,
                    'metaDescription' => 'Destaca tu reporte en AyudaPet y aumenta su alcance en la zona afectada.',
                ]);
                return;
            }
            if (!boost_button_enabled()) { flash('Continuaremos el impulso por WhatsApp.', 'warning'); redirect_to('/mascotas/' . $pet['id'] . '/impulsar'); }
            $checkoutUrl = create_boost_checkout($pet, boost_plan_days($_POST['plan_dias'] ?? BOOST_DAYS));
            redirect_to($checkoutUrl);
        }


        if (preg_match('#^/mascotas/([a-f0-9]{32})/impulso-manual$#', $path, $m) && $method === 'POST') {
            require_login();
            if (!is_admin_user()) { render('error', ['title' => 'Sin permiso', 'message' => 'Esta accion es privada.'], 403); return; }
            $pet = get_mascota($m[1]);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El reporte solicitado no existe.'], 404); return; }
            $enabled = ($_POST['enabled'] ?? '0') === '1';
            if ($enabled) {
                $dias = boost_plan_days($_POST['dias'] ?? default_boost_plan_days());
                db()->prepare('UPDATE mascotas SET impulsado_hasta = DATE_ADD(NOW(), INTERVAL ' . $dias . ' DAY), paypal_order_id = NULL, paypal_payment_status = ?, paypal_boost_days = ?, boost_expired_notified_at = NULL WHERE id = ?')
                    ->execute(['manual', $dias, $pet['id']]);
                flash('Impulso manual activado por ' . $dias . ' dias.', 'success');
            } else {
                db()->prepare('UPDATE mascotas SET impulsado_hasta = NULL, paypal_order_id = NULL, paypal_payment_status = NULL, paypal_boost_days = NULL, boost_expired_notified_at = NULL WHERE id = ?')
                    ->execute([$pet['id']]);
                flash('Impulso manual desactivado.', 'success');
            }
            redirect_to('/mascotas/' . $pet['id']);
        }

        if (preg_match('#^/mascotas/([a-f0-9]{32})/editar$#', $path, $m)) {
            require_login();
            $pet = get_mascota($m[1]);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El reporte solicitado no existe.'], 404); return; }
            if (!can_manage_report($pet)) { render('error', ['title' => 'Sin permiso', 'message' => 'No puedes editar este reporte.'], 403); return; }
            if ($method === 'POST') {
                try { update_report($pet['id'], $pet); flash('Reporte actualizado correctamente.', 'success'); redirect_to('/mascotas/' . $pet['id']); }
                catch (RuntimeException $e) { flash($e->getMessage(), 'error'); redirect_to('/mascotas/' . $pet['id'] . '/editar'); }
            }
            render('reportar', ['title' => 'Editar reporte', 'mascota' => $pet, 'editing' => true, 'mapsApiKey' => envv('API_KEY')]);
            return;
        }

        if (preg_match('#^/mascotas/([a-f0-9]{32})/eliminar$#', $path, $m) && $method === 'POST') {
            require_login();
            $pet = get_mascota($m[1]);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El reporte solicitado no existe.'], 404); return; }
            if (!can_manage_report($pet)) { render('error', ['title' => 'Sin permiso', 'message' => 'No puedes eliminar este reporte.'], 403); return; }
            ensure_archive_table();
            $pdo = db();
            try {
                $pdo->beginTransaction();
                archive_report($pet, 'deleted_by_owner');
                $pdo->prepare('DELETE FROM mascotas WHERE id = ? AND reportado_por = ?')->execute([$pet['id'], $pet['reportado_por']]);
                $pdo->commit();
                flash('Reporte eliminado. La informacion quedo archivada para historial y mapa de calor.', 'success');
            } catch (Throwable $e) {
                if ($pdo->inTransaction()) $pdo->rollBack();
                flash('No se pudo eliminar el reporte porque no se pudo archivar la informacion.', 'error');
                redirect_to('/mascotas/' . $pet['id']);
            }
            redirect_to('/');
        }

        if (preg_match('#^/mascotas/([a-f0-9]{32})/imagenes/eliminar$#', $path, $m) && $method === 'POST') {
            require_login();
            $pet = get_mascota($m[1]);
            header('Content-Type: application/json');
            if (!$pet || !can_manage_report($pet)) { http_response_code(403); echo json_encode(['ok' => false]); return; }
            $raw = file_get_contents('php://input');
            $data = json_decode($raw ?: '{}', true) ?: $_POST;
            try { remove_report_image($pet['id'], $pet, (string)($data['target'] ?? ''), $data['image'] ?? null); echo json_encode(['ok' => true]); }
            catch (RuntimeException $e) { http_response_code(400); echo json_encode(['ok' => false, 'message' => $e->getMessage()]); }
            return;
        }

        render('error', ['title' => 'Pagina no encontrada', 'message' => 'La ruta solicitada no existe.'], 404);
    } catch (Throwable $e) {
        error_log($e->getMessage());
        render('error', ['title' => 'No se pudo cargar AyudaPet', 'message' => 'Revisa la configuracion de PHP/MySQL en el hosting. Detalle: ' . $e->getMessage()], 500);
    }
}

if (!defined('AYUDAPET_SKIP_ROUTE')) {
    route();
}
