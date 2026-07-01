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

    $host = envv('MYSQL_HOST', envv('DB_HOST', 'mysql'));
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

function e($value): string {
    return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
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
    return db()->query('SELECT * FROM mascotas ORDER BY creado_at DESC LIMIT 80')->fetchAll();
}

function list_user_reports(string $phone): array {
    $stmt = db()->prepare('SELECT * FROM mascotas WHERE reportado_por = ? ORDER BY creado_at DESC');
    $stmt->execute([$phone]);
    return $stmt->fetchAll();
}

function get_mascota(string $id): ?array {
    $stmt = db()->prepare('SELECT * FROM mascotas WHERE id = ? LIMIT 1');
    $stmt->execute([$id]);
    $pet = $stmt->fetch();
    return $pet ?: null;
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
    $name = post_value('nombre');
    if (!$name) throw new RuntimeException('El nombre de la mascota es obligatorio.');
    $existing = $existing ?? [];

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
        'nombre' => $name,
        'descripcion' => post_value('descripcion'),
        'contacto' => post_value('contacto'),
        'principal' => $principal,
        'secundarias' => json_encode($secondaries, JSON_UNESCAPED_SLASHES),
        'fecha' => post_value('fecha'),
        'edad' => post_value('edad'),
        'raza' => post_value('raza'),
        'genero' => post_value('genero'),
        'color' => post_value('color'),
        'collar' => post_value('collar'),
        'docil' => post_value('docil'),
        'direccion' => post_value('direccion'),
        'calles' => null,
        'dueno' => null,
        'recompensa' => post_value('recompensa'),
        'encontrado' => isset($_POST['encontrado']) ? 1 : 0,
    ];
}

function create_report(): string {
    $id = bin2hex(random_bytes(16));
    $data = report_payload($id);
    $sql = 'INSERT INTO mascotas (id, reportado_por, nombre, descripcion, contacto, principal, secundarias, fecha, edad, raza, genero, color, collar, docil, direccion, calles, dueno, recompensa, encontrado)
            VALUES (:id, :reportado_por, :nombre, :descripcion, :contacto, :principal, :secundarias, :fecha, :edad, :raza, :genero, :color, :collar, :docil, :direccion, :calles, :dueno, :recompensa, :encontrado)';
    $stmt = db()->prepare($sql);
    $stmt->execute(['id' => $id, 'reportado_por' => current_user_phone()] + $data);
    return $id;
}

function update_report(string $id, array $existing): void {
    $data = report_payload($id, $existing);
    $sets = [];
    foreach ($data as $key => $_) $sets[] = "{$key} = :{$key}";
    $stmt = db()->prepare('UPDATE mascotas SET ' . implode(', ', $sets) . ' WHERE id = :id AND reportado_por = :reportado_por');
    $stmt->execute($data + ['id' => $id, 'reportado_por' => current_user_phone()]);
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
        <a class="btn ghost" href="/logout">Cerrar sesion</a>
      <?php else: ?>
        <a class="btn ghost <?= $active('/login') ?>" href="/login">Entrar</a>
        <a class="btn ghost <?= $active('/registro') ?>" href="/registro">Crear cuenta</a>
        <a class="btn ghost <?= $active('/') ?>" href="/">Reportes</a>
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
    if ($view === 'reportar') { view_reportar($mascota, $editing, $mapsApiKey); return; }
    if ($view === 'error') { view_error($title, $message); return; }
}

