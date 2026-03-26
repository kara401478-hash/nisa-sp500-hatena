"""
🔥 TAKA｜新NISA実録 - 自動投稿システム（はてなブログ版）
Groq AI + はてなブログ AtomPub API
毎日AM8:00に自動実行
"""

import os
import sys
import time
import logging
from datetime import datetime

from fetcher import NewsFetcher
from ai_writer import AIWriter
from hatena_poster import HatenaPoster

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    logger.info("🔥 TAKA｜新NISA実録 自動投稿システム（はてなブログ版）起動！")
    logger.info(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    config = {
        "groq_api_key":   os.environ.get("GROQ_API_KEY", ""),
        "hatena_id":      os.environ.get("HATENA_ID", ""),
        "hatena_api_key": os.environ.get("HATENA_API_KEY", ""),
        "blog_domain":    os.environ.get("HATENA_BLOG_DOMAIN", ""),
        "max_articles":   int(os.environ.get("MAX_ARTICLES", "3")),
        "dry_run":        os.environ.get("DRY_RUN", "false").lower() == "true",
    }

    if not config["dry_run"]:
        missing = [k for k, v in config.items()
                   if not v and k not in ("dry_run", "max_articles")]
        if missing:
            logger.error(f"❌ 未設定の環境変数: {missing}")
            sys.exit(1)

    logger.info("📡 ニュース取得中...")
    fetcher = NewsFetcher()
    articles = fetcher.fetch_all()
    logger.info(f"✅ {len(articles)} 件の新着記事を取得")

    if not articles:
        logger.info("📭 新着記事なし。本日はスキップ。")
        return

    articles = articles[:config["max_articles"]]

    writer = AIWriter(api_key=config["groq_api_key"])
    poster = HatenaPoster()

    success = 0
    for i, article in enumerate(articles, 1):
        logger.info(f"\n--- 記事 {i}/{len(articles)}: {article['title'][:50]} ---")

        post = writer.generate_post(article)
        if not post:
            logger.warning("⚠️ AI執筆失敗。スキップ。")
            continue

        if config["dry_run"]:
            logger.info(f"🧪 DRY RUN: {post['title']}")
            logger.info(post["content"][:300])
            success += 1
            continue

        result = poster.post_article(post)
        if result:
            logger.info(f"✅ 投稿成功！ → {result.get('url', '')}")
            success += 1
        else:
            logger.error("❌ 投稿失敗")

        if i < len(articles):
            logger.info("⏳ 5秒待機中...")
            time.sleep(5)

    logger.info(f"\n🎯 完了！ {success}/{len(articles)} 件投稿成功")
    logger.info("💪 更新料、絶対奪還するぞ！")


if __name__ == "__main__":
    main()
