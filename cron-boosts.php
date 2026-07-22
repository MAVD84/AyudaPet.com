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
    $restored = restore_resolved_archived_reports();
    $archives = sync_report_archives();
    $freeReports = remove_expired_free_reports();
    echo 'boost_checked=' . $result['checked'] . ' boost_sent=' . $result['sent'] . ' boost_failed=' . $result['failed']
        . ' restored_checked=' . $restored['checked'] . ' restored=' . $restored['restored'] . ' restored_failed=' . $restored['failed']
        . ' archive_checked=' . $archives['checked'] . ' archive_synced=' . $archives['synced'] . ' archive_failed=' . $archives['failed']
        . ' free_checked=' . $freeReports['checked'] . ' free_removed=' . $freeReports['removed'] . ' free_failed=' . $freeReports['failed'] . PHP_EOL;
    exit(($result['failed'] + $restored['failed'] + $archives['failed'] + $freeReports['failed']) > 0 ? 1 : 0);
} catch (Throwable $e) {
    error_log('Cron boosts failed: ' . $e->getMessage());
    echo 'error=' . $e->getMessage() . PHP_EOL;
    exit(1);
}