function css(): string {
    return <<<'CSS'
:root{--ink:#18212f;--muted:#617084;--line:#dfe7ef;--paper:#fff;--wash:#f5f7fb;--brand:#e85035;--brand-dark:#b93824;--blue:#176b87;--green:#287c5a;--amber:#a46614;--shadow:0 18px 48px rgba(20,32,48,.10)}*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);background:var(--wash)}a{color:inherit;text-decoration:none}.topbar{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{max-width:1440px;margin:0 auto;min-height:70px;padding:0 clamp(12px,4vw,22px);display:flex;align-items:center;justify-content:space-between;gap:20px}.menu-toggle{width:42px;height:42px;border:1px solid var(--line);border-radius:8px;background:#fff;display:inline-grid;place-items:center;cursor:pointer}.menu-toggle span,.menu-toggle span:before,.menu-toggle span:after{width:19px;height:2px;display:block;background:var(--ink);content:"";border-radius:99px}.menu-toggle span:before{transform:translateY(-6px)}.menu-toggle span:after{transform:translateY(4px)}.brand{display:flex;align-items:center;gap:12px;font-weight:900;letter-spacing:.02em}.mark{width:44px;height:44px;border-radius:999px;object-fit:cover;border:2px solid #fff;box-shadow:0 10px 24px rgba(20,32,48,.18)}.nav-spacer{width:42px}.menu-backdrop{position:fixed;inset:0;z-index:30;background:rgba(10,16,24,.42);opacity:0;pointer-events:none;transition:opacity .18s ease}.side-menu{position:fixed;inset:0 auto 0 0;z-index:40;width:min(330px,88vw);background:#fff;border-right:1px solid var(--line);box-shadow:var(--shadow);transform:translateX(-100%);transition:transform .2s ease;display:flex;flex-direction:column}body.menu-open .menu-backdrop{opacity:1;pointer-events:auto}body.menu-open .side-menu{transform:translateX(0)}.menu-head{min-height:72px;padding:16px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:12px}.menu-close{width:38px;height:38px;border:1px solid var(--line);border-radius:8px;background:#fff;font-size:1.4rem;cursor:pointer}.menu-links{padding:14px;display:grid;gap:8px}.menu-links .btn{width:100%;justify-content:flex-start;min-height:48px}.menu-links .btn.active{background:var(--brand);color:#fff;border-color:var(--brand)}.menu-foot{margin-top:auto;padding:16px 18px;color:var(--muted);border-top:1px solid var(--line);font-size:.9rem}.shell{max-width:1440px;margin:0 auto;padding:clamp(16px,4vw,34px) clamp(12px,4vw,22px) 48px}.hero{display:grid;grid-template-columns:minmax(0,1.7fr) 340px;gap:20px;margin-bottom:30px}.hero-main{min-height:300px;padding:42px;border-radius:8px;color:#fff;background:linear-gradient(110deg,rgba(24,33,47,.94),rgba(23,107,135,.82)),url("https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=1600&q=80");background-size:cover;background-position:center;box-shadow:var(--shadow);display:flex;flex-direction:column;justify-content:flex-end}.eyebrow{margin:0 0 12px;font-weight:800;color:#ffd9c7;text-transform:uppercase;font-size:.78rem}h1{margin:0;font-size:clamp(2rem,5vw,4.1rem);line-height:1;letter-spacing:0}.hero-main p{max-width:650px;color:rgba(255,255,255,.88);font-size:1.08rem;line-height:1.6;margin:18px 0 0}.panel,.pet-card,.form-panel{background:var(--paper);border:1px solid var(--line);border-radius:8px;box-shadow:0 10px 34px rgba(20,32,48,.06)}.panel{padding:22px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:18px}.stat{padding:16px;border:1px solid var(--line);border-radius:8px;background:#fbfdff}.stat strong{display:block;font-size:1.8rem}.stat span,.meta,.hint{color:var(--muted)}.stats-dropdown summary{list-style:none;display:flex;align-items:center;justify-content:space-between;gap:12px;cursor:pointer;font-weight:900}.stats-dropdown summary::-webkit-details-marker{display:none}.stats-dropdown summary:after{content:"+";color:var(--muted);font-size:1.25rem}.stats-dropdown[open] summary:after{content:"-"}.search-panel{margin:0 0 24px}.search-form{display:grid;grid-template-columns:minmax(0,1fr) 190px auto;gap:10px;align-items:end}.field{display:grid;gap:7px;min-width:0}.field.full{grid-column:1/-1}.search-form label,label{font-weight:800;font-size:.92rem}.filter-meta{margin:12px 0 0;color:var(--muted)}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}.actions form{display:flex;min-width:132px}.btn{border:0;border-radius:8px;min-height:42px;padding:0 16px;display:inline-flex;align-items:center;justify-content:center;gap:8px;font-weight:800;cursor:pointer;background:#e8edf3;color:var(--ink);text-align:center;max-width:100%}.btn.primary{color:#fff;background:var(--brand)}.btn.primary:hover{background:var(--brand-dark)}.btn.ghost{background:transparent;border:1px solid var(--line)}.section-head{display:flex;align-items:end;justify-content:space-between;gap:18px;margin:26px 0 14px}.section-head h2{margin:0;font-size:1.35rem}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:20px}.pet-card{position:relative;overflow:hidden;display:grid;grid-template-columns:220px minmax(0,1fr);min-height:220px;align-items:start;color:inherit}.pet-card:hover{transform:translateY(-2px);transition:transform .16s ease}.pet-media{position:relative;width:220px;height:220px;aspect-ratio:1;background:linear-gradient(135deg,rgba(232,80,53,.20),rgba(23,107,135,.20)),#edf3f7;display:grid;place-items:center;font-size:2rem;font-weight:900;color:var(--blue)}.pet-media img{width:100%;height:100%;object-fit:cover;display:block}.pet-body{min-height:220px;padding:20px 60px 20px 20px;border-left:1px solid var(--line);display:grid;gap:10px;align-content:start;min-width:0}.pet-body h3{margin:0;font-size:1.15rem}.pet-summary{margin:0;color:var(--muted);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.badge{display:inline-flex;align-items:center;min-height:28px;padding:0 10px;border-radius:999px;background:#eef5f7;color:var(--blue);font-weight:800;font-size:.78rem}.badge.lost{background:#fff2ef;color:var(--brand-dark)}.badge.found{background:#e9f7f0;color:var(--green)}.photo-badge{position:absolute;top:10px;right:10px;box-shadow:0 10px 24px rgba(20,32,48,.16)}.view-cue{position:absolute;top:12px;right:12px;width:34px;height:34px;display:grid;place-items:center;border-radius:999px;background:rgba(255,255,255,.94);border:1px solid rgba(20,32,48,.10);box-shadow:0 10px 24px rgba(20,32,48,.16);pointer-events:none}.view-cue svg{width:18px;height:18px;stroke:currentColor;stroke-width:2.2;fill:none;stroke-linecap:round;stroke-linejoin:round}.form-wrap{max-width:1040px;margin:0 auto}.form-panel{padding:clamp(20px,4vw,34px)}.form-panel h1{color:var(--ink);font-size:clamp(1.8rem,4vw,2.7rem)}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:20px}.login-form{grid-template-columns:repeat(2,minmax(0,1fr));align-items:start}.login-actions{grid-column:1/-1;margin-top:6px}input,textarea,select{width:100%;min-width:0;max-width:100%;border:1px solid #cfd9e4;border-radius:8px;min-height:44px;padding:10px 12px;background:#fff;color:var(--ink);font:inherit}textarea{min-height:118px;resize:vertical}input:focus,textarea:focus,select:focus{outline:3px solid rgba(23,107,135,.16);border-color:var(--blue)}.phone-box{display:grid;grid-template-columns:auto 1fr;align-items:center;border:1px solid #cfd9e4;border-radius:8px;background:#fff;overflow:hidden}.phone-prefix{min-height:44px;padding:0 12px;display:inline-flex;align-items:center;gap:8px;border-right:1px solid var(--line);background:#f8fafc;font-weight:900;white-space:nowrap}.phone-box input{border:0;border-radius:0}.detail-wrap{display:grid;grid-template-columns:360px minmax(0,1fr);gap:28px;max-width:1120px;margin-inline:auto;align-items:start}.detail-photos{display:grid;gap:12px;max-width:360px}.detail-photo{overflow:hidden;padding:0;aspect-ratio:1;border-radius:8px;background:#edf3f7}.detail-media{position:relative;height:100%;aspect-ratio:1;display:grid;place-items:center;color:var(--blue);font-size:3rem;font-weight:900;background:linear-gradient(135deg,rgba(232,80,53,.18),rgba(23,107,135,.18)),#edf3f7}.detail-media img{width:100%;height:100%;object-fit:contain;display:block;background:#edf3f7}.info-list{display:grid;gap:0;margin-top:22px;border-top:1px solid var(--line)}.info-row{padding:12px 0;border-bottom:1px solid var(--line);display:grid;gap:3px}.info-row strong{font-size:.82rem;text-transform:uppercase;color:var(--muted)}.split-info{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 18px;margin-top:18px;border-top:1px solid var(--line)}.map-frame{width:100%;aspect-ratio:16/9;margin-top:22px;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#edf3f7}.map-frame iframe{width:100%;height:100%;border:0;display:block}.contact-actions,.share-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:18px}.share-title{grid-column:1/-1;margin:0;color:var(--muted);font-weight:900;text-transform:uppercase;font-size:.82rem}.btn.whatsapp{background:#25d366;color:#fff}.wa-icon{width:20px;height:20px;display:inline-block;flex:0 0 auto}.gallery{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:16px}.gallery img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:8px;border:1px solid var(--line)}.profile-layout{display:grid;grid-template-columns:420px minmax(0,1fr);gap:22px;align-items:start}.profile-card{padding:clamp(20px,4vw,32px)}.avatar{width:112px;height:112px;border-radius:999px;object-fit:cover;border:4px solid #fff;box-shadow:var(--shadow);background:#edf3f7;display:grid;place-items:center;color:var(--blue);font-size:2.4rem;font-weight:900;overflow:hidden}.avatar img{width:100%;height:100%;object-fit:cover;display:block}.mini-list{display:grid;gap:10px;margin-top:16px}.mini-report{display:grid;grid-template-columns:72px 1fr;gap:12px;align-items:center;padding:10px;border:1px solid var(--line);border-radius:8px;background:#fff}.mini-report img,.mini-thumb{width:72px;height:72px;object-fit:cover;border-radius:8px;background:#edf3f7;display:grid;place-items:center;color:var(--blue);font-weight:900}.edit-image-grid,.edit-images{display:flex;flex-wrap:wrap;gap:10px}.edit-image-item{position:relative;width:104px;height:104px;border:1px solid var(--line);border-radius:8px;background:#fbfdff;display:grid;overflow:hidden}.edit-image-item.removing{display:none}.edit-image-item img{width:100%;height:100%;object-fit:cover;display:block}.remove-image-check{position:absolute;top:8px;right:8px;width:34px;height:34px;border-radius:999px;display:grid;place-items:center;background:rgba(184,56,36,.95);color:#fff;font-weight:900;box-shadow:0 10px 24px rgba(20,32,48,.20);cursor:pointer}.remove-image-check input{position:absolute;opacity:0;pointer-events:none}.zoomable{cursor:zoom-in}.lightbox{position:fixed;inset:0;z-index:80;display:none;align-items:center;justify-content:center;padding:24px;background:rgba(6,10,16,.88)}.lightbox.open{display:flex}.lightbox img{max-width:min(1100px,94vw);max-height:88vh;object-fit:contain;border-radius:8px;box-shadow:0 24px 80px rgba(0,0,0,.42);background:#111}.lightbox-close{position:absolute;top:16px;right:16px;width:42px;height:42px;border:1px solid rgba(255,255,255,.25);border-radius:8px;background:rgba(255,255,255,.12);color:#fff;font-size:1.6rem;cursor:pointer}.flash{border-radius:8px;padding:12px 14px;border:1px solid var(--line);background:#fff;font-weight:700;margin-bottom:10px}.flash.success{border-color:#bde5d0;background:#effaf4;color:var(--green)}.flash.error{border-color:#f1b8aa;background:#fff2ef;color:var(--brand-dark)}.flash.warning{border-color:#edd398;background:#fff8e8;color:var(--amber)}.empty{padding:34px;text-align:center;color:var(--muted);border:1px dashed #c6d2de;border-radius:8px;background:#fff}footer{color:var(--muted);text-align:center;padding:20px}@media(max-width:840px){.hero,.grid,.form-grid,.login-form,.detail-wrap,.profile-layout{grid-template-columns:1fr}.contact-actions{grid-template-columns:1fr}.search-form{grid-template-columns:1fr}.actions{flex-direction:column;align-items:stretch}.actions .btn,.actions form{width:100%}.stats{grid-template-columns:1fr}.detail-photos{max-width:none}}@media(max-width:420px){.pet-card{grid-template-columns:104px minmax(0,1fr);min-height:104px}.pet-media{width:104px;height:104px;font-size:1.55rem}.pet-body{min-height:104px;padding:12px 44px 12px 12px;gap:7px}.pet-body h3{font-size:1rem}.pet-summary{-webkit-line-clamp:1}.photo-badge{top:7px;right:7px;min-height:24px;padding:0 8px;font-size:.68rem}.view-cue{top:8px;right:8px;width:28px;height:28px}.hero-main{min-height:260px}.form-panel,.profile-card,.panel{padding:16px}}
CSS;
}

function js(): string {
    return <<<'JS'
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
document.querySelectorAll("[data-native-share-button]").forEach((button)=>button.addEventListener("click",async()=>{const shareData={title:button.dataset.shareTitle||document.title,text:button.dataset.shareText||"",url:button.dataset.shareUrl||window.location.href};if(navigator.share){try{await navigator.share(shareData);return}catch(error){if(error?.name==="AbortError")return}}const original=button.textContent;button.textContent="Usa copiar enlace";window.setTimeout(()=>{button.textContent=original},1800)}));
document.querySelectorAll("[data-max-files]").forEach((input)=>input.addEventListener("change",()=>{const maxFiles=Number(input.dataset.maxFiles||0);if(input.files.length>maxFiles){input.value="";alert(maxFiles>0?`Solo puedes seleccionar hasta ${maxFiles} imagenes.`:"Ya tienes el maximo de 3 fotos adicionales.")}}));
JS;
}

function view_index(array $mascotas, array $stats, array $filters): void { ?>
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
  <section class="panel search-panel">
    <form class="search-form" method="get" action="/">
      <div class="field"><label for="q">Buscar</label><input id="q" name="q" value="<?= e($filters['q']) ?>" placeholder="Nombre, direccion o contacto"></div>
      <div class="field"><label for="estado">Filtro</label><select id="estado" name="estado">
        <?php foreach (['todos'=>'Todos','perdidos'=>'Perdidos','localizados'=>'Localizados'] as $value => $label): ?>
          <option value="<?= e($value) ?>" <?= $filters['estado'] === $value ? 'selected' : '' ?>><?= e($label) ?></option>
        <?php endforeach; ?>
      </select></div>
      <button class="btn primary" type="submit">Buscar</button>
    </form>
    <p class="filter-meta"><?= e($filters['resultados']) ?> resultado<?= $filters['resultados'] == 1 ? '' : 's' ?></p>
  </section>
  <div class="section-head"><div><h2>Reportes recientes</h2><p>Informacion publica enviada por la comunidad.</p></div></div>
  <?php if ($mascotas): ?><section class="grid">
    <?php foreach ($mascotas as $pet): ?>
      <a class="pet-card" href="/mascotas/<?= e($pet['id']) ?>">
        <div class="pet-media">
          <?php if ($pet['principal']): ?><img class="zoomable" src="<?= e($pet['principal']) ?>" alt="<?= e($pet['nombre']) ?>" data-zoom-src="<?= e($pet['principal']) ?>"><?php else: ?><?= e(first_letter($pet['nombre'] ?: '?')) ?><?php endif; ?>
          <span class="badge photo-badge <?= $pet['encontrado'] ? 'found' : 'lost' ?>"><?= $pet['encontrado'] ? 'Localizado' : 'Perdido' ?></span>
        </div>
        <div class="pet-body">
          <h3><?= e($pet['nombre']) ?></h3>
          <p class="meta"><?php if ($pet['direccion']): ?><strong>Direccion:</strong> <?= e($pet['direccion']) ?><br><?php endif; ?></p>
          <?php if ($pet['descripcion']): ?><p class="pet-summary"><?= e($pet['descripcion']) ?></p><?php endif; ?>
        </div>
        <span class="view-cue" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z"></path><circle cx="12" cy="12" r="2.8"></circle></svg></span>
      </a>
    <?php endforeach; ?>
  </section><?php else: ?><div class="empty">Todavia no hay reportes publicados.</div><?php endif; ?>
<?php }

function view_detalle(array $mascota, bool $isOwner, array $share, ?string $mapUrl): void {
    $secundarias = pet_secondaries($mascota);
    $callPhone = phone_digits($mascota['contacto'] ?? '');
    $waPhone = whatsapp_digits($mascota['contacto'] ?? '');
    ?>
  <section class="detail-wrap">
    <div class="detail-photos">
      <div class="detail-photo"><div class="detail-media">
        <?php if ($mascota['principal']): ?><img class="zoomable" src="<?= e($mascota['principal']) ?>" alt="<?= e($mascota['nombre']) ?>" data-zoom-src="<?= e($mascota['principal']) ?>"><?php else: ?><?= e(first_letter($mascota['nombre'] ?: '?')) ?><?php endif; ?>
        <span class="badge photo-badge <?= $mascota['encontrado'] ? 'found' : 'lost' ?>"><?= $mascota['encontrado'] ? 'Localizado' : 'Perdido' ?></span>
      </div></div>
      <?php if ($secundarias): ?><div class="gallery"><?php foreach ($secundarias as $image): ?><img class="zoomable" src="<?= e($image) ?>" alt="Foto de <?= e($mascota['nombre']) ?>" data-zoom-src="<?= e($image) ?>"><?php endforeach; ?></div><?php endif; ?>
    </div>
    <article class="detail-info">
      <?php if ($isOwner): ?><div class="actions" style="margin-top:0;"><a class="btn primary" href="/mascotas/<?= e($mascota['id']) ?>/editar">Editar</a><form method="post" action="/mascotas/<?= e($mascota['id']) ?>/eliminar" onsubmit="return confirm('Eliminar este reporte?');"><button class="btn" type="submit">Eliminar</button></form></div><?php endif; ?>
      <div class="info-list"><?php info_row('Fecha de extravio', $mascota['fecha']); info_row('Nombre de mascota', $mascota['nombre']); info_row('Descripcion', $mascota['descripcion']); ?></div>
      <div class="split-info"><?php foreach ([['Edad','edad'],['Raza','raza'],['Genero','genero'],['Color','color'],['Collar','collar'],['Docil','docil']] as [$label,$key]) info_row($label, $mascota[$key]); ?></div>
      <?php if ($mapUrl): ?><div class="map-frame"><iframe src="<?= e($mapUrl) ?>" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen title="Mapa de direccion de extravio"></iframe></div><?php endif; ?>
      <div class="info-list"><?php info_row('Direccion de extravio', $mascota['direccion']); ?></div>
      <div class="split-info"><?php info_row('Recompensa', $mascota['recompensa']); ?></div>
      <?php if ($callPhone): ?><div class="contact-actions"><a class="btn primary" href="tel:<?= e($callPhone) ?>">Llamar</a><a class="btn whatsapp" href="https://wa.me/<?= e($waPhone) ?>" target="_blank" rel="noopener">WhatsApp</a></div><?php endif; ?>
      <div class="share-actions" aria-label="Compartir reporte"><p class="share-title">Comparte:</p><button class="btn primary" type="button" data-native-share-button data-share-title="<?= e($share['text']) ?>" data-share-text="<?= e($share['message']) ?>" data-share-url="<?= e($share['url']) ?>">Compartir</button><button class="btn" type="button" data-copy-url="<?= e($share['url']) ?>">Copiar enlace</button></div>
      <div class="actions"><a class="btn" href="/">Volver a reportes</a></div>
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
    <div class="panel profile-card"><p class="eyebrow" style="color:var(--brand);">Seguridad</p><h1>Cambiar contrasena</h1><form method="post" action="/perfil/password" class="form-grid"><div class="field full"><label for="current_password">Contrasena actual</label><input id="current_password" name="current_password" type="password" autocomplete="current-password" required></div><div class="field"><label for="new_password">Nueva contrasena</label><input id="new_password" name="new_password" type="password" autocomplete="new-password" minlength="8" required></div><div class="field"><label for="confirm_password">Confirmar contrasena</label><input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" minlength="8" required></div><div class="actions"><button class="btn primary" type="submit">Actualizar contrasena</button></div></form></div>
  </section>
  <section class="panel profile-card" style="margin-top:18px;"><div class="section-head" style="margin-top:0;"><div><h2>Mis reportes</h2><p>Reportes publicados con tu numero registrado.</p></div><a class="btn primary" href="/reportar">Nuevo reporte</a></div><?php if ($reportes): ?><div class="mini-list"><?php foreach ($reportes as $pet): ?><a class="mini-report" href="/mascotas/<?= e($pet['id']) ?>"><?php if ($pet['principal']): ?><img src="<?= e($pet['principal']) ?>" alt="<?= e($pet['nombre']) ?>"><?php else: ?><span class="mini-thumb"><?= e(first_letter($pet['nombre'] ?: '?')) ?></span><?php endif; ?><span><strong><?= e($pet['nombre']) ?></strong><br><span class="meta"><?= $pet['encontrado'] ? 'Localizado' : 'Perdido' ?></span></span></a><?php endforeach; ?></div><?php else: ?><div class="empty">Todavia no tienes reportes publicados.</div><?php endif; ?></section>
<?php }

function view_reportar(array $mascota, bool $editing, ?string $mapsApiKey): void {
    $secundarias = $editing ? pet_secondaries($mascota) : [];
    $slots = max(0, MAX_SECONDARY_IMAGES - count($secundarias));
    ?>
  <section class="form-wrap"><form class="form-panel" method="post" enctype="multipart/form-data"><p class="eyebrow" style="color:var(--brand);"><?= $editing ? 'Editar reporte' : 'Nuevo reporte' ?></p><h1><?= $editing ? 'Editar reporte' : 'Datos de la mascota' ?></h1><div class="form-grid">
    <div class="field full"><label for="principal">Foto principal</label><?php if ($editing && $mascota['principal']): ?><div class="edit-images"><div class="edit-image-item"><img src="<?= e($mascota['principal']) ?>" alt="Foto principal actual"><label class="remove-image-check" title="Quitar" data-remove-image data-remove-url="/mascotas/<?= e($mascota['id']) ?>/imagenes/eliminar" data-remove-target="principal"><input type="checkbox" name="remove_principal"><span>&times;</span></label></div></div><?php endif; ?><input id="principal" name="principal" type="file" accept="image/*"></div>
    <div class="field full"><label>Fotos adicionales</label><?php if ($secundarias): ?><div class="edit-image-grid"><?php foreach ($secundarias as $image): ?><div class="edit-image-item"><img src="<?= e($image) ?>" alt="Foto secundaria actual"><label class="remove-image-check" title="Quitar" data-remove-image data-remove-url="/mascotas/<?= e($mascota['id']) ?>/imagenes/eliminar" data-remove-target="secundaria" data-remove-image-url="<?= e($image) ?>"><input type="checkbox" name="remove_secundarias[]" value="<?= e($image) ?>"><span>&times;</span></label></div><?php endforeach; ?></div><?php endif; ?><input name="secundarias[]" type="file" accept="image/*" multiple data-max-files="<?= e($slots) ?>"><span class="hint">Puedes seleccionar hasta 3 imagenes adicionales.</span></div>
    <div class="field"><label for="fecha">Fecha de extravio</label><input id="fecha" name="fecha" type="date" value="<?= e($mascota['fecha'] ?? '') ?>"></div>
    <div class="field"><label for="nombre">Nombre de mascota</label><input id="nombre" name="nombre" value="<?= e($mascota['nombre'] ?? '') ?>" required></div>
    <div class="field full"><label for="descripcion">Descripcion</label><textarea id="descripcion" name="descripcion" placeholder="Senales particulares, temperamento, ultima vez visto"><?= e($mascota['descripcion'] ?? '') ?></textarea></div>
    <?php input_field('edad','Edad',$mascota); input_field('raza','Raza',$mascota); ?>
    <div class="field"><label for="genero">Genero</label><select id="genero" name="genero"><option value="">Seleccionar</option><?php foreach (['Macho','Hembra','No se sabe'] as $opt): ?><option <?= ($mascota['genero'] ?? '') === $opt ? 'selected' : '' ?>><?= e($opt) ?></option><?php endforeach; ?></select></div>
    <?php input_field('color','Color',$mascota); input_field('collar','Collar',$mascota); input_field('docil','Docil',$mascota, 'Docil, nervioso, asustado'); ?>
    <div class="field full"><label for="direccion">Direccion de extravio</label><input id="direccion" name="direccion" value="<?= e($mascota['direccion'] ?? '') ?>" autocomplete="off" data-address-autocomplete></div>
    <?php input_field('recompensa','Recompensa',$mascota); input_field('contacto','Contacto publico',$mascota, 'Telefono, WhatsApp o correo'); ?>
    <div class="field"><label>Estado del reporte</label><label class="btn ghost"><input type="checkbox" name="encontrado" <?= !empty($mascota['encontrado']) ? 'checked' : '' ?>> Localizado</label></div>
  </div><div class="actions"><button class="btn primary" type="submit"><?= $editing ? 'Guardar cambios' : 'Publicar reporte' ?></button><a class="btn" href="<?= $editing ? '/mascotas/' . e($mascota['id']) : '/' ?>">Cancelar</a></div></form>
  <?php if ($mapsApiKey): ?><script>
    window.initAddressAutocomplete = function () {
      const input = document.querySelector("[data-address-autocomplete]");
      if (!input || !window.google?.maps?.places) return;
      const autocomplete = new google.maps.places.Autocomplete(input, {
        componentRestrictions: { country: "mx" },
        fields: ["address_components", "formatted_address", "name"],
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
        input.setAttribute("readonly", "readonly");
        document.querySelectorAll(".pac-container").forEach((container) => {
          container.style.display = "none";
        });
        window.setTimeout(() => input.removeAttribute("readonly"), 250);
      };

      const applySelectedPlace = () => {
        const place = autocomplete.getPlace();
        if (!place || (!place.address_components && !place.formatted_address && !place.name)) {
          closeSuggestions();
          return;
        }
        input.value = privateAddress(place);
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        closeSuggestions();
      };

      autocomplete.addListener("place_changed", applySelectedPlace);

      const handleSuggestionPick = (event) => {
        if (!event.target.closest(".pac-item")) return;
        window.setTimeout(applySelectedPlace, 80);
        window.setTimeout(applySelectedPlace, 220);
      };

      document.addEventListener("mousedown", handleSuggestionPick, true);
      document.addEventListener("touchend", handleSuggestionPick, true);
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
        if ($path === '/') {
            $pets = list_mascotas();
            $q = trim((string)($_GET['q'] ?? ''));
            $estado = strtolower(trim((string)($_GET['estado'] ?? 'todos')));
            $stats = [
                'total' => count($pets),
                'activos' => count(array_filter($pets, function ($p) { return !$p['encontrado']; })),
                'encontrados' => count(array_filter($pets, function ($p) { return $p['encontrado']; })),
            ];
            if ($estado === 'perdidos') {
                $pets = array_values(array_filter($pets, function ($p) { return !$p['encontrado']; }));
            }
            if ($estado === 'localizados') {
                $pets = array_values(array_filter($pets, function ($p) { return $p['encontrado']; }));
            }
            if ($q !== '') {
                $needle = lower_text($q);
                $pets = array_values(array_filter($pets, function ($p) use ($needle) {
                    return contains_text(lower_text(implode(' ', [$p['nombre'], $p['descripcion'], $p['direccion'], $p['calles'], $p['contacto']])), $needle);
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

        if ($path === '/reportar') {
            require_login();
            if ($method === 'POST') {
                try { create_report(); flash('Reporte publicado correctamente.', 'success'); redirect_to('/'); }
                catch (RuntimeException $e) { flash($e->getMessage(), 'error'); redirect_to('/reportar'); }
            }
            render('reportar', ['title' => 'Reportar mascota', 'mascota' => [], 'editing' => false, 'mapsApiKey' => envv('API_KEY')]);
            return;
        }

        if (preg_match('#^/mascotas/([a-f0-9]{32})$#', $path, $m)) {
            $pet = get_mascota($m[1]);
            if (!$pet) { render('error', ['title' => 'Reporte no encontrado', 'message' => 'El reporte solicitado no existe.'], 404); return; }
            $status = $pet['encontrado'] ? 'Localizado' : 'Perdido';
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
            db()->prepare('DELETE FROM mascotas WHERE id = ? AND reportado_por = ?')->execute([$m[1], current_user_phone()]);
            flash('Reporte eliminado.', 'success');
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

route();
