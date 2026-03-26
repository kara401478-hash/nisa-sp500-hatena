"""
🤖 AI執筆エンジン（Groq版）
"""
import json
import re
import logging
import time
import requests
from typing import Dict, Optional

logger = logging.getLogger(__name__)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

PERSONA = """
あなたは「TAKA」という30代の会社員投資家ブロガーです。

【プロフィール】
- 30代会社員。副業ブログで毎月の更新料・生活費の足しを稼ごうと奮闘中
- かつて消費者金融で痛い目にあった経験あり
- 銀行へ借り換えで金利を大幅圧縮し、その差額をS&P500インデックスファンドへ積み立て中
- 新NISAを活用した長期積立を実践中

【新NISAの正確な情報】
- 2024年1月から開始した新しい制度
- つみたて投資枠：年間120万円まで非課税
- 成長投資枠：年間240万円まで非課税
- 合計：年間360万円、生涯1800万円まで非課税
- 非課税期間：無期限
- 年齢：18歳以上なら上限なし
- 旧NISAとは別制度。「2014年」「年間20万円」「10年限定」は間違いなので絶対に書かない

【投資商品の正確な情報】
- eMAXIS Slim米国株式(S&P500)の信託報酬：年0.09372%以内（業界最低水準）
- 100万円預けても年間コストは1000円以下
- S&P500はApple・Microsoft・Amazon・NVIDIAなど世界的優良企業500社で構成

【執筆スタイル】
- 「金利や手数料を甘く見るな。その分を積み立てろ」と実体験ベースで熱く語る
- 難しい金融用語は必ず平易な言葉で補足する
- 投資初心者でも行動できる「次のステップ」を必ず示す
- 必ず「投資は自己責任」の一言を含める
- 語尾は「〜ですよ」「〜してみてください」など親しみやすいトーン
"""


class AIWriter:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate_post(self, article: Dict) -> Optional[Dict]:
        time.sleep(3)
        if not self.api_key:
            return self._mock(article)

        title = article.get('title', '')
        summary = article.get('summary', '') or ''
        source = article.get('source', '')
        category = article.get('category', '')

        # summaryがある場合とない場合でプロンプトを切り替え
        if len(summary) > 50:
            news_section = (
                f"【今日のニュース】\n"
                f"タイトル：{title}\n"
                f"情報源：{source}（カテゴリ：{category}）\n"
                f"内容：{summary}\n\n"
                f"このニュースの内容を記事の軸にしてください。\n"
                f"上記の「内容」に書かれている事実・数字・出来事を必ず本文で具体的に触れること。\n"
                f"「詳細は元記事をご確認ください」は絶対に書かないこと。"
            )
        else:
            news_section = (
                f"【今日のニュース】\n"
                f"タイトル：{title}\n"
                f"情報源：{source}（カテゴリ：{category}）\n\n"
                f"このニュースのタイトルをテーマに、TAKAの視点で記事を書いてください。\n"
                f"「詳細は元記事をご確認ください」は絶対に書かないこと。"
            )

        prompt = (
            f"{news_section}\n\n"
            "【記事の構成（必ず守ること）】\n"
            "1. 冒頭：今日のニュースについてTAKAの一言コメント（共感・驚き・気づきなど）\n"
            "2. h2：今日のニュースのポイントをTAKAの言葉で解説（ニュースの内容を自分の言葉で説明する）\n"
            "3. h2：このニュースが積立投資家にとって何を意味するか（TAKAの視点・体験談を交えて）\n"
            "4. h2：今日から使える具体的なアクション（曖昧なアドバイスNG。「〇〇証券でeMAXIS Slimを検索する」レベルの具体性）\n"
            "5. 末尾：投資は自己責任の一言\n\n"
            "【絶対禁止】\n"
            "- 「詳細は元記事をご確認ください」→ 絶対禁止。自分の言葉で書くこと\n"
            "- 「公式ページをチェックする」「調べてみる」などの曖昧なアクション→ 禁止\n"
            "- 毎回同じ新NISA制度説明の繰り返し→ 必要な場合のみ1〜2行で済ませる\n"
            "- 根拠のない計算・利回り予測（「年率〇%で〇年後に〇万円」など）→ 禁止\n\n"
            "【必須ルール】\n"
            "- 800〜1200字\n"
            "- HTMLタグ使用(h2,p,ul,li)\n"
            "- SEOキーワード：新NISA、S&P500、積立投資\n\n"
            "JSONのみ返してください:\n"
            '{"title":"記事タイトル","content":"HTML本文","excerpt":"120字以内の記事説明","tags":["タグ1","タグ2"]}'
        )

        try:
            resp = requests.post(
                GROQ_API_URL,
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": PERSONA},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"},
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30
            )
            logger.info(f"🔗 Groq status: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            raw = data["choices"][0]["message"]["content"].strip()
            raw = re.sub(r"```json\s*", "", raw)
            raw = re.sub(r"```\s*", "", raw).strip()
            post = json.loads(raw)
            post["content"] += (
                "<hr><p style='font-size:0.85em;color:#666;'>"
                f"📰 参考: <a href='{article.get('link','')}' target='_blank' rel='nofollow'>{article.get('source','')}</a> | "
                "⚠️ 投資は自己責任でお願いします。</p>"
            )
            post["source_url"] = article.get("link", "")
            post["category"] = article.get("category", "")
            logger.info(f"✅ 執筆完了: {post['title']}")
            return post
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Groq APIエラー {e.response.status_code}: {e.response.text[:300]}")
        except Exception as e:
            logger.error(f"❌ エラー: {e}")
        return None

    def _mock(self, article: Dict) -> Dict:
        return {
            "title": f"【TAKA解説】{article.get('title','')[:35]}",
            "content": f"<h2>今日のニュース</h2><p>{article.get('title','')}</p><p>⚠️ 投資は自己責任です。</p>",
            "excerpt": article.get('title','')[:60],
            "tags": ["新NISA","S&P500"],
            "source_url": article.get("link",""),
            "category": article.get("category",""),
        }
