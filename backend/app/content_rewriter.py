"""Claude-based content generation for app/content_optimizer.py's
autonomous rewrites - the one part of the STEP42 optimization loop that
costs real money per call (see docs/ai_company_guidelines.md absolute
rule 1, explicitly approved by the president for this feature, capped at
a few actions/day by content_optimizer's daily action limit).

Both functions follow the same "AI is only ever given already-computed,
real numbers/names and is told never to invent facts" contract as
app/ai.py and app/x_post.py - the underperformance reason and the
candidate product list are the only grounding given, and both raise on
failure rather than silently falling back, so the caller (content_
optimizer.py) can log a failed action instead of quietly overwriting real
content with something unreviewed.
"""

import dataclasses
import json

from app import models
from app.config import get_settings

REWRITE_SYSTEM_PROMPT = """あなたはゴルフ用品の価格比較サイト「PAR.」のライター兼ファクトチェッカーです。
既存の紹介文が実データ（検索クリック率・ページ離脱率など）上で振るわない商品について、
同じ事実関係を保ったまま、より分かりやすく興味を引く文面に書き直してください。

厳守事項:
- 与えられていない価格・割引率・在庫状況・スペックなどを絶対に創作しない。
- 数値は与えられた値をそのまま使い、言い換えで誤解を招く表現をしない。
- 誇大広告・断定的な将来予測（「必ず値上がりする」等）をしない。
- 出力は必ず次のJSON形式のみ: {"title": "...", "summary": "...", "caution": "..."}
- titleはページタイトル・SNS共有見出しとして使う短い体言止めの見出し（20〜40文字程度、
  商品名を含む）にする。「〜です。」「〜ます。」のような文章にしない。
- summaryには、titleに入れなかった判定理由の詳細を1〜2文で書く。
- captionには「価格は変動する可能性があります」という主旨の注意書きを必ず含める。
"""

GUIDE_SYSTEM_PROMPT = """あなたはゴルフ用品の価格比較サイト「PAR.」のライターです。
実際に検索されているキーワードと、サイトに実在する商品リストだけを根拠に、
新しい比較ガイド記事の下書きを作成してください。

厳守事項:
- 与えられた商品リストに無い商品名・型番・価格・ブランドを絶対に創作しない。
- 統計や「〜%の人が」のような架空のデータを作らない。
- 誇大広告・断定的な将来予測をしない。
- 出力は必ず次のJSON形式のみ:
  {"title": "...", "description": "...", "sections": [{"heading": "...", "paragraphs": ["..."]}]}
- titleは検索されやすい具体的な文言にする（32文字程度まで）。
- descriptionは記事の要約（80文字程度まで）。
- sectionsは2〜3個、各paragraphsは1〜2文。
"""


@dataclasses.dataclass
class RewrittenProductCopy:
    title: str
    summary: str
    caution: str


@dataclasses.dataclass
class GuideSectionDraft:
    heading: str
    paragraphs: list[str]


@dataclasses.dataclass
class GuideDraft:
    title: str
    description: str
    sections: list[GuideSectionDraft]


def _product_facts(product: models.Product, reason: str) -> dict:
    discount_percent = None
    if product.msrp and product.current_price is not None:
        discount_percent = round((product.current_price - product.msrp) / product.msrp * 100, 1)
    return {
        "product_name": product.name,
        "brand": product.brand,
        "current_price_jpy": product.current_price,
        "average_price_jpy": product.average_price,
        "msrp_jpy": product.msrp,
        "discount_percent_vs_msrp": discount_percent,
        "price_change_percent_vs_30d_avg": product.price_change_percent,
        "buy_score": product.buy_score,
        "current_title": product.ai_title,
        "current_summary": product.ai_summary,
        "why_being_rewritten": reason,
    }


def rewrite_product_copy(product: models.Product, reason: str) -> RewrittenProductCopy:
    """Raises (RuntimeError/anthropic errors/json errors) on any failure -
    the caller must not apply a partial/guessed result."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    facts = _product_facts(product, reason)
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=500,
        system=REWRITE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": "以下の事実だけを根拠にJSONを生成してください:\n" + json.dumps(facts, ensure_ascii=False),
            }
        ],
    )
    text = "".join(block.text for block in message.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
    data = json.loads(text)
    return RewrittenProductCopy(
        title=str(data["title"])[:120],
        summary=str(data["summary"]),
        caution=str(data["caution"]),
    )


def draft_new_guide(query_text: str, candidate_products: list[models.Product]) -> GuideDraft:
    """Raises on any failure. `candidate_products` must be non-empty real,
    already-catalogued products - the only material Claude is allowed to
    reference, so a drafted guide can never mention a product that doesn't
    exist on the site."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    if not candidate_products:
        raise ValueError("draft_new_guide requires at least one real candidate product")

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    facts = {
        "search_query": query_text,
        "products": [
            {
                "name": p.name,
                "brand": p.brand,
                "category": p.category,
                "current_price_jpy": p.current_price,
                "buy_score": p.buy_score,
            }
            for p in candidate_products
        ],
    }
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=800,
        system=GUIDE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": "以下の事実だけを根拠にJSONを生成してください:\n" + json.dumps(facts, ensure_ascii=False),
            }
        ],
    )
    text = "".join(block.text for block in message.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
    data = json.loads(text)
    sections = [
        GuideSectionDraft(heading=str(s["heading"]), paragraphs=[str(p) for p in s["paragraphs"]])
        for s in data["sections"]
    ]
    return GuideDraft(title=str(data["title"])[:255], description=str(data["description"]), sections=sections)
