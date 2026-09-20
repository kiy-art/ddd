"""Shared analysis + AI-generation step, used by both the daily batch script
(scripts/update_prices.py) and the admin "run update" API endpoint so the
two never drift apart."""

import datetime

from sqlalchemy.orm import Session

from app import ai, analysis, crud, models


def sync_product_analysis(db: Session, product: models.Product) -> bool:
    """Recompute stats/buy_score from price history, refresh buy_reason, and
    regenerate AI wording only if the underlying facts changed (cost control).

    Returns True if AI content was (re)generated.
    """
    if product.current_price is None:
        return False

    history = crud.get_price_history(db, product.id)
    pairs = [(h.price, h.recorded_at) for h in history]
    result = analysis.analyze_prices(product.current_price, pairs)

    product.average_price = result.average_price
    product.lowest_price = result.lowest_price
    product.price_change_percent = result.price_change_percent
    product.buy_score = result.buy_score
    product.buy_reason = analysis.rule_based_reason(result)

    new_hash = ai.content_hash(product.name, product.current_price, product.buy_score, product.average_price)
    if not ai.should_regenerate(product, new_hash):
        db.commit()
        return False

    content, error = ai.generate_ai_content_safe(product.name, product.brand, result)
    if error:
        crud.create_error_log(db, source="ai_generation", message=error, product_id=product.id)

    product.ai_title = content.title
    product.ai_summary = content.summary
    product.ai_caution = content.caution
    product.ai_generated_at = datetime.datetime.utcnow()
    product.ai_content_hash = new_hash
    db.commit()
    db.refresh(product)
    return True
