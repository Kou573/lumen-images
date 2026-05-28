<?php
/**
 * Lightlog フロントページテンプレート
 * cocoon-child/ ディレクトリにこのファイルをアップロードしてください
 */
get_header();

// 人気記事（Cocoon の PV カウント順、なければ新着順）
$popular_args = array(
    'post_type'      => 'post',
    'post_status'    => 'publish',
    'posts_per_page' => 4,
    'meta_key'       => 'cocoon_pv_total',
    'orderby'        => 'meta_value_num',
    'order'          => 'DESC',
);
$popular_query = new WP_Query( $popular_args );
if ( ! $popular_query->have_posts() ) {
    $popular_args['meta_key'] = '';
    $popular_args['orderby']  = 'date';
    $popular_query = new WP_Query( $popular_args );
}

// カテゴリ一覧
$categories = get_categories( array(
    'orderby'    => 'count',
    'order'      => 'DESC',
    'hide_empty' => true,
    'number'     => 6,
) );

// 記事数・カテゴリ数
$post_count = wp_count_posts()->publish;
$cat_count  = count( get_categories( array( 'hide_empty' => true ) ) );
?>

<!-- Hero -->
<section class="lg-hero">
  <div class="lg-hero-inner">
    <span class="lg-hero-tag">SaaS × AI × 副業メディア</span>
    <h1 class="lg-hero-title">
      ビジネスを加速する<br>
      <span class="lg-hero-accent">ツール選びの羅針盤</span>
    </h1>
    <p class="lg-hero-desc">
      会計・プロジェクト管理・AI活用まで、実際に使って検証したSaaSレビューと副業情報をお届けします。
    </p>
    <a href="<?php echo esc_url( get_permalink( get_option( 'page_for_posts' ) ) ?: home_url( '/?page_id=2' ) ); ?>" class="lg-hero-btn">
      人気記事を読む →
    </a>
    <div class="lg-hero-stats">
      <div class="lg-stat">
        <div class="lg-stat-num"><?php echo esc_html( $post_count ); ?>+</div>
        <div class="lg-stat-label">ARTICLES</div>
      </div>
      <div class="lg-stat">
        <div class="lg-stat-num"><?php echo esc_html( $cat_count ); ?></div>
        <div class="lg-stat-label">CATEGORIES</div>
      </div>
      <div class="lg-stat">
        <div class="lg-stat-num">毎朝更新</div>
        <div class="lg-stat-label">DAILY 8AM</div>
      </div>
    </div>
  </div>
</section>

<!-- Main Content -->
<div class="lg-main-wrap">
  <main class="lg-main">
    <div class="lg-section-title">最新記事</div>
    <div class="lg-card-grid">
      <?php
      $paged = ( get_query_var( 'paged' ) ) ? get_query_var( 'paged' ) : 1;
      $args  = array(
          'post_type'      => 'post',
          'post_status'    => 'publish',
          'posts_per_page' => 8,
          'paged'          => $paged,
      );
      $query = new WP_Query( $args );

      if ( $query->have_posts() ) :
          while ( $query->have_posts() ) :
              $query->the_post();
              $thumb = get_the_post_thumbnail_url( get_the_ID(), 'medium_large' );
              $cats  = get_the_category();
              $cat   = ! empty( $cats ) ? $cats[0]->name : '';
              ?>
              <a href="<?php the_permalink(); ?>" class="lg-card">
                <div class="lg-card-img">
                  <?php if ( $thumb ) : ?>
                    <img src="<?php echo esc_url( $thumb ); ?>"
                         alt="<?php the_title_attribute(); ?>"
                         loading="lazy">
                  <?php else : ?>
                    <div class="lg-card-noimg">NO IMAGE</div>
                  <?php endif; ?>
                  <?php if ( $cat ) : ?>
                    <span class="lg-card-cat"><?php echo esc_html( $cat ); ?></span>
                  <?php endif; ?>
                </div>
                <div class="lg-card-body">
                  <div class="lg-card-title"><?php the_title(); ?></div>
                  <div class="lg-card-excerpt">
                    <?php echo wp_trim_words( get_the_excerpt(), 45, '…' ); ?>
                  </div>
                  <div class="lg-card-meta">
                    <?php echo get_the_date( 'Y.m.d' ); ?>
                  </div>
                </div>
              </a>
              <?php
          endwhile;
          wp_reset_postdata();
      else :
          echo '<p style="grid-column:1/-1;text-align:center;color:#78716c;">記事がまだありません。</p>';
      endif;
      ?>
    </div>

    <!-- Pagination -->
    <div class="lg-pagination">
      <?php
      $big = 999999999;
      echo paginate_links( array(
          'base'      => str_replace( $big, '%#%', esc_url( get_pagenum_link( $big ) ) ),
          'format'    => '?paged=%#%',
          'current'   => $paged,
          'total'     => $query->max_num_pages,
          'prev_text' => '‹',
          'next_text' => '›',
      ) );
      ?>
    </div>
  </main>

  <!-- Sidebar -->
  <aside class="lg-sidebar">

    <!-- 人気記事 -->
    <div class="widget">
      <div class="widget-title">人気記事</div>
      <?php
      $rank = 1;
      if ( $popular_query->have_posts() ) :
          while ( $popular_query->have_posts() ) :
              $popular_query->the_post();
              $rank_class = $rank === 1 ? '' : ( $rank === 2 ? ' rank-2' : ( $rank === 3 ? ' rank-3' : ' lg-rank-other' ) );
              ?>
              <a href="<?php the_permalink(); ?>" class="lg-popular-item">
                <span class="lg-rank<?php echo esc_attr( $rank_class ); ?>"><?php echo esc_html( $rank ); ?></span>
                <span class="lg-popular-title"><?php the_title(); ?></span>
              </a>
              <?php
              $rank++;
          endwhile;
          wp_reset_postdata();
      endif;
      ?>
    </div>

    <!-- カテゴリ -->
    <div class="widget">
      <div class="widget-title">カテゴリ</div>
      <?php foreach ( $categories as $cat ) : ?>
        <a href="<?php echo esc_url( get_category_link( $cat->term_id ) ); ?>" class="lg-cat-item">
          <span><?php echo esc_html( $cat->name ); ?></span>
          <span class="lg-cat-count"><?php echo esc_html( $cat->count ); ?></span>
        </a>
      <?php endforeach; ?>
    </div>

  </aside>
</div>

<?php get_footer();
