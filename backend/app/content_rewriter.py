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

from app import marketing_playbook, models
from app.config import get_settings

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


def _product_facts(
    product: models.Product, reason: str, goal: str | None, search_queries: list[dict] | None
) -> dict:
    discount_percent = None
    if product.msrp and product.current_price is not None:
        discount_percent = round((product.current_price - product.msrp) / product.msrp * 100, 1)
    return {
        "product_name": product.name,
        "brand": product.brand,
        "current_price_jpy": product.current_price,
        "average_price_jpy": product.average_price,
        "lowest_recorded_price_jpy": product.lowest_price,
        "msrp_jpy": product.msrp,
        "discount_percent_vs_msrp": discount_percent,
        "price_change_percent_vs_30d_avg": product.price_change_percent,
        "is_at_recorded_lowest_price": _is_at_recorded_lowest(product),
        "price_history_days": product.history_span_days,
        "buy_score": product.buy_score,
        "current_title": product.ai_title,
        "current_summary": product.ai_summary,
        "optimization_goal": goal,
        "why_being_rewritten": reason,
        "real_search_queries": search_queries or [],
    }


def _is_at_recorded_lowest(product: models.Product) -> bool:
    # Only meaningful with some real history behind it - a product with one
    # price record is trivially "at its lowest", which isn't a claim worth
    # (or safe) making.
    return (
        product.current_price is not None
        and product.lowest_price is not None
        and product.current_price <= product.lowest_price
        and (product.history_span_days or 0) >= 7
    )


def _call_claude(system: str, facts: dict, max_tokens: int) -> dict:
    settings = get_settings()
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        system=system,
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
    return json.loads(text)


def rewrite_product_copy(
    product: models.Product,
    reason: str,
    goal: str | None = None,
    search_queries: list[dict] | None = None,
) -> RewrittenProductCopy:
    """Raises (RuntimeError/anthropic errors/json errors/
    marketing_playbook.ContentPolicyViolation) on any failure - the caller
    must not apply a partial, guessed, or non-compliant result.

    `goal` picks which professional playbook section leads (see
    marketing_playbook.product_copy_system_prompt); `search_queries` are
    the real Search Console queries this page already appears for, so a
    search_ctr rewrite aligns the title with actual search intent instead
    of guessing at keywords."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    facts = _product_facts(product, reason, goal, search_queries)
    data = _call_claude(marketing_playbook.product_copy_system_prompt(goal), facts, max_tokens=600)
    rewritten = RewrittenProductCopy(
        title=str(data["title"])[:120],
        summary=str(data["summary"]),
        caution=str(data["caution"]),
    )
    marketing_playbook.validate_copy(
        [rewritten.title, rewritten.summary, rewritten.caution],
        allowed_yen={v for v in (product.current_price, product.average_price, product.lowest_price, product.msrp) if v},
        allowed_percents={v for v in (facts["discount_percent_vs_msrp"], product.price_change_percent) if v is not None},
        allow_lowest_price_claim=facts["is_at_recorded_lowest_price"],
    )
    return rewritten


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
    data = _call_claude(marketing_playbook.guide_system_prompt(), facts, max_tokens=900)
    sections = [
        GuideSectionDraft(heading=str(s["heading"]), paragraphs=[str(p) for p in s["paragraphs"]])
        for s in data["sections"]
    ]
    draft = GuideDraft(title=str(data["title"])[:255], description=str(data["description"]), sections=sections)
    marketing_playbook.validate_copy(
        [draft.title, draft.description] + [p for sec in draft.sections for p in [sec.heading, *sec.paragraphs]],
        allowed_yen={p.current_price for p in candidate_products if p.current_price},
        allowed_percents=set(),
    )
    return draft
