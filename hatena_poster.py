"""
📤 はてなブログ投稿モジュール
AtomPub API使用（APIキー認証・トークン期限切れなし）
"""
import json
import logging
import os
import urllib.request
import urllib.error
from base64 import b64encode
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class HatenaPoster:
    def __init__(self):
        self.hatena_id = os.environ.get("HATENA_ID", "")
        self.api_key = os.environ.get("HATENA_API_KEY", "")
        self.blog_domain = os.environ.get("HATENA_BLOG_DOMAIN", "")
        self.endpoint = f"https://blog.hatena.ne.jp/{self.hatena_id}/{self.blog_domain}/atom/entry"

        # Basic認証（はてなID:APIキー をBase64エンコード）
        credentials = f"{self.hatena_id}:{self.api_key}"
        self.auth_header = "Basic " + b64encode(credentials.encode()).decode()

    def post_article(self, post_data: Dict) -> Optional[Dict]:
        title = post_data.get("title", "")
        content = post_data.get("content", "")
        tags = post_data.get("tags", [])[:10]

        # はてなブログAtomPub形式のXML
        categories = "".join(
            f'<category term="{tag}" />' for tag in tags
        )

        body = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>{self._escape(title)}</title>
  <content type="text/html"><![CDATA[{content}]]></content>
  {categories}
  <app:control>
    <app:draft>no</app:draft>
  </app:control>
</entry>"""

        payload = body.encode("utf-8")

        req = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Content-Type": "application/atom+xml; charset=utf-8",
                "Authorization": self.auth_header,
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result_xml = resp.read().decode("utf-8")
                # URLを抽出
                url = self._extract_url(result_xml)
                logger.info(f"✅ はてなブログ投稿成功: {url}")
                return {"url": url, "title": title}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.error(f"❌ はてなAPI エラー {e.code}: {error_body[:300]}")
        except Exception as e:
            logger.error(f"❌ 投稿エラー: {e}")

        return None

    def _escape(self, text: str) -> str:
        """XML特殊文字をエスケープ"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    def _extract_url(self, xml: str) -> str:
        """レスポンスXMLからURLを抽出"""
        import re
        match = re.search(r'<link[^>]+rel="alternate"[^>]+href="([^"]+)"', xml)
        if match:
            return match.group(1)
        return ""
