"""
🤖 AI執筆エンジン（Groq公式ライブラリ版）
TAKA｜新NISA実録 ペルソナで記事を自動生成する
"""

import json
import re
import logging
from groq import Groq
from typing import Dict, Optional

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"

PERSONA = """
あなたは「TAKA」という30代の会社員投資家ブロガーです。

【プロフィール】
- 30代会社員。副業ブログで毎月の更新料・生活費の足しを稼ごうと奮闘中
- かつて消費者金融で年利18%という猛毒ダメージを負った実体験あり
- 銀行へ借り換えで金利を大幅圧縮し、その差額をS&P500インデックスファンドへ積み立て中
- 新NISAを活用した長期積立を実践中

【執筆スタイル】
- 難しい金融用語は必ず平易な言葉で補足する
- 数字・比較・実例を多用して「で、結局いくらトクするの？」を明確にする
- 必ず「投資は自己責任」の一言を含める

【厳守ルール】
- TAKAの消費者金融18%の実体験は、自然に関連する場合のみ使う。無理に絡めるな
- 毎回同じ文言を繰り返すな（特に「消費者金融で痛い目」「銀行へ借り換え」の多用禁止）
- アクションは必ずそのニュースに直結した内容にする
- 「eMAXIS Slimを検索してみよう」「新NISAを検討してみよう」などの汎用アクションは禁止
"""


class AIWriter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = Groq(api_key=api_key) if api_key else None

    def _build_prompt(self, article: Dict) -> str:
        return (
            "以下の金融ニュースをもとに、ブログ記事を日本語で作成してください。\n\n"
            "【元記事】\n"
            f"タイトル: {article.get('title', '')}\n"
            f"情報源: {article.get('source', '')}\n"
            f"カテゴリ: {article.get('category', '')}\n"
            f"概要: {article.get('summary', '') or '概要なし'}\n\n"
            "【構成】\n"
            "1. 読者を引き込むイントロ（1〜2文）\n"
            "2. このニュースの重要ポイントを3点（箇条書き・具体的な数字や事実を含める）\n"
            "3. TAKAの解説（400字以上）\n"
            "   - このニュースがS&P500・新NISA・積立投資家にとって何を意味するか論理的に説明\n"
            "   - 例：データセンター増設→NVIDIA・Amazon株上昇→S&P500にプラス→インデックス投資家に恩恵\n"
            "   - 例：証券会社再編→手数料競争激化→投資家にとってコスト削減チャンス\n"
            "   - TAKAの実体験は自然に関連する場合のみ使う（無理に絡めない）\n"
            "4. 今日できる具体的なアクション（重要）\n"
            "   - このニュースに直接関連したアクションのみ書く\n"
            "   - 「eMAXIS Slimを検索」「新NISAを検討」などの汎用アクションは禁止\n"
            "   - 例：SBI証券への移管を検討中なら「移管手続きの期間と注意点を公式サイトで確認」\n"
            "   - 例：データセンター関連なら「自分のS&P500保有割合でNVIDIA・Amazon比率を確認」\n"
            "5. 締めのセリフ（熱く・前向きに）\n\n"
            "【ルール】\n"
            "- 文字数: 1000字以上\n"
            "- SEOキーワードを自然に含める: 新NISA、S&P500、積立投資、手数料\n"
            "- HTMLタグを使用: h2, p, ul, li, strong\n"
            "- 投資は自己責任の免責事項を含める\n"
            "- 毎回同じ文言を繰り返さない\n\n"
            "必ず以下のJSON形式のみで返してください:\n"
            '{"title": "記事タイトル", "content": "HTML本文", "excerpt": "120字以内の抜粋", "tags": ["タグ1", "タグ2", "タグ3"]}'
        )

    def generate_post(self, article: Dict) -> Optional[Dict]:
        if not self.client:
            logger.warning("Groq APIキー未設定。モックデータを返します。")
            return self._mock(article)

        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": PERSONA},
                    {"role": "user", "content": self._build_prompt(article)}
                ],
                temperature=0.8,
                max_tokens=2500,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"```json\s*", "", raw)
            raw = re.sub(r"```\s*", "", raw).strip()

            post = json.loads(raw)

            if "title" not in post or "content" not in post:
                logger.error(f"❌ 必須フィールドなし: {list(post.keys())}")
                return None

            post["content"] += (
                "<hr><p style='font-size:0.85em;color:#666;'>"
                f"📰 参考: <a href='{article.get('link', '')}' target='_blank' rel='nofollow'>{article.get('source', '')}</a> | "
                "⚠️ 本記事は情報提供目的です。投資は自己責任でお願いします。</p>"
            )
            post["source_url"] = article.get("link", "")
            post["category"] = article.get("category", "")
            logger.info(f"✅ Groq執筆完了: {post['title']}")
            return post

        except Exception as e:
            import traceback
            logger.error(f"❌ Groqエラー: {e}")
            logger.error(traceback.format_exc())
            return None

    def _mock(self, article: Dict) -> Dict:
        return {
            "title": f"【TAKA解説】{article.get('title', '')[:35]}を会社員目線で読む",
            "content": (
                "<h2>3行でわかる今日のニュース</h2>"
                f"<ul><li>📌 {article.get('title', '')}</li></ul>"
                "<h2>TAKAの一言</h2>"
                "<p>新NISAとS&P500で積み立てしてる人は要チェック。</p>"
                "<hr><p style='font-size:0.85em;color:#666;'>⚠️ 投資は自己責任です。</p>"
            ),
            "excerpt": f"{article.get('title', '')[:60]}について、会社員投資家TAKAが解説。",
            "tags": ["新NISA", "S&P500", "積立投資", "手数料"],
            "source_url": article.get("link", ""),
            "category": article.get("category", ""),
        }
