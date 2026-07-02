<?php
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    echo "Forbidden\n";
    exit(1);
}

define('AYUDAPET_SKIP_ROUTE', true);
require __DIR__ . '/index.php';

try {
    $result = process_expired_boosts();
    echo 'checked=' . $result['checked'] . ' sent=' . $result['sent'] . ' failed=' . $result['failed'] . PHP_EOL;
    exit($result['failed'] > 0 ? 1 : 0);
} catch (Throwable $e) {
    error_log('Cron boosts failed: ' . $e->getMessage());
    echo 'error=' . $e->getMessage() . PHP_EOL;
    exit(1);
}
