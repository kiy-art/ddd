"""AI-generated wording for buy-time listings.

The AI is only ever given already-computed, real numbers (current price,
30-day average, highest price, buy_score) and is instructed never to invent
prices or facts. If no API key is configured, or the call fails, we fall
back to a deterministic rule-based sentence so the pipeline still works
end to end without an AI dependency.
"""

import dataclasses
import hashlib
import json

from app import analysis
from app.config import get_settings

SYSTEM_PROMPT = """あなたはゴルフ用品の価格情報サイトのライター兼ファクトチェッカーです。
与えられた数値・判定結果のみを根拠に、日本語で短い紹介文を作成してください。

厳守事項:
- 与えられていない価格・割引率・在庫状況などを絶対に創作しない。
- 数値は与えられた値をそのまま使い、言い換えで誤解を招く表現をしない。
- 誇大広告・断定的な将来予測（「必ず値上がりする」等）をしない。
- 出力は必ず次のJSON形式のみ: {"title": "...", "summary": "...", "caution": "..."}
- captionには「価格は変動する可能性があります」という主旨の注意書きを必ず含める。
"""


@dataclasses.dataclass
class AiContent:
    title: str
    summary: str
    caution: str
    source: str  # "ai" or "rule_based"


def content_hash(product_name: str, current_price: int, buy_score: str, average_price: int | None) -> str:
    raw = f"{product_name}|{current_price}|{buy_score}|{average_price}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def should_regenerate(product, new_hash: str) -> bool:
    """Cost control: only call the AI when the underlying facts changed."""
    return product.ai_content_hash != new_hash


def _rule_based_content(product_name: str, result: analysis.AnalysisResult) -> AiContent:
    reason = analysis.rule_based_reason(result)
    if result.buy_score == "insufficient_data":
        title = f"{product_name} の価格データを収集中"
    else:
        title = f"{product_name} {reason}".strip()
    return AiContent(
        title=title[:120],
        summary=reason,
        caution="価格は変動する可能性があります。購入前に最新価格をご確認ください。",
        source="rule_based",
    )


def generate_ai_content(product_name: str, brand: str, result: analysis.AnalysisResult) -> AiContent:
    """Raises on AI failure so the caller can log it to ErrorLog and decide
    whether to fall back to _rule_based_content."""
    settings = get_settings()

    if not settings.anthropic_api_key or result.buy_score == "insufficient_data":
        return _rule_based_content(product_name, result)

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    facts = {
        "product_name": product_name,
        "brand": brand,
        "current_price_jpy": result.current_price,
        "average_price_30d_jpy": result.average_price,
        "highest_price_30d_jpy": result.highest_price_30d,
        "lowest_price_jpy": result.lowest_price,
        "price_change_percent_vs_30d_avg": result.price_change_percent,
        "buy_score": result.buy_score,
    }
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "以下の事実だけを根拠にJSONを生成してください:\n"
                    + json.dumps(facts, ensure_ascii=False)
                ),
            }
        ],
    )
    text = "".join(block.text for block in message.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
    data = json.loads(text)
    return AiContent(
        title=str(data["title"])[:120],
        summary=str(data["summary"]),
        caution=str(data["caution"]),
        source="ai",
    )


def generate_ai_content_safe(product_name: str, brand: str, result: analysis.AnalysisResult) -> tuple[AiContent, str | None]:
    """Never raises. Returns (content, error_message). error_message is set
    when the AI call failed and we fell back to rule-based wording."""
    try:
        return generate_ai_content(product_name, brand, result), None
    except Exception as exc:  # noqa: BLE001 - AI provider failures are varied
        return _rule_based_content(product_name, result), str(exc)
