<?php
// 親テーマ（Cocoon）のスタイルを読み込む
function lightlog_child_enqueue_styles() {
    wp_enqueue_style(
        'cocoon-parent-style',
        get_template_directory_uri() . '/style.css'
    );
}
add_action( 'wp_enqueue_scripts', 'lightlog_child_enqueue_styles' );
