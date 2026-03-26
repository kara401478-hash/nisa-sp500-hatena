"""
📤 はてなブログ投稿モジュール
AtomPub API使用（APIキー認証・トークン期限切れなし）
"""
import logging
import os
import re
import urllib.request
import urllib.error
from base64 import b64encode
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class HatenaPoster:
    def __init__(self):
        self.hatena_id = os.environ.get("HATENA_ID", "")
        self.api_key = os.environ.get("HATENA_API_KEY", "")
        self.blog_domain = os.environ.get("HATENA_BLOG_DOMAIN", "")
        self.endpoint = f"https://blog.hatena.ne.jp/{self.hatena_id}/{self.blog_domain}/atom/entry"

        credentials = f"{self.hatena_id}:{self.api_key}"
        self.auth_header = "Basic " + b64encode(credentials.encode()).decode()

    def post_article(self, post_data: Dict) -> Optional[Dict]:
        title = post_data.get("title", "")
        content = post_data.get("content", "")
        tags = post_data.get("tags", [])[:10]

        categories = "".join(
            f'<category term="{self._escape_attr(tag)}" />' for tag in tags
        )

        # CDATAセクション内の]]>を安全に処理
        safe_content = content.replace("]]>", "]]]]><![CDATA[>")

        body = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<entry xmlns="http://www.w3.org/2005/Atom"\n'
            '       xmlns:app="http://www.w3.org/2007/app">\n'
            f'  <title>{self._escape_xml(title)}</title>\n'
            f'  <content type="text/html"><![CDATA[{safe_content}]]></content>\n'
            f'  {categories}\n'
            '  <app:control>\n'
            '    <app:draft>no</app:draft>\n'
            '  </app:control>\n'
            '</entry>'
        )

        # デバッグ：送信するXMLの最初の500文字をログ出力
        logger.info(f"📤 送信XML（先頭500文字）:\n{body[:500]}")

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
                url = self._extract_url(result_xml)
                logger.info(f"✅ はてなブログ投稿成功: {url}")
                return {"url": url, "title": title}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.error(f"❌ はてなAPI エラー {e.code}: {error_body[:500]}")
        except Exception as e:
            logger.error(f"❌ 投稿エラー: {e}")

        return None

    def _escape_xml(self, text: str) -> str:
        """XMLタグ内テキストの特殊文字をエスケープ"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))

    def _escape_attr(self, text: str) -> str:
        """XML属性値の特殊文字をエスケープ"""
        return (text
                .replace("&", "&amp;")
                .replace('"', "&quot;")
                .replace("<", "&lt;"))

    def _extract_url(self, xml: str) -> str:
        """レスポンスXMLからURLを抽出"""
        match = re.search(r'<link[^>]+rel="alternate"[^>]+href="([^"]+)"', xml)
        if match:
            return match.group(1)
        return ""
