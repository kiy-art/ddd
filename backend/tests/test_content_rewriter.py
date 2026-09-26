import json
from unittest.mock import MagicMock

import pytest

from app import content_rewriter, models


def _make_product(**overrides):
    defaults = dict(
        id=1,
        name="G440 MAX ドライバー",
        brand="PING",
        category="driver",
        current_price=58000,
        average_price=62000,
        msrp=79200,
        price_change_percent=-6.5,
        buy_score="strong_buy",
        ai_title="旧タイトル",
        ai_summary="旧サマリー",
    )
    defaults.update(overrides)
    return models.Product(**defaults)


def _mock_anthropic_client(response_text: str):
    fake_block = MagicMock()
    fake_block.type = "text"
    fake_block.text = response_text
    fake_message = MagicMock()
    fake_message.content = [fake_block]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message
    return fake_client


def test_rewrite_product_copy_raises_when_not_configured(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            content_rewriter.rewrite_product_copy(_make_product(), "CTRが平均より低い")
    finally:
        get_settings.cache_clear()


def test_rewrite_product_copy_returns_parsed_json_grounded_in_real_facts(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()

    response = json.dumps(
        {
            "title": "PING G440 MAX ドライバー 価格推移・買い時情報",
            "summary": "定価より26.8%安い水準です。",
            "caution": "価格は変動する可能性があります。",
        },
        ensure_ascii=False,
    )
    fake_client = _mock_anthropic_client(response)

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: fake_client)

    try:
        result = content_rewriter.rewrite_product_copy(_make_product(), "CTRが平均より低い")
        assert result.title == "PING G440 MAX ドライバー 価格推移・買い時情報"
        assert "26.8%" in result.summary
        assert "変動する可能性" in result.caution

        call_kwargs = fake_client.messages.create.call_args.kwargs
        sent_facts = json.loads(call_kwargs["messages"][0]["content"].split("\n", 1)[1])
        assert sent_facts["current_price_jpy"] == 58000
        assert sent_facts["why_being_rewritten"] == "CTRが平均より低い"
    finally:
        get_settings.cache_clear()


def test_draft_new_guide_requires_at_least_one_real_product(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError):
            content_rewriter.draft_new_guide("パター 型落ち", [])
    finally:
        get_settings.cache_clear()


def test_draft_new_guide_returns_parsed_json_referencing_only_given_products(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()

    response = json.dumps(
        {
            "title": "型落ちパター特選：今買えるお得な型番まとめ",
            "description": "型落ちパターの中から実際に価格が下がっているモデルをまとめました。",
            "sections": [
                {"heading": "このページの見方", "paragraphs": ["実際の価格データに基づいた一覧です。"]},
            ],
        },
        ensure_ascii=False,
    )
    fake_client = _mock_anthropic_client(response)

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: fake_client)

    product = _make_product(category="putter", name="Anser 2 パター")

    try:
        draft = content_rewriter.draft_new_guide("パター 型落ち", [product])
        assert draft.title == "型落ちパター特選：今買えるお得な型番まとめ"
        assert len(draft.sections) == 1
        assert draft.sections[0].heading == "このページの見方"

        call_kwargs = fake_client.messages.create.call_args.kwargs
        sent_facts = json.loads(call_kwargs["messages"][0]["content"].split("\n", 1)[1])
        assert sent_facts["products"] == [
            {"name": "Anser 2 パター", "brand": "PING", "category": "putter", "current_price_jpy": 58000, "buy_score": "strong_buy"}
        ]
    finally:
        get_settings.cache_clear()
