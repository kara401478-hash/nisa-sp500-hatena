"""
📡 ニュースフェッチャー
Google ニュース RSS から新NISA・S&P500関連の最新記事を取得する
"""

import feedparser
import hashlib
import json
import os
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    {
        "name": "Googleニュース: 新NISA",
        "url": "https://news.google.com/rss/search?q=%E6%96%B0NISA+%E6%8A%95%E8%B3%87&hl=ja&gl=JP&ceid=JP:ja",
        "category": "新NISA",
        "source": "Googleニュース"
    },
    {
        "name": "Googleニュース: S&P500",
        "url": "https://news.google.com/rss/search?q=SP500+%E6%8A%95%E8%B3%87+%E7%A9%8D%E7%AB%8B&hl=ja&gl=JP&ceid=JP:ja",
        "category": "S&P500",
        "source": "Googleニュース"
    },
    {
        "name": "Googleニュース: 証券手数料",
        "url": "https://news.google.com/rss/search?q=%E8%A8%BC%E5%88%B8+%E6%89%8B%E6%95%B0%E6%96%99+%E7%84%A1%E6%96%99&hl=ja&gl=JP&ceid=JP:ja",
        "category": "手数料",
        "source": "Googleニュース"
    },
    {
        "name": "Googleニュース: SBI証券",
        "url": "https://news.google.com/rss/search?q=SBI%E8%A8%BC%E5%88%B8+%E6%96%B0NISA&hl=ja&gl=JP&ceid=JP:ja",
        "category": "証券会社",
        "source": "SBI証券"
    },
    {
        "name": "Googleニュース: 積立投資",
        "url": "https://news.google.com/rss/search?q=%E7%A9%8D%E7%AB%8B%E6%8A%95%E8%B3%87+%E3%82%A4%E3%83%B3%E3%83%87%E3%83%83%E3%82%AF%E3%82%B9&hl=ja&gl=JP&ceid=JP:ja",
        "category": "積立投資",
        "source": "Googleニュース"
    },
    {
        "name": "Googleニュース: eMAXIS Slim",
        "url": "https://news.google.com/rss/search?q=eMAXIS+Slim+%E3%82%A4%E3%83%B3%E3%83%87%E3%83%83%E3%82%AF%E3%82%B9&hl=ja&gl=JP&ceid=JP:ja",
        "category": "インデックス投資",
        "source": "Googleニュース"
    },
    {
        "name": "Yahoo!ニュース: ビジネス",
        "url": "https://news.yahoo.co.jp/rss/topics/business.xml",
        "category": "経済・ビジネス",
        "source": "Yahoo!ニュース"
    },
    {
        "name": "Googleニュース経由: Yahoo!ファイナンス 新NISA",
        "url": "https://news.google.com/rss/search?q=site:finance.yahoo.co.jp+%E6%96%B0NISA&hl=ja&gl=JP&ceid=JP:ja",
        "category": "新NISA",
        "source": "Yahoo!ファイナンス"
    },
    {
        "name": "日経ビジネス: 最新記事",
        "url": "https://business.nikkei.com/rss/sns/nb.rdf",
        "category": "経済ニュース",
        "source": "日経ビジネス"
    },
]

# 投資・金融関連キーワード
INVESTMENT_KEYWORDS = [
    "NISA", "nisa", "投資", "積立", "株", "証券", "ファンド",
    "インデックス", "S&P", "資産", "金利", "手数料", "配当",
    "ETF", "iDeCo", "オルカン", "eMAXIS", "運用", "節税",
    "銘柄", "相場", "日経平均", "為替", "円安", "円高",
    "利回り", "複利", "分散投資", "ポートフォリオ"
]

SEEN_CACHE_FILE = "seen_articles.json"


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _build_summary(entry) -> str:
    summary = entry.get("summary", "")
    if summary:
        clean = _strip_html(summary)
        if len(clean) > 30:
            return clean[:800]
    content_list = entry.get("content", [])
    if content_list:
        for content in content_list:
            value = content.get("value", "")
            if value:
                clean = _strip_html(value)
                if len(clean) > 30:
                    return clean[:800]
    title = _strip_html(entry.get("title", ""))
    return title[:800]


def _is_investment_related(article: Dict) -> bool:
    """投資・金融関連の記事かどうかをチェック"""
    text = article.get("title", "") + " " + article.get("summary", "")
    return any(kw in text for kw in INVESTMENT_KEYWORDS)


class NewsFetcher:
    def __init__(self, hours_lookback: int = 24):
        self.cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)
        self.seen_ids = self._load_seen()

    def _load_seen(self) -> set:
        if os.path.exists(SEEN_CACHE_FILE):
            try:
                with open(SEEN_CACHE_FILE) as f:
                    return set(json.load(f))
            except Exception:
                pass
        return set()

    def _save_seen(self):
        with open(SEEN_CACHE_FILE, "w") as f:
            json.dump(list(self.seen_ids)[-1000:], f)

    def _article_id(self, entry) -> str:
        key = entry.get("link", "") + entry.get("title", "")
        return hashlib.md5(key.encode()).hexdigest()

    def _parse(self, entry, source_info: dict) -> Optional[Dict]:
        try:
            title = _strip_html(entry.get("title", "")).strip()
            link  = entry.get("link", "").strip()
            summary = _build_summary(entry)

            if not title:
                return None

            published = None
            for attr in ("published_parsed", "updated_parsed"):
                val = getattr(entry, attr, None)
                if val:
                    published = datetime(*val[:6], tzinfo=timezone.utc)
                    break

            return {
                "title": title,
                "link": link,
                "summary": summary,
                "published": published.isoformat() if published else None,
                "published_dt": published,
                "source": source_info["source"],
                "category": source_info["category"],
                "article_id": self._article_id(entry),
            }
        except Exception:
            return None

    def fetch_feed(self, feed_info: dict, max_per_feed: int = 3) -> List[Dict]:
        results = []
        logger.info(f"  📥 {feed_info['name']} 取得中...")
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries:
                if len(results) >= max_per_feed:
                    break
                article = self._parse(entry, feed_info)
                if not article:
                    continue
                if article["published_dt"] and article["published_dt"] < self.cutoff:
                    continue
                if article["article_id"] in self.seen_ids:
                    continue
                results.append(article)
                self.seen_ids.add(article["article_id"])
            logger.info(f"  ✅ {len(results)} 件")
        except Exception as e:
            logger.error(f"  ❌ 取得失敗: {e}")
        return results

    def fetch_all(self) -> List[Dict]:
        all_articles = []
        for feed in RSS_FEEDS:
            all_articles.extend(self.fetch_feed(feed))

        # 投資・金融関連のみに絞る
        before = len(all_articles)
        all_articles = [a for a in all_articles if _is_investment_related(a)]
        logger.info(f"🔍 キーワードフィルター: {before}件 → {len(all_articles)}件")

        all_articles.sort(
            key=lambda a: a["published_dt"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )
        self._save_seen()
        return all_articles
