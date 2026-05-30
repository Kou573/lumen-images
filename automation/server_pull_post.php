<?php
/**
 * Lumen Industries — サーバーサイド pull 投稿スクリプト（Plan B）
 * =============================================================
 * エックスサーバーの Cron で実行する想定。
 *
 * 目的:
 *   GitHub Actions が生成・コミットした articles/latest.json を
 *   「サーバー自身（日本IP）」が取得し、WordPress に直接投稿する。
 *
 * なぜ Plan B か:
 *   - REST / XML-RPC は GitHub Actions（海外IP）からだと
 *     エックスサーバーの「国外IPアクセス制限」で 403 になる。
 *   - このスクリプトは wp-load.php 経由で WordPress を直接操作するため、
 *     REST も XML-RPC も HTTP も使わない → 国外IP制限・WAF の影響をゼロにできる。
 *
 * 重複投稿の防止（旧プラグインの「1日9回投稿」問題を再発させないための要）:
 *   ① 状態ファイル last_posted.json に最後に投稿したタイトルを記録し、一致ならスキップ
 *   ② WordPress 上に同タイトルの公開記事が既にあればスキップ
 *   ③ flock による多重起動ロック（Cron 重複起動でも二重投稿しない）
 *
 * デプロイ手順は automation/B_DEPLOY_GUIDE.md を参照。
 */

// ============================================================
// 設定（デプロイ時に環境に合わせて書き換える）
// ============================================================

// WordPress の wp-load.php への絶対パス。
// 例: /home/xs752098/glowlog.net/public_html/wp-load.php
$WP_LOAD = getenv('LUMEN_WP_LOAD')
    ?: '/home/xs752098/glowlog.net/public_html/wp-load.php';

// 取得元（main ブランチの latest.json の raw URL）
$LATEST_URL = getenv('LUMEN_LATEST_URL')
    ?: 'https://raw.githubusercontent.com/Kou573/lumen-industries/main/articles/latest.json';

// 状態・ログ・ロックファイル（このスクリプトと同じディレクトリに作成）
$STATE_FILE = __DIR__ . '/last_posted.json';
$LOG_FILE   = __DIR__ . '/pull_post.log';
$LOCK_FILE  = __DIR__ . '/pull_post.lock';

// true にすると実際には投稿せず、判定結果だけログに残す（初回テスト用）
$DRY_RUN = (getenv('LUMEN_DRY_RUN') === '1');

// 投稿者ユーザーID（通常は 1 = 管理者）
$DEFAULT_AUTHOR_ID = (int) (getenv('LUMEN_AUTHOR_ID') ?: 1);

// ============================================================
// ヘルパ
// ============================================================

function lumen_log(string $file, string $msg): void {
    @file_put_contents($file, '[' . date('c') . '] ' . $msg . "\n", FILE_APPEND);
    // Cron のメール通知にも出るよう標準出力にも吐く
    echo $msg . "\n";
}

/**
 * 同タイトルの公開済み記事を探す（WP_Query：新旧バージョンで動作）。
 */
function lumen_find_published_by_title(string $title) {
    $q = new WP_Query([
        'post_type'      => 'post',
        'post_status'    => 'publish',
        'title'          => $title,
        'posts_per_page' => 1,
        'no_found_rows'  => true,
    ]);
    return $q->have_posts() ? $q->posts[0] : null;
}

// ============================================================
// 多重起動ロック
// ============================================================

$lock = @fopen($LOCK_FILE, 'c');
if (!$lock || !flock($lock, LOCK_EX | LOCK_NB)) {
    lumen_log($LOG_FILE, '別プロセスが実行中のためスキップします。');
    exit(0);
}

// ============================================================
// latest.json を取得
// ============================================================

$ctx = stream_context_create([
    'http' => ['timeout' => 30, 'header' => "User-Agent: LumenPull/1.0\r\n"],
    'ssl'  => ['verify_peer' => true, 'verify_peer_name' => true],
]);
$raw = @file_get_contents($LATEST_URL, false, $ctx);
if ($raw === false) {
    lumen_log($LOG_FILE, 'latest.json の取得に失敗しました: ' . $LATEST_URL);
    exit(1);
}

$art = json_decode($raw, true);
if (!is_array($art) || empty($art['title'])) {
    lumen_log($LOG_FILE, 'latest.json の解析に失敗、または title がありません。');
    exit(1);
}
$title = trim($art['title']);

// ============================================================
// 重複チェック①: 状態ファイル
// ============================================================

$state = [];
if (file_exists($STATE_FILE)) {
    $state = json_decode((string) file_get_contents($STATE_FILE), true) ?: [];
}
if (isset($state['last_title']) && $state['last_title'] === $title) {
    lumen_log($LOG_FILE, "重複（状態ファイル一致）のためスキップ: {$title}");
    exit(0);
}

// ============================================================
// WordPress を読み込む
// ============================================================

if (!file_exists($WP_LOAD)) {
    lumen_log($LOG_FILE, "wp-load.php が見つかりません: {$WP_LOAD}");
    exit(1);
}
define('WP_USE_THEMES', false);
require_once $WP_LOAD;

// ============================================================
// 重複チェック②: WordPress 上の同タイトル公開記事
// ============================================================

$existing = lumen_find_published_by_title($title);
if ($existing) {
    lumen_log($LOG_FILE, "重複（WP既存 ID={$existing->ID}）のためスキップ: {$title}");
    @file_put_contents($STATE_FILE, json_encode(
        ['last_title' => $title, 'wp_post_id' => $existing->ID, 'at' => date('c')],
        JSON_UNESCAPED_UNICODE
    ));
    exit(0);
}

// ============================================================
// DRY_RUN ならここで終了
// ============================================================

if ($DRY_RUN) {
    lumen_log($LOG_FILE, "DRY_RUN: 新規投稿対象として検出（実投稿はしません）: {$title}");
    exit(0);
}

// ============================================================
// 投稿
// ============================================================

$postarr = [
    'post_title'   => $title,
    'post_content' => $art['content'] ?? '',
    'post_excerpt' => $art['meta_description'] ?? '',
    'post_status'  => 'publish',
    'post_author'  => $DEFAULT_AUTHOR_ID,
    'post_type'    => 'post',
];

$pid = wp_insert_post($postarr, true);
if (is_wp_error($pid)) {
    lumen_log($LOG_FILE, 'wp_insert_post に失敗: ' . $pid->get_error_message());
    exit(1);
}

// タグ（affiliate_tools をそのままタグ名として付与・自動作成）
if (!empty($art['affiliate_tools']) && is_array($art['affiliate_tools'])) {
    wp_set_post_tags($pid, $art['affiliate_tools'], true);
}

// アイキャッチ画像（外部URLを取り込んで featured image に設定）
if (!empty($art['featured_image_url'])) {
    require_once ABSPATH . 'wp-admin/includes/media.php';
    require_once ABSPATH . 'wp-admin/includes/file.php';
    require_once ABSPATH . 'wp-admin/includes/image.php';
    $att_id = media_sideload_image($art['featured_image_url'], $pid, $title, 'id');
    if (!is_wp_error($att_id)) {
        set_post_thumbnail($pid, $att_id);
    } else {
        lumen_log($LOG_FILE, 'アイキャッチ取得に失敗（本文冒頭画像を代用）: ' . $att_id->get_error_message());
    }
}

lumen_log($LOG_FILE, "投稿成功 ID={$pid}: {$title}");
@file_put_contents($STATE_FILE, json_encode(
    ['last_title' => $title, 'wp_post_id' => $pid, 'at' => date('c')],
    JSON_UNESCAPED_UNICODE
));
exit(0);
