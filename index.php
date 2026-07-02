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
const DEFAULT_PUBLIC_CONTACT = '+526567787712';
const DEFAULT_ADMIN_PHONE = '6567787712';
const BOOST_DAYS = 10;
const BOOST_PRICE_LABEL = '$1,300 M.N.';

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
    if (empty($existing['impulsado_hasta'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN impulsado_hasta DATETIME NULL');
    }
    if (empty($existing['stripe_session_id'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN stripe_session_id VARCHAR(255) NULL');
    }
    if (empty($existing['stripe_payment_status'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN stripe_payment_status VARCHAR(50) NULL');
    }
    if (empty($existing['boost_expired_notified_at'])) {
        db()->exec('ALTER TABLE mascotas ADD COLUMN boost_expired_notified_at DATETIME NULL');
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
        ubicacion_lat DECIMAL(9,6) NULL,
        ubicacion_lng DECIMAL(9,6) NULL,
        calles VARCHAR(240) NULL,
        dueno VARCHAR(160) NULL,
        recompensa VARCHAR(160) NULL,
        encontrado TINYINT(1) NOT NULL DEFAULT 0,
        vistas INT UNSIGNED NOT NULL DEFAULT 0,
        impulsado_hasta DATETIME NULL,
        stripe_session_id VARCHAR(255) NULL,
        stripe_payment_status VARCHAR(50) NULL,
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
    $indexes = db()->query("SHOW INDEX FROM mascotas_archivadas WHERE Key_name = 'uniq_archivadas_reporte'")->fetchAll();
    if (!$indexes) {
        db()->exec('DELETE older FROM mascotas_archivadas older JOIN mascotas_archivadas newer ON older.id = newer.id AND older.archive_id < newer.archive_id');
        db()->exec('ALTER TABLE mascotas_archivadas ADD UNIQUE KEY uniq_archivadas_reporte (id)');
    }
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

function is_boosted(array $pet): bool {
    $until = trim((string)($pet['impulsado_hasta'] ?? ''));
    return $until !== '' && strtotime($until) !== false && strtotime($until) > time();
}

function boosted_until_label(array $pet): ?string {
    if (!is_boosted($pet)) return null;
    $timestamp = strtotime((string)$pet['impulsado_hasta']);
    return $timestamp ? date('d/m/Y', $timestamp) : null;
}

function stripe_enabled(): bool {
    return (bool)(envv('STRIPE_SECRET_KEY') && envv('STRIPE_PRICE_ID'));
}

function stripe_request(string $method, string $endpoint, array $params = []): array {
    $secret = envv('STRIPE_SECRET_KEY');
    if (!$secret) throw new RuntimeException('Falta STRIPE_SECRET_KEY en el .env.');
    $url = 'https://api.stripe.com/v1/' . ltrim($endpoint, '/');
    if ($method === 'GET' && $params) {
        $url .= '?' . http_build_query($params);
    }
    $ch = curl_init($url);
    $options = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_USERPWD => $secret . ':',
        CURLOPT_TIMEOUT => 20,
    ];
    if ($method === 'POST') {
        $options[CURLOPT_POST] = true;
        $options[CURLOPT_POSTFIELDS] = http_build_query($params);
    }
    curl_setopt_array($ch, $options);
    $body = curl_exec($ch);
    $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    $json = json_decode((string)$body, true);
    if ($body === false || $status < 200 || $status >= 300) {
        $message = is_array($json) && isset($json['error']['message']) ? $json['error']['message'] : ($error ?: 'Stripe no pudo procesar la solicitud.');
        throw new RuntimeException($message);
    }
    return is_array($json) ? $json : [];
}

function create_boost_checkout(array $pet): string {
    if (!stripe_enabled()) throw new RuntimeException('Stripe todavia no esta configurado.');
    $session = stripe_request('POST', 'checkout/sessions', [
        'mode' => 'payment',
        'line_items[0][price]' => envv('STRIPE_PRICE_ID'),
        'line_items[0][quantity]' => '1',
        'success_url' => full_url('/mascotas/' . $pet['id']) . '?impulso=exito&session_id={CHECKOUT_SESSION_ID}',
        'cancel_url' => full_url('/mascotas/' . $pet['id']) . '?impulso=cancelado',
        'metadata[pet_id]' => $pet['id'],
        'metadata[owner_phone]' => $pet['reportado_por'],
        'metadata[boost_days]' => (string)BOOST_DAYS,
    ]);
    if (empty($session['id']) || empty($session['url'])) throw new RuntimeException('Stripe no regreso una sesion valida.');
    db()->prepare('UPDATE mascotas SET stripe_session_id = ?, stripe_payment_status = ? WHERE id = ? AND reportado_por = ?')
        ->execute([$session['id'], $session['payment_status'] ?? 'pending', $pet['id'], current_user_phone()]);
    return (string)$session['url'];
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

function send_boost_notification(array $pet, string $sessionId, string $boostedUntil): void {
    $url = full_url('/mascotas/' . $pet['id']);
    [$sent, $message] = send_notification_email('Nuevo anuncio impulsado en AyudaPet', [
        'Se activo un anuncio impulsado en AyudaPet.',
        '',
        'Mascota: ' . ($pet['nombre'] ?? 'Sin nombre'),
        'Tipo de reporte: ' . report_type_label($pet['tipo_reporte'] ?? 'extravio'),
        'Telefono del usuario: ' . ($pet['reportado_por'] ?? ''),
        'Contacto publico: ' . ($pet['contacto'] ?? ''),
        'Direccion: ' . ($pet['direccion'] ?? ''),
        'Activo hasta: ' . $boostedUntil,
        'Stripe session: ' . $sessionId,
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
        'Contacto publico: ' . ($pet['contacto'] ?? ''),
        'Direccion: ' . ($pet['direccion'] ?? ''),
        'Estuvo activo hasta: ' . ($pet['impulsado_hasta'] ?? ''),
        'Stripe session: ' . ($pet['stripe_session_id'] ?? ''),
        '',
        'Ver reporte: ' . $url,
    ]);
    if (!$sent) error_log('Correo de anuncio vencido no enviado: ' . $message);
    return $sent;
}

function process_expired_boosts(int $limit = 50): array {
    ensure_report_columns();
    $stmt = db()->prepare("SELECT * FROM mascotas WHERE impulsado_hasta IS NOT NULL AND impulsado_hasta <= NOW() AND stripe_payment_status = 'paid' AND boost_expired_notified_at IS NULL ORDER BY impulsado_hasta ASC LIMIT ?");
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

function activate_boost(string $petId, string $sessionId): void {
    ensure_report_columns();
    $pet = get_mascota($petId);
    if (!$pet) return;
    $alreadyNotified = is_boosted($pet) && ($pet['stripe_session_id'] ?? '') === $sessionId && ($pet['stripe_payment_status'] ?? '') === 'paid';
    db()->prepare('UPDATE mascotas SET impulsado_hasta = DATE_ADD(NOW(), INTERVAL ' . BOOST_DAYS . ' DAY), stripe_session_id = ?, stripe_payment_status = ?, boost_expired_notified_at = NULL WHERE id = ?')
        ->execute([$sessionId, 'paid', $petId]);
    if (!$alreadyNotified) {
        $updated = get_mascota($petId);
        send_boost_notification($updated ?: $pet, $sessionId, (string)(($updated['impulsado_hasta'] ?? null) ?: date('Y-m-d H:i:s', strtotime('+' . BOOST_DAYS . ' days'))));
    }
}

function confirm_boost_checkout(string $petId, string $sessionId): bool {
    if (!stripe_enabled() || $sessionId === '') return false;
    $session = stripe_request('GET', 'checkout/sessions/' . rawurlencode($sessionId));
    $sessionPetId = (string)($session['metadata']['pet_id'] ?? '');
    if (($session['payment_status'] ?? '') !== 'paid' || $sessionPetId !== $petId) return false;
    activate_boost($petId, (string)($session['id'] ?? $sessionId));
    return true;
}

function stripe_signature_valid(string $payload, string $header, string $secret): bool {
    $timestamp = null;
    $signatures = [];
    foreach (explode(',', $header) as $part) {
        [$key, $value] = array_pad(explode('=', trim($part), 2), 2, '');
        if ($key === 't') $timestamp = $value;
        if ($key === 'v1') $signatures[] = $value;
    }
    if (!$timestamp || !$signatures) return false;
    if (abs(time() - (int)$timestamp) > 300) return false;
    $expected = hash_hmac('sha256', $timestamp . '.' . $payload, $secret);
    foreach ($signatures as $signature) {
        if (hash_equals($expected, $signature)) return true;
    }
    return false;
}

function handle_stripe_webhook(): void {
    $secret = envv('STRIPE_WEBHOOK_SECRET');
    $payload = file_get_contents('php://input') ?: '';
    $signature = $_SERVER['HTTP_STRIPE_SIGNATURE'] ?? '';
    if (!$secret || !stripe_signature_valid($payload, $signature, $secret)) {
        http_response_code(400);
        echo 'invalid signature';
        return;
    }
    $event = json_decode($payload, true);
    if (!is_array($event)) {
        http_response_code(400);
        echo 'invalid payload';
        return;
    }
    if (($event['type'] ?? '') === 'checkout.session.completed') {
        $session = $event['data']['object'] ?? [];
        $petId = (string)($session['metadata']['pet_id'] ?? '');
        $sessionId = (string)($session['id'] ?? '');
        if ($petId && ($session['payment_status'] ?? '') === 'paid') {
            activate_boost($petId, $sessionId);
        }
    }
    http_response_code(200);
    echo 'ok';
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
    $stmt = db()->prepare('SELECT * FROM usuarios WHERE telefono = ? LIMIT 1');
    $stmt->execute([$phone]);
    return $stmt->fetch() ?: null;
}

function save_user(string $phone, string $password, ?string $name = null): void {
    $hash = password_hash($password, PASSWORD_DEFAULT);
    if (get_user($phone)) {
        $stmt = db()->prepare('UPDATE usuarios SET password_hash = ?, nombre = COALESCE(?, nombre), activo = 1 WHERE telefono = ?');
        $stmt->execute([$hash, $name, $phone]);
        return;
    }
    $stmt = db()->prepare('INSERT INTO usuarios (telefono, creado, password_hash, nombre, activo) VALUES (?, ?, ?, ?, 1)');
    $stmt->execute([$phone, time(), $hash, $name]);
}

function list_mascotas(): array {
    ensure_report_columns();
    return db()->query("SELECT * FROM mascotas ORDER BY CASE WHEN impulsado_hasta IS NOT NULL AND impulsado_hasta > NOW() THEN 0 ELSE 1 END, creado_at DESC LIMIT 80")->fetchAll();
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

function increment_report_views(string $id): void {
    ensure_report_columns();
    db()->prepare('UPDATE mascotas SET vistas = vistas + 1 WHERE id = ?')->execute([$id]);
}

function archive_report(array $pet, string $reason = 'deleted_by_owner'): void {
    ensure_archive_table();
    $fields = [
        'id', 'reportado_por', 'tipo_reporte', 'tipo_mascota', 'nombre', 'descripcion', 'contacto',
        'principal', 'secundarias', 'fecha', 'edad', 'raza', 'genero', 'color', 'collar', 'docil',
        'direccion', 'ubicacion_lat', 'ubicacion_lng', 'calles', 'dueno', 'recompensa', 'encontrado',
        'vistas', 'impulsado_hasta', 'stripe_session_id', 'stripe_payment_status',
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

function heatmap_reports(): array {
    ensure_archive_table();
    $stmt = db()->query("SELECT id, nombre, tipo_reporte, tipo_mascota, direccion, principal, ubicacion_lat, ubicacion_lng, encontrado, creado_at, archivado_at
        FROM mascotas_archivadas
        WHERE ubicacion_lat IS NOT NULL AND ubicacion_lng IS NOT NULL
        ORDER BY archivado_at DESC
        LIMIT 2000");
    $reports = $stmt->fetchAll();
    $stats = ['total' => count($reports), 'extravio' => 0, 'resguardo' => 0, 'en_casa' => 0];
    foreach ($reports as $report) {
        $type = report_type_value($report['tipo_reporte'] ?? '');
        if ($type === 'resguardo') $stats['resguardo']++;
        else $stats['extravio']++;
        if (!empty($report['encontrado'])) $stats['en_casa']++;
    }
    return ['reports' => $reports, 'stats' => $stats];
}

function heatmap_city_contacts(?string $city): array {
    ensure_archive_table();
    $city = trim((string)$city);
    if ($city === '') return ['city' => '', 'contacts' => [], 'sms' => ''];
    $terms = preg_split('/\s+/', preg_replace('/[^\p{L}\p{N}]+/u', ' ', lower_text($city)) ?: '', -1, PREG_SPLIT_NO_EMPTY);
    $terms = array_values(array_filter($terms, fn($term) => !in_array($term, ['cd', 'ciudad', 'mx', 'mexico'], true)));
    if (!$terms) $terms = [$city];
    $where = implode(' AND ', array_fill(0, count($terms), 'direccion LIKE ?'));
    $stmt = db()->prepare("SELECT reportado_por, contacto, direccion, COUNT(*) AS reportes, MAX(archivado_at) AS ultimo
        FROM mascotas_archivadas
        WHERE {$where}
        GROUP BY reportado_por, contacto, direccion
        ORDER BY ultimo DESC
        LIMIT 600");
    $stmt->execute(array_map(fn($term) => '%' . $term . '%', $terms));
    $seen = [];
    $contacts = [];
    $excluded = array_merge(admin_phones(), [normalize_phone(DEFAULT_PUBLIC_CONTACT)]);
    foreach ($stmt->fetchAll() as $row) {
        foreach ([$row['reportado_por'] ?? null, $row['contacto'] ?? null] as $rawPhone) {
            $phone = normalize_phone($rawPhone);
            if (!$phone || isset($seen[$phone]) || in_array($phone, $excluded, true)) continue;
            $seen[$phone] = true;
            $contacts[] = [
                'phone' => $phone,
                'sms' => phone_for_sms($phone),
                'direccion' => (string)($row['direccion'] ?? ''),
                'reportes' => (int)($row['reportes'] ?? 0),
            ];
        }
    }
    return [
        'city' => $city,
        'contacts' => $contacts,
        'sms' => implode("\n", array_column($contacts, 'sms')),
    ];
}

function pet_secondaries(array $pet): array {
    $items = json_decode((string)($pet['secundarias'] ?? '[]'), true);
    return is_array($items) ? array_values(array_filter($items, 'is_string')) : [];
}

function owns_report(?array $pet): bool {
    return $pet && current_user_phone() && $pet['reportado_por'] === current_user_phone();
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
    return '/uploads/reportes/' . $reportId . '/' . $name;
}

function report_payload(string $id, ?array $existing = null): array {
    $existing = $existing ?? [];
    $reportType = report_type_value(post_value('tipo_reporte') ?: ($existing['tipo_reporte'] ?? 'extravio'));
    $name = post_value('nombre');
    if (!$name && $reportType === 'extravio') throw new RuntimeException('El nombre de la mascota es obligatorio.');
    if (!$name) $name = 'Sin nombre';
    $contacto = isset($_POST['usar_contacto_propio']) ? post_value('contacto') : null;

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
        'direccion' => post_value('direccion'),
        'ubicacion_lat' => geo_value(post_value('ubicacion_lat'), -90, 90),
        'ubicacion_lng' => geo_value(post_value('ubicacion_lng'), -180, 180),
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
    $sql = 'INSERT INTO mascotas (id, reportado_por, tipo_reporte, tipo_mascota, nombre, descripcion, contacto, principal, secundarias, fecha, edad, raza, genero, color, collar, docil, direccion, ubicacion_lat, ubicacion_lng, calles, dueno, recompensa, encontrado)
            VALUES (:id, :reportado_por, :tipo_reporte, :tipo_mascota, :nombre, :descripcion, :contacto, :principal, :secundarias, :fecha, :edad, :raza, :genero, :color, :collar, :docil, :direccion, :ubicacion_lat, :ubicacion_lng, :calles, :dueno, :recompensa, :encontrado)';
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

function update_report(string $id, array $existing): void {
    ensure_report_columns();
    $data = report_payload($id, $existing);
    $sets = [];
    foreach ($data as $key => $_) $sets[] = "{$key} = :{$key}";
    $stmt = db()->prepare('UPDATE mascotas SET ' . implode(', ', $sets) . ' WHERE id = :id AND reportado_por = :reportado_por');
    $stmt->execute($data + ['id' => $id, 'reportado_por' => current_user_phone()]);
    try {
        $pet = get_mascota($id);
        if ($pet) archive_report($pet, 'updated_snapshot');
    } catch (Throwable $e) {
        error_log('No se pudo actualizar el archivo del reporte ' . $id . ': ' . $e->getMessage());
    }
}

function remove_report_image(string $id, array $pet, string $target, ?string $image): void {
    if ($target === 'principal') {
        db()->prepare('UPDATE mascotas SET principal = NULL WHERE id = ? AND reportado_por = ?')->execute([$id, current_user_phone()]);
        return;
    }
    if ($target === 'secundaria' && $image) {
        $secondaries = array_values(array_filter(pet_secondaries($pet), function ($img) use ($image) {
            return $img !== $image;
        }));
        db()->prepare('UPDATE mascotas SET secundarias = ? WHERE id = ? AND reportado_por = ?')->execute([json_encode($secondaries), $id, current_user_phone()]);
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
    $metaDescription = $metaDescription ?? 'AyudaPet conecta reportes de mascotas perdidas y localizadas para que vuelvan a casa mas rapido.';
    $metaUrl = $metaUrl ?? full_url('/');
    $metaImage = $metaImage ?? full_url('/static/og_image.png');
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
  <link rel="canonical" href="<?= e($metaUrl) ?>">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="AyudaPet">
  <meta property="og:title" content="<?= e($metaTitle) ?>">
  <meta property="og:description" content="<?= e($metaDescription) ?>">
  <meta property="og:url" content="<?= e($metaUrl) ?>">
  <meta property="og:image" content="<?= e($metaImage) ?>">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="<?= e($metaTitle) ?>">
  <meta name="twitter:description" content="<?= e($metaDescription) ?>">
  <meta name="twitter:image" content="<?= e($metaImage) ?>">
  <link rel="icon" type="image/png" href="/static/logo.png">
  <link rel="apple-touch-icon" href="/static/logo.png">
  <style><?= css() ?></style>
  <style>.switch input:checked~.switch-ui{background:var(--green)}.switch input:checked~.switch-ui:before{transform:translateX(22px)}.inline-fields{display:grid;grid-template-columns:88px minmax(0,132px);gap:8px;align-items:center}.inline-fields select,.inline-fields input{min-width:0}.pet-body{padding-right:20px}.btn.facebook{background:#1877f2;color:#fff;border-color:#1877f2}.btn.facebook:hover{background:#145dbd}.btn.donate{background:#22607a;color:#fff;border-color:#22607a}.btn.donate:hover{background:#18475c}.btn.boost{background:#f6a623;color:#18212f;border-color:#f6a623}.btn.boost:hover{background:#e99612}.badge.rescue{background:#fff8e8;color:var(--amber)}.boost-badge{width:max-content;background:#fff4d8;color:#8a570b}.pet-card.boosted{border-color:#f0c56f;box-shadow:0 16px 42px rgba(164,102,20,.16)}.boost-panel,.boost-copy{margin-bottom:16px;padding:14px;border:1px solid #f0c56f;border-radius:8px;background:#fffaf0}.boost-panel{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.boost-copy h2{margin:0 0 8px;font-size:1.15rem}.boost-copy p{margin:0 0 10px;color:var(--muted);line-height:1.5}.filter-dropdown{position:relative}.filter-dropdown summary{list-style:none;display:flex;align-items:center;justify-content:space-between;gap:14px;padding-right:32px;cursor:pointer;font-weight:900}.filter-dropdown summary::-webkit-details-marker{display:none}.filter-dropdown summary:after{content:"+";position:absolute;top:0;right:0;color:var(--muted);font-size:1.25rem;line-height:1}.filter-dropdown[open] summary:after{content:"-"}.filter-dropdown .search-form{margin-top:16px}.modal-page{min-height:calc(100vh - 170px);display:grid;place-items:center;padding:clamp(16px,4vw,34px)}.report-type-modal{width:min(680px,100%);padding:clamp(20px,4vw,34px)}.report-type-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:20px}.report-type-option{display:grid;gap:8px;padding:18px;border:1px solid var(--line);border-radius:8px;background:#fbfdff}.report-type-option:hover{border-color:var(--brand);box-shadow:0 12px 28px rgba(20,32,48,.08)}.report-type-option strong{font-size:1.05rem}.report-type-option span{color:var(--muted);line-height:1.45}.donation-modal{position:fixed;inset:0;z-index:90;display:none;place-items:center;padding:18px;background:rgba(10,16,24,.48)}.donation-modal.open{display:grid}.donation-dialog{width:min(460px,100%);padding:24px;border:1px solid var(--line);border-radius:8px;background:#fff;box-shadow:0 24px 80px rgba(20,32,48,.22)}.donation-dialog h2{margin:0;font-size:1.6rem}.donation-dialog p:not(.eyebrow){color:var(--muted);line-height:1.55}.detail-media .views-badge,.detail-media .photo-badge{top:10px;min-width:86px;min-height:28px;padding:0 10px;font-size:.78rem;line-height:1;align-items:center;justify-content:center;text-align:center}.views-badge{position:absolute;left:10px;box-shadow:0 10px 24px rgba(20,32,48,.16);background:rgba(255,255,255,.94);color:var(--ink)}@media(max-width:640px){.report-type-actions{grid-template-columns:1fr}}@media(max-width:420px){.pet-body{padding-right:12px}.filter-dropdown summary{align-items:flex-start;flex-direction:column}.detail-media .views-badge,.detail-media .photo-badge{top:7px;min-width:80px;min-height:24px;padding:0 8px;font-size:.68rem}.views-badge{left:7px}}</style>
  <style>.btn{font-size:.92rem;line-height:1}.btn.logout,.btn.back-report{background:#b93824;color:#fff;border-color:#b93824}.btn.logout:hover,.btn.back-report:hover{background:#922b1b}.btn.call{background:#0d83f2;color:#fff;border-color:#0d83f2}.btn.call:hover{background:#096dce}.btn.whatsapp{background:#128C7E;color:#fff;border-color:#128C7E}.btn.whatsapp:hover{background:#0f766b}.btn.share{background:#25d366;color:#fff;border-color:#25d366}.btn.share:hover{background:#20b858}.detail-owner-actions{display:flex;justify-content:flex-end;gap:10px;margin:0 0 14px}.detail-owner-actions form{display:flex;margin:0}.detail-owner-actions .btn{min-height:38px;padding:0 14px;border:1px solid var(--line);color:#fff}.detail-owner-actions .btn.edit{background:#176b87;border-color:#176b87}.detail-owner-actions .btn.edit:hover{background:#10546c}.detail-owner-actions .btn.delete{background:#b93824;border-color:#b93824}.detail-owner-actions .btn.delete:hover{background:#922b1b}.boost-copy{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:16px;padding:16px 18px}.boost-copy form{margin:0}.boost-copy .btn.boost{min-width:190px;min-height:48px;box-shadow:0 12px 28px rgba(246,166,35,.22)}@media(max-width:840px){.detail-owner-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.detail-owner-actions .btn,.detail-owner-actions form{width:100%}.boost-copy{grid-template-columns:1fr;gap:14px}.boost-copy .btn.boost,.boost-copy form{width:100%}}@media(max-width:420px){.detail-owner-actions .btn{min-height:42px}.boost-copy{padding:14px}.boost-copy h2{font-size:1.05rem}.boost-copy .btn.boost{min-height:46px}}</style>
  <style>.heatmap-page{display:grid;gap:18px}.heatmap-stats{grid-template-columns:repeat(4,minmax(0,1fr));margin:0}.heatmap-panel{padding:0;overflow:hidden}.heatmap-canvas{width:100%;height:min(72vh,720px);min-height:460px}.heatmap-list{margin-top:4px}.heatmap-list .mini-list{gap:12px}.heatmap-list .mini-report{grid-template-columns:64px minmax(0,1fr);align-items:center;gap:14px;padding:10px;min-width:0}.heatmap-list .mini-report>span:not(.mini-thumb){min-width:0;display:block}.heatmap-list .mini-report img,.heatmap-list .mini-thumb{width:64px;height:64px;min-width:64px;border-radius:8px;object-fit:cover}.heatmap-list .mini-report strong{display:block;line-height:1.2}.heatmap-list .mini-report .meta{display:block;margin-top:3px;line-height:1.35;overflow-wrap:anywhere}.map-popup{width:190px;display:grid;gap:7px;color:#18212f}.map-popup-img{width:190px;height:140px;object-fit:cover;border-radius:8px;display:block;background:#edf3f7}.map-popup strong{font-size:.95rem;line-height:1.2}.map-popup span{color:#617084;line-height:1.3;overflow-wrap:anywhere}.sms-search{grid-template-columns:minmax(0,1fr) auto}.sms-copy-box{margin-top:14px;min-height:150px;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;line-height:1.5}.sms-contact-list{display:grid;gap:8px;margin-top:14px}.sms-contact{display:grid;gap:3px;padding:10px;border:1px solid var(--line);border-radius:8px;background:#fbfdff}.sms-contact span{color:var(--muted);overflow-wrap:anywhere}@media(max-width:820px){.heatmap-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.heatmap-canvas{height:68vh;min-height:420px}.sms-search{grid-template-columns:1fr}}@media(max-width:480px){.heatmap-stats{grid-template-columns:1fr}.heatmap-canvas{height:62vh;min-height:360px}.heatmap-list .mini-report{grid-template-columns:58px minmax(0,1fr);gap:12px}.heatmap-list .mini-report img,.heatmap-list .mini-thumb{width:58px;height:58px;min-width:58px}.map-popup,.map-popup-img{width:160px}.map-popup-img{height:118px}}</style>
</head>
<body>
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
        <a class="btn ghost <?= $active('/') ?>" href="/">Reportes</a>
        <?php if (is_admin_user()): ?><a class="btn ghost <?= $active('/mapa-calor') ?>" href="/mapa-calor">Mapa de calor</a><?php endif; ?>
        <a class="btn facebook" href="https://www.facebook.com/AyudaPet26" target="_blank" rel="noopener">Facebook</a>
        <a class="btn donate" href="https://donate.stripe.com/6oU3cpg1T0Y60sOerJ3ks00" target="_blank" rel="noopener">Donar</a>
        <a class="btn logout" href="/logout">Cerrar sesion</a>
      <?php else: ?>
        <a class="btn ghost <?= $active('/login') ?>" href="/login">Entrar</a>
        <a class="btn ghost <?= $active('/registro') ?>" href="/registro">Crear cuenta</a>
        <a class="btn ghost <?= $active('/') ?>" href="/">Reportes</a>
        <a class="btn facebook" href="https://www.facebook.com/AyudaPet26" target="_blank" rel="noopener">Facebook</a>
        <a class="btn donate" href="https://donate.stripe.com/6oU3cpg1T0Y60sOerJ3ks00" target="_blank" rel="noopener">Donar</a>
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
  <div class="donation-modal" data-donation-modal aria-hidden="true">
    <section class="donation-dialog" role="dialog" aria-modal="true" aria-labelledby="donation-title">
      <p class="eyebrow" style="color:var(--brand);">AyudaPet</p>
      <h2 id="donation-title">Quieres apoyar con un donativo?</h2>
      <p>Tu apoyo ayuda a mantener activa la plataforma para reportes de mascotas perdidas y en resguardo.</p>
      <div class="actions"><a class="btn primary" href="https://donate.stripe.com/6oU3cpg1T0Y60sOerJ3ks00" data-donation-yes>Si, donar</a><button class="btn" type="button" data-donation-no>No gracias</button></div>
    </section>
  </div>
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
    if ($view === 'detalle') { view_detalle($mascota, $isOwner, $share, $mapUrl); return; }
    if ($view === 'registro') { view_registro(); return; }
    if ($view === 'verificar') { view_verificar($phone); return; }
    if ($view === 'set_password') { view_set_password($phone, $recovering); return; }
    if ($view === 'login') { view_login(); return; }
    if ($view === 'recuperar') { view_recuperar(); return; }
    if ($view === 'perfil') { view_perfil($user, $reportes); return; }
    if ($view === 'tipo_reporte') { view_tipo_reporte(); return; }
    if ($view === 'reportar') { view_reportar($mascota, $editing, $mapsApiKey); return; }
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
document.addEventListener("keydown",(event)=>{if(event.key==="Escape")document.body.classList.remove("menu-open")});
const lightbox=document.querySelector("[data-lightbox]");const lightboxImage=lightbox?.querySelector("img");function closeLightbox(){if(!lightbox||!lightboxImage)return;lightbox.classList.remove("open");lightbox.setAttribute("aria-hidden","true");lightboxImage.src="";lightboxImage.alt=""}
document.querySelectorAll("[data-zoom-src]").forEach((image)=>image.addEventListener("click",(event)=>{if(!lightbox||!lightboxImage)return;event.preventDefault();event.stopPropagation();lightboxImage.src=image.dataset.zoomSrc;lightboxImage.alt=image.alt||"Imagen ampliada";lightbox.classList.add("open");lightbox.setAttribute("aria-hidden","false")}));
document.querySelectorAll("[data-lightbox-close]").forEach((button)=>button.addEventListener("click",closeLightbox));lightbox?.addEventListener("click",(event)=>{if(event.target===lightbox)closeLightbox()});document.addEventListener("keydown",(event)=>{if(event.key==="Escape")closeLightbox()});
document.querySelectorAll("[data-remove-image]").forEach((button)=>button.addEventListener("click",async(event)=>{event.preventDefault();const input=button.querySelector("input");const item=button.closest(".edit-image-item");if(input)input.checked=true;item?.classList.add("removing");if(!button.dataset.removeUrl)return;try{const response=await fetch(button.dataset.removeUrl,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({target:button.dataset.removeTarget,image:button.dataset.removeImageUrl||null})});if(!response.ok)throw new Error("remove failed")}catch(error){if(input)input.checked=false;item?.classList.remove("removing");alert("No se pudo eliminar la imagen. Intenta de nuevo.")}}));
document.querySelectorAll("[data-copy-url]").forEach((button)=>button.addEventListener("click",async()=>{const url=button.dataset.copyUrl;if(!url)return;try{await navigator.clipboard.writeText(url)}catch(error){const input=document.createElement("input");input.value=url;document.body.appendChild(input);input.select();document.execCommand("copy");input.remove()}const original=button.textContent;button.textContent="Copiado";window.setTimeout(()=>{button.textContent=original},1600)}));
document.addEventListener("click",async(event)=>{const button=event.target.closest("[data-copy-sms]");if(!button)return;const box=document.querySelector("[data-sms-copy]");const text=box?.value||"";if(!text)return;try{await navigator.clipboard.writeText(text)}catch(error){box?.focus();box?.select();document.execCommand("copy")}const original=button.textContent;button.textContent="Copiado";window.setTimeout(()=>{button.textContent=original},1600)});
document.querySelectorAll("[data-sms-search]").forEach((form)=>form.addEventListener("submit",async(event)=>{event.preventDefault();const input=form.querySelector("[name='ciudad']");const results=document.querySelector("[data-sms-results]");const city=(input?.value||"").trim();if(!results||!city)return;const button=form.querySelector("button[type='submit']");const original=button?.textContent||"";if(button){button.disabled=true;button.textContent="Buscando"}results.innerHTML='<div class="empty">Buscando telefonos...</div>';try{const response=await fetch(`/mapa-calor/contactos?ciudad=${encodeURIComponent(city)}`,{headers:{"Accept":"application/json"}});const data=await response.json();if(!response.ok||!data.ok)throw new Error(data.message||"Error");const count=(data.contacts||[]).length;let html=`<p class="filter-meta">${count} telefono${count===1?"":"s"} para ${escapeHtml(data.city)}.</p>`;if(count){html+=`<textarea class="sms-copy-box" readonly data-sms-copy>${escapeHtml(data.sms||"")}</textarea><div class="actions"><button class="btn share" type="button" data-copy-sms>Copiar telefonos para SMS</button></div><div class="sms-contact-list">`;html+=(data.contacts||[]).slice(0,80).map((contact)=>`<div class="sms-contact"><strong>${escapeHtml(contact.sms)}</strong><span>${escapeHtml(contact.direccion)}</span></div>`).join("");html+="</div>"}else{html+='<div class="empty">No encontre telefonos asociados a esa ciudad.</div>'}results.innerHTML=html;history.replaceState(null,"",`/mapa-calor?ciudad=${encodeURIComponent(city)}`)}catch(error){results.innerHTML='<div class="empty">No se pudo buscar. Intenta de nuevo.</div>'}finally{if(button){button.disabled=false;button.textContent=original}}}));
document.querySelectorAll("[data-native-share-button]").forEach((button)=>button.addEventListener("click",async()=>{const shareData={title:button.dataset.shareTitle||document.title,text:button.dataset.shareText||"",url:button.dataset.shareUrl||window.location.href};if(navigator.share){try{await navigator.share(shareData);return}catch(error){if(error?.name==="AbortError")return}}const original=button.textContent;button.textContent="Usa copiar enlace";window.setTimeout(()=>{button.textContent=original},1800)}));
document.querySelectorAll("[data-max-files]").forEach((input)=>input.addEventListener("change",()=>{const maxFiles=Number(input.dataset.maxFiles||0);if(input.files.length>maxFiles){input.value="";alert(maxFiles>0?`Solo puedes seleccionar hasta ${maxFiles} imagenes.`:"Ya tienes el maximo de 3 fotos adicionales.")}}));
document.querySelectorAll("[data-contact-toggle]").forEach((toggle)=>{const box=document.querySelector("[data-contact-own]");const input=document.querySelector("[data-contact-input]");const sync=()=>{if(!box)return;box.classList.toggle("show",toggle.checked);if(input){input.disabled=!toggle.checked;if(!toggle.checked)input.value=""}};toggle.addEventListener("change",sync);sync()});
document.querySelectorAll("[data-money-input]").forEach((input)=>{const preview=document.querySelector("[data-money-preview]");const sync=()=>{if(!preview)return;const amount=Number(String(input.value||"").replace(/\D/g,""));preview.textContent=amount>0?`$${amount.toLocaleString("es-MX")} M.N.`:"Se mostrara como $1,000 M.N."};input.addEventListener("input",sync);sync()});
(()=>{const modal=document.querySelector("[data-donation-modal]");if(!modal)return;const path=window.location.pathname;if(path==="/reportar"||/\/mascotas\/[a-f0-9]{32}\/editar$/.test(path))return;const key="ayudapet_donation_prompt";const close=()=>{modal.classList.remove("open");modal.setAttribute("aria-hidden","true")};try{if(localStorage.getItem(key))return}catch(error){}window.setTimeout(()=>{modal.classList.add("open");modal.setAttribute("aria-hidden","false")},180000);modal.querySelector("[data-donation-no]")?.addEventListener("click",()=>{try{localStorage.setItem(key,"no")}catch(error){}close()});modal.querySelector("[data-donation-yes]")?.addEventListener("click",()=>{try{localStorage.setItem(key,"yes")}catch(error){}});})();
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
      <details class="stats-dropdown">
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
  <section class="panel search-panel"><details class="filter-dropdown" <?= $activeFilter ? 'open' : '' ?>><summary><span>Buscar y filtrar</span></summary><form class="search-form" method="get" action="/"><div class="field"><label for="q">Buscar</label><input id="q" name="q" value="<?= e($filters['q']) ?>" placeholder="Nombre, direccion o contacto"></div><div class="field"><label for="estado">Estado</label><select id="estado" name="estado"><?php foreach (['todos'=>'Todos','perdidos'=>'Perdidos','resguardo'=>'Resguardados','localizados'=>'Localizados'] as $value => $label): ?><option value="<?= e($value) ?>" <?= $filters['estado'] === $value ? 'selected' : '' ?>><?= e($label) ?></option><?php endforeach; ?></select></div><button class="btn primary" type="submit">Buscar</button></form><p class="filter-meta"><?= e($filters['resultados']) ?> resultado<?= $filters['resultados'] == 1 ? '' : 's' ?></p></details></section>
  <div class="section-head"><div><h2>Reportes recientes</h2><p>Informacion publica enviada por la comunidad.</p></div></div>
  <?php if ($mascotas): ?><section class="grid">
    <?php foreach ($mascotas as $pet): ?>
      <a class="pet-card <?= is_boosted($pet) ? 'boosted' : '' ?>" href="/mascotas/<?= e($pet['id']) ?>">
        <div class="pet-media">
          <?php if ($pet['principal']): ?><img class="zoomable" src="<?= e($pet['principal']) ?>" alt="<?= e($pet['nombre']) ?>" data-zoom-src="<?= e($pet['principal']) ?>"><?php else: ?><?= e(first_letter($pet['nombre'] ?: '?')) ?><?php endif; ?>
          <span class="badge photo-badge <?= e(report_status_class($pet)) ?>"><?= e(report_status_label($pet)) ?></span>
        </div>
        <div class="pet-body">
          <?php if (is_boosted($pet)): ?><span class="badge boost-badge">Impulsado</span><?php endif; ?>
          <h3><?= e($pet['nombre']) ?></h3>
          <p class="meta"><?php if ($pet['direccion']): ?><strong>Direccion:</strong> <?= e($pet['direccion']) ?><br><?php endif; ?></p>
          <?php if ($pet['descripcion']): ?><p class="pet-summary"><?= e($pet['descripcion']) ?></p><?php endif; ?>
        </div>
      </a>
    <?php endforeach; ?>
  </section><?php else: ?><div class="empty">Todavia no hay reportes publicados.</div><?php endif; ?>
<?php }

function view_detalle(array $mascota, bool $isOwner, array $share, ?string $mapUrl): void {
    $secundarias = pet_secondaries($mascota);
    $callPhone = phone_digits($mascota['contacto'] ?? '');
    $waPhone = whatsapp_digits($mascota['contacto'] ?? '');
    $direccionLabel = report_type_value($mascota['tipo_reporte'] ?? '') === 'resguardo' ? 'Direccion donde se encontro' : 'Direccion de extravio';
    $boostedUntil = boosted_until_label($mascota);
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
      <?php if ($isOwner): ?><div class="detail-owner-actions"><a class="btn edit" href="/mascotas/<?= e($mascota['id']) ?>/editar">Editar</a><form method="post" action="/mascotas/<?= e($mascota['id']) ?>/eliminar" onsubmit="return confirm('Eliminar este reporte?');"><button class="btn delete" type="submit">Eliminar</button></form></div><?php endif; ?>
      <?php if ($boostedUntil): ?><div class="boost-panel"><span class="badge boost-badge">Impulsado</span><strong>Activo hasta <?= e($boostedUntil) ?></strong></div><?php endif; ?>
      <?php if ($isOwner && !$boostedUntil): ?><div class="boost-copy"><div><h2>Impulsa tu anuncio por 10 dias.</h2><p>Lo destacamos en AyudaPet y tambien enviamos tu reporte directo a celulares de personas cercanas a la zona donde se perdio tu mascota.</p><strong><?= e(BOOST_PRICE_LABEL) ?> por <?= e(BOOST_DAYS) ?> dias</strong></div><form method="post" action="/mascotas/<?= e($mascota['id']) ?>/impulsar"><button class="btn boost" type="submit">Impulsar ahora</button></form></div><?php endif; ?>
      <div class="info-list"><?php info_row('Tipo de reporte', report_type_label($mascota['tipo_reporte'] ?? 'extravio')); info_row('Fecha', $mascota['fecha']); info_row('Nombre de mascota', $mascota['nombre']); info_row('Descripcion', $mascota['descripcion']); ?></div>
      <div class="split-info"><?php foreach ([['Tipo de mascota','tipo_mascota'],['Edad','edad'],['Raza','raza'],['Genero','genero'],['Color','color'],['Collar','collar'],['Docil','docil']] as [$label,$key]) info_row($label, $mascota[$key]); ?></div>
      <?php if ($mapUrl): ?><div class="map-frame"><iframe src="<?= e($mapUrl) ?>" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen title="Mapa de direccion de extravio"></iframe></div><?php endif; ?>
      <div class="info-list"><?php info_row($direccionLabel, $mascota['direccion']); ?></div>
      <div class="split-info"><?php info_row('Recompensa', money_display($mascota['recompensa'])); ?></div>
      <?php if ($callPhone): ?><div class="contact-actions"><a class="btn call" href="tel:<?= e($callPhone) ?>">Llamar</a><a class="btn whatsapp" href="https://wa.me/<?= e($waPhone) ?>" target="_blank" rel="noopener">WhatsApp</a></div><?php endif; ?>
      <div class="share-actions" aria-label="Compartir reporte"><p class="share-title">Comparte:</p><button class="btn share" type="button" data-native-share-button data-share-title="<?= e($share['text']) ?>" data-share-text="<?= e($share['message']) ?>" data-share-url="<?= e($share['url']) ?>">Compartir</button><button class="btn" type="button" data-copy-url="<?= e($share['url']) ?>">Copiar enlace</button></div>
      <div class="actions"><a class="btn back-report" href="/">Volver a reportes</a></div>
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
  <section class="form-wrap"><form class="form-panel" method="post"><p class="eyebrow" style="color:var(--brand);">Registro seguro</p><h1>Crea tu cuenta</h1><p class="meta">Solo aceptamos numeros mexicanos de 10 digitos.</p><div class="form-grid"><div class="field full"><label for="tel">Telefono mexicano</label><?php phone_field(); ?></div></div><div class="actions"><button class="btn primary" type="submit">Enviar codigo</button></div></form></section>
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
    <div class="panel profile-card"><p class="eyebrow" style="color:var(--brand);">Cuenta</p><div class="avatar"><?php if ($user['foto']): ?><img src="<?= e($user['foto']) ?>" alt="<?= e($user['nombre'] ?: 'Perfil') ?>"><?php else: ?><?= e(first_letter($user['nombre'] ?: $user['telefono'])) ?><?php endif; ?></div><h1><?= e($user['nombre'] ?: 'Mi perfil') ?></h1><p class="meta"><strong>Telefono registrado:</strong><br><?= e($user['telefono']) ?></p><form method="post" enctype="multipart/form-data" class="form-grid"><div class="field full"><label for="nombre">Nombre</label><input id="nombre" name="nombre" value="<?= e($user['nombre'] ?? '') ?>"></div><div class="field full"><label for="foto">Foto de perfil</label><input id="foto" name="foto" type="file" accept="image/*"></div><div class="actions"><button class="btn primary" type="submit">Guardar perfil</button></div></form></div>
    <div class="panel profile-card"><p class="eyebrow" style="color:var(--brand);">Seguridad</p><h1>Cambiar contrase&ntilde;a</h1><form method="post" action="/perfil/password" class="form-grid"><div class="field full"><label for="current_password">Contrase&ntilde;a actual</label><input id="current_password" name="current_password" type="password" autocomplete="current-password" required></div><div class="field"><label for="new_password">Nueva contrase&ntilde;a</label><input id="new_password" name="new_password" type="password" autocomplete="new-password" minlength="8" required></div><div class="field"><label for="confirm_password">Confirmar contrase&ntilde;a</label><input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" minlength="8" required></div><div class="actions"><button class="btn primary" type="submit">Actualizar contrase&ntilde;a</button></div></form></div>
  </section>
  <section class="panel profile-card" style="margin-top:18px;"><div class="section-head" style="margin-top:0;"><div><h2>Mis reportes</h2><p>Reportes publicados con tu numero registrado.</p></div><a class="btn primary" href="/reportar">Nuevo reporte</a></div><?php if ($reportes): ?><div class="mini-list"><?php foreach ($reportes as $pet): ?><a class="mini-report" href="/mascotas/<?= e($pet['id']) ?>"><?php if ($pet['principal']): ?><img src="<?= e($pet['principal']) ?>" alt="<?= e($pet['nombre']) ?>"><?php else: ?><span class="mini-thumb"><?= e(first_letter($pet['nombre'] ?: '?')) ?></span><?php endif; ?><span><strong><?= e($pet['nombre']) ?></strong><br><span class="meta"><?= e(report_status_label($pet)) ?></span></span></a><?php endforeach; ?></div><?php else: ?><div class="empty">Todavia no tienes reportes publicados.</div><?php endif; ?></section>
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
  <section class="form-wrap"><form class="form-panel" method="post" enctype="multipart/form-data"><input type="hidden" name="tipo_reporte" value="<?= e($tipoReporte) ?>"><p class="eyebrow" style="color:var(--brand);"><?= $editing ? report_type_label($tipoReporte) : 'Nuevo reporte' ?></p><h1><?= e($formTitle) ?></h1><div class="form-grid">
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
    <div class="field full"><label for="direccion"><?= e($direccionLabel) ?></label><input id="direccion" name="direccion" value="<?= e($mascota['direccion'] ?? '') ?>" autocomplete="off" data-address-autocomplete><input type="hidden" name="ubicacion_lat" value="<?= e($mascota['ubicacion_lat'] ?? '') ?>" data-address-lat><input type="hidden" name="ubicacion_lng" value="<?= e($mascota['ubicacion_lng'] ?? '') ?>" data-address-lng></div>
    <?php if (!$isResguardo): ?><div class="field"><label for="recompensa">Recompensa</label><input id="recompensa" name="recompensa" type="number" min="0" step="1" inputmode="numeric" value="<?= e($recompensaInput) ?>" placeholder="1000" data-money-input><span class="hint" data-money-preview><?= e(money_display($recompensaInput) ?: 'Se mostrara como $1,000 M.N.') ?></span></div><?php endif; ?>
    <?php $usesOwnContact = !empty($mascota['contacto']) && $mascota['contacto'] !== DEFAULT_PUBLIC_CONTACT; ?>
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
      <input id="contacto" name="contacto" value="<?= e($usesOwnContact ? ($mascota['contacto'] ?? '') : '') ?>" placeholder="Telefono, WhatsApp o correo" data-contact-input>
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
      const latInput = document.querySelector("[data-address-lat]");
      const lngInput = document.querySelector("[data-address-lng]");
      if (!input || !window.google?.maps?.places) return;
      const autocomplete = new google.maps.places.Autocomplete(input, {
        componentRestrictions: { country: "mx" },
        fields: ["address_components", "formatted_address", "geometry", "name"],
        types: ["address"],
      });

      const getPart = (parts, type, shortName = false) => {
        const item = parts.find((part) => part.types.includes(type));
        return item ? (shortName ? item.short_name : item.long_name) : "";
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
        return place.name || input.value;
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
        selectedPrivateAddress = privateAddress(place);
        input.value = selectedPrivateAddress;
        setCoordinates(place);
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
            'direccion' => (string)($report['direccion'] ?? ''),
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
      <?php if ($reports): ?><div class="mini-list"><?php foreach (array_slice($reports, 0, 40) as $report): ?><div class="mini-report"><?php if (!empty($report['principal'])): ?><img src="<?= e($report['principal']) ?>" alt="<?= e($report['nombre'] ?: 'Reporte') ?>"><?php else: ?><span class="mini-thumb"><?= e(first_letter($report['nombre'] ?? '?')) ?></span><?php endif; ?><span><strong><?= e($report['nombre'] ?: 'Reporte') ?></strong><span class="meta"><?= e(report_type_value($report['tipo_reporte'] ?? '') === 'resguardo' ? 'Resguardo' : 'Extravio') ?> · <?= e($report['direccion'] ?: 'Sin direccion') ?></span></span></div><?php endforeach; ?></div><?php else: ?><div class="empty">Todavia no hay ubicaciones archivadas.</div><?php endif; ?>
    </section>
    <section class="panel sms-panel">
      <div class="section-head" style="margin-top:0;"><div><h2>Telefonos por ciudad</h2><p>Busca numeros registrados asociados a reportes de esa ciudad.</p></div></div>
      <form class="search-form sms-search" method="get" action="/mapa-calor" data-sms-search>
        <div class="field"><label for="ciudad">Ciudad o zona</label><input id="ciudad" name="ciudad" value="<?= e($cityContacts['city'] ?? '') ?>" placeholder="Ej. Juarez, San Felipe del Real"></div>
        <button class="btn primary" type="submit">Buscar telefonos</button>
      </form>
      <div data-sms-results>
      <?php if (($cityContacts['city'] ?? '') !== ''): ?>
        <p class="filter-meta"><?= count($cityContacts['contacts']) ?> telefono<?= count($cityContacts['contacts']) === 1 ? '' : 's' ?> para <?= e($cityContacts['city']) ?>.</p>
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
      points.forEach((point) => {
        new google.maps.Circle({
          strokeColor: "#e85035",
          strokeOpacity: 0.78,
          strokeWeight: 1,
          fillColor: "#e85035",
          fillOpacity: 0.24,
          map,
          center: { lat: point.lat, lng: point.lng },
          radius: 420,
        });
      });
      points.slice(0, 120).forEach((point) => {
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
        const image = point.imagen ? `<img class="map-popup-img" src="${escapeHtml(point.imagen)}" alt="${escapeHtml(point.nombre)}">` : "";
        const info = new google.maps.InfoWindow({ content: `<div class="map-popup">${image}<strong>${escapeHtml(point.nombre)}</strong><span>${escapeHtml(point.direccion)}</span></div>` });
        marker.addListener("click", () => info.open({ anchor: marker, map }));
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

function route(): void {
    $method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
    $path = path_only();

    try {
        if ($path === '/stripe/webhook' && $method === 'POST') {
            handle_stripe_webhook();
            return;
        }

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

        if ($path === '/') {
            $pets = list_mascotas();
            $q = trim((string)($_GET['q'] ?? ''));
            $estado = strtolower(trim((string)($_GET['estado'] ?? 'todos')));
            if (!in_array($estado, ['todos', 'perdidos', 'resguardo', 'localizados'], true)) $estado = 'todos';
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
            if ($estado === 'localizados') {
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

        if ($path === '/registro') {
            if ($method === 'POST') {
                $phone = normalize_phone($_POST['tel'] ?? '');
                if (!$phone) { flash('Escribe un numero mexicano valido.', 'error'); redirect_to('/registro'); }
                [$sent, $dev] = create_otp($phone);
                $_SESSION['pending_tel'] = $phone;
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
                save_user($phone, $pwd, $recovering ? null : post_value('nombre'));
                unset($_SESSION['pending_tel'], $_SESSION['verified_tel']);
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

        if (preg_match('#^/mascotas/([a-f0-9]{32})$#', $path, $m)) {
            $pet = get_mascota($m[1]);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El reporte solicitado no existe.'], 404); return; }
            if (($_GET['impulso'] ?? '') === 'exito') {
                try {
                    $confirmed = confirm_boost_checkout($pet['id'], (string)($_GET['session_id'] ?? ''));
                    flash($confirmed ? 'Tu anuncio ya esta impulsado por 10 dias.' : 'Pago recibido. Stripe confirmara el impulso en unos momentos.', 'success');
                } catch (Throwable $e) {
                    error_log('No se pudo confirmar impulso Stripe: ' . $e->getMessage());
                    flash('Pago recibido. Stripe confirmara el impulso en unos momentos.', 'success');
                }
                redirect_to('/mascotas/' . $pet['id']);
            }
            if (($_GET['impulso'] ?? '') === 'cancelado') { flash('Pago cancelado. Tu reporte no fue impulsado.', 'warning'); redirect_to('/mascotas/' . $pet['id']); }
            increment_report_views($pet['id']);
            $pet['vistas'] = ((int)($pet['vistas'] ?? 0)) + 1;
            $status = report_status_label($pet);
            $detailUrl = full_url('/mascotas/' . $pet['id']);
            $mapUrl = null;
            if (envv('API_KEY') && $pet['direccion']) $mapUrl = 'https://www.google.com/maps/embed/v1/place?key=' . urlencode(envv('API_KEY')) . '&q=' . urlencode($pet['direccion'] . ', Mexico');
            render('detalle', [
                'title' => "{$pet['nombre']} - {$status} | AyudaPet",
                'metaTitle' => "{$pet['nombre']} - {$status} | AyudaPet",
                'metaDescription' => ($pet['descripcion'] ?: 'Reporte de mascota en AyudaPet.') . ($pet['direccion'] ? ' Ubicacion: ' . $pet['direccion'] . '.' : ''),
                'metaUrl' => $detailUrl,
                'metaImage' => $pet['principal'] ?: full_url('/static/og_image.png'),
                'mascota' => $pet,
                'isOwner' => owns_report($pet),
                'mapUrl' => $mapUrl,
                'share' => ['url' => $detailUrl, 'text' => "{$status}: {$pet['nombre']} en AyudaPet", 'message' => "{$status}: {$pet['nombre']} en AyudaPet {$detailUrl}"],
            ]);
            return;
        }

        if (preg_match('#^/mascotas/([a-f0-9]{32})/impulsar$#', $path, $m) && $method === 'POST') {
            require_login();
            $pet = get_mascota($m[1]);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El reporte solicitado no existe.'], 404); return; }
            if (!owns_report($pet)) { render('error', ['title' => 'Sin permiso', 'message' => 'Solo puedes impulsar tus propios reportes.'], 403); return; }
            if (is_boosted($pet)) { flash('Este reporte ya esta impulsado.', 'success'); redirect_to('/mascotas/' . $pet['id']); }
            $checkoutUrl = create_boost_checkout($pet);
            redirect_to($checkoutUrl);
        }

        if (preg_match('#^/mascotas/([a-f0-9]{32})/editar$#', $path, $m)) {
            require_login();
            $pet = get_mascota($m[1]);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El reporte solicitado no existe.'], 404); return; }
            if (!owns_report($pet)) { render('error', ['title' => 'Sin permiso', 'message' => 'Solo puedes editar tus propios reportes.'], 403); return; }
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
            if (!owns_report($pet)) { render('error', ['title' => 'Sin permiso', 'message' => 'Solo puedes eliminar tus propios reportes.'], 403); return; }
            ensure_archive_table();
            $pdo = db();
            try {
                $pdo->beginTransaction();
                archive_report($pet, 'deleted_by_owner');
                $pdo->prepare('DELETE FROM mascotas WHERE id = ? AND reportado_por = ?')->execute([$pet['id'], current_user_phone()]);
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
            if (!$pet || !owns_report($pet)) { http_response_code(403); echo json_encode(['ok' => false]); return; }
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
