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

from app import analysis, marketing_playbook
from app.config import get_settings

# Shared with app/content_rewriter.py so routine copy and optimizer
# rewrites follow one professional playbook (STEP43).
SYSTEM_PROMPT = marketing_playbook.product_copy_system_prompt(None)


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
    title = f"{product_name}の価格推移・買い時情報"
    return AiContent(
        title=title[:120],
        summary=reason,
        caution="価格は変動する可能性があります。購入前に最新価格をご確認ください。",
        source="rule_based",
    )


def would_use_claude(result: analysis.AnalysisResult) -> bool:
    """The one place deciding whether product copy for this verdict costs a
    Claude call - also used by pipeline.sync_product_analysis so keeping an
    optimizer rewrite's style alive never adds calls beyond this set."""
    settings = get_settings()
    return bool(
        settings.anthropic_api_key
        and result.buy_score != "insufficient_data"
        and result.data_basis == "price_history"
    )


def _is_at_recorded_lowest(result: analysis.AnalysisResult) -> bool:
    return (
        result.lowest_price is not None
        and result.current_price <= result.lowest_price
        and result.history_span_days >= 7
    )


def generate_ai_content(product_name: str, brand: str, result: analysis.AnalysisResult) -> AiContent:
    """Raises on AI failure so the caller can log it to ErrorLog and decide
    whether to fall back to _rule_based_content."""
    settings = get_settings()

    # STEP21: an "msrp_estimate"-basis verdict isn't backed by a real price
    # trend (see analysis.AnalysisResult.data_basis) - skip the live API
    # call for it too, same as insufficient_data, so introducing this
    # fallback tier doesn't silently start spending on more Claude calls
    # for a wider set of products than before (docs/ai_company_guidelines.md
    # absolute rule 1: no cost-incurring change without explicit go-ahead).
    # The deterministic rule_based_reason() wording already says plainly
    # that it's a provisional, MSRP-based call.
    if not would_use_claude(result):
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
        "is_at_recorded_lowest_price": _is_at_recorded_lowest(result),
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
    content = AiContent(
        title=str(data["title"])[:120],
        summary=str(data["summary"]),
        caution=str(data["caution"]),
        source="ai",
    )
    # Raises ContentPolicyViolation -> generate_ai_content_safe falls back
    # to the rule-based wording rather than publishing a non-compliant or
    # number-inventing sentence.
    marketing_playbook.validate_copy(
        [content.title, content.summary, content.caution],
        allowed_yen={
            v
            for v in (result.current_price, result.average_price, result.highest_price_30d, result.lowest_price)
            if v
        },
        allowed_percents={result.price_change_percent} if result.price_change_percent is not None else set(),
        allow_lowest_price_claim=_is_at_recorded_lowest(result),
    )
    return content


def generate_ai_content_safe(product_name: str, brand: str, result: analysis.AnalysisResult) -> tuple[AiContent, str | None]:
    """Never raises. Returns (content, error_message). error_message is set
    when the AI call failed and we fell back to rule-based wording."""
    try:
        return generate_ai_content(product_name, brand, result), None
    except Exception as exc:  # noqa: BLE001 - AI provider failures are varied
        return _rule_based_content(product_name, result), str(exc)
