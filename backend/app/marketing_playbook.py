"""Professional affiliate-marketing guidance (SEO / CRO / sales copy) for
every piece of copy this site's AI writes on its own - app/ai.py's
routine product copy, app/content_rewriter.py's goal-specific rewrites,
and new guide drafts - kept in one place so all three follow the same
playbook instead of three drifting prompts (STEP43).

Two halves:
- The *guidance* (SEO_TITLE_PRINCIPLES etc.) shapes what Claude writes.
- validate_copy() is the hard backstop: autonomous copy is published
  without a human review (STEP42), so anything that breaks the site's
  anti-fabrication rule or Japan's 景品表示法 (有利誤認/優良誤認) / ステマ
  規制 is rejected in code rather than trusted to the prompt alone.
  A real professional treats compliance as part of the craft, not an
  afterthought - an unsupported "最安値" or "今だけ" can cost an
  affiliate account, which costs far more than any CTR gain.
"""

import re

COMPLIANCE_RULES = """【絶対に守るルール（法令・事実）】
- 与えられた事実データに無い数値（価格・割引率・順位・在庫・スペック）を書かない。数値は与えられた値をそのまま使う。
- 景品表示法に抵触する表現を使わない：根拠の無い「最安値」「業界最安」「No.1」「日本一」、事実でない期間限定・在庫僅少の演出（「今だけ」「残りわずか」「在庫限り」）、効果の断定（「必ず飛ぶ」「誰でも上達」）。
- 「記録上の最安値」と書いてよいのは、事実データの is_at_recorded_lowest_price が true の場合だけ。
- 将来の価格を断定しない（「必ず値上がりする」「確実に値下がりする」は禁止。傾向として述べるのは可）。
- ステルスマーケティング規制：第三者の口コミ・購入者の声・体験談を装わない。「話題沸騰」「みんなが選んでいる」等、根拠の無い評判も書かない。
"""

SEO_TITLE_PRINCIPLES = """【検索結果でクリックされるタイトルの原則（SEO）】
1. 検索意図との一致：real_search_queries に実際にこのページが表示されている検索語がある場合、その言葉（型番・「中古」「値下がり」等の修飾語）を自然に含める。ただし、この商品と一致しない語（別モデル名など）は使わない。
2. 重要語を先頭に：「ブランド名＋商品名」をタイトル冒頭に置く（検索結果で途中が省略されても何の商品か分かるように）。
3. 長さ：全角30文字前後に収める（検索結果での省略を避ける）。
4. 価値提案は1つだけ：実データの数値（定価比◯%安、30日平均比◯%安、記録上の最安値 等）から最も強い1点を選ぶ。
5. キーワードの詰め込み・記号の多用（【】★！の連発）をしない。
"""

CRO_COPY_PRINCIPLES = """【ページ上で「ショップで確認する」行動につなげる文章の原則（CRO）】
1. 結論を先に：最初の一文で「今が買い時か」への答えを実データで示す。
2. 具体性：「お得」「おすすめ」などの抽象語より、実際の価格差・割引率を示す。
3. 判断材料：何と比べて有利なのか（定価、過去30日平均、記録上の最安値）を明示する。
4. 不安への先回り：価格は変動すること、スペック（ロフト・シャフト等）は購入前に確認すべきことに一言触れる。
5. 次の行動を1つに：ショップで最新価格・在庫を確認する、という行動が自然に取れる文で締める。
6. 誇張しない：煽りは短期的にクリックを増やしても信頼と継続的な成果を損なう。事実の強さで訴求する。
"""

GUIDE_PRINCIPLES = """【比較ガイド記事の原則（SEOコンテンツ）】
1. 検索意図に正面から答える：search_query で探している人が知りたいこと（どれが買い時か、どう選ぶか）を冒頭で答える。
2. 実在商品のみ：products に無い商品・型番・価格は書かない。
3. 比較軸を示す：価格・買い時スコア・定価との差など、読者が自分で判断できる軸を提示する。
4. 見出しは具体的に：各セクションの見出しだけで内容が分かるようにする。
5. 次の行動：カテゴリ一覧や値下がり中の商品で実際の価格を確認する流れを作る。
"""

# Claims that are 景品表示法 / anti-fabrication risks regardless of
# context. Deliberately narrow - "必ずご確認ください" in a caution line is
# fine, so only claim-shaped phrases are listed, not bare words.
BANNED_PHRASES = [
    "今だけ",
    "今しかない",
    "最安値保証",
    "業界最安",
    "日本最安",
    "日本一",
    "No.1",
    "ナンバーワン",
    "絶対に",
    "絶対お得",
    "必ず値上がり",
    "必ず値下がり",
    "確実に値",
    "必ず飛",
    "誰でも",
    "間違いなく",
    "限定価格",
    "在庫限り",
    "残りわずか",
    "買わないと損",
    "話題沸騰",
    "口コミで話題",
    "購入者の声",
    "みんなが選",
]

_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[%％]")
_YEN_PREFIX_RE = re.compile(r"[¥￥]\s*(\d[\d,]*)")
_YEN_SUFFIX_RE = re.compile(r"(\d[\d,]*)\s*円")
_MAN_YEN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*万円")


class ContentPolicyViolation(Exception):
    pass


def _percent_matches(value: float, allowed: set[float]) -> bool:
    return any(value == round(abs(a), 1) or value == float(round(abs(a))) for a in allowed)


def validate_copy(
    texts: list[str],
    allowed_yen: set[int],
    allowed_percents: set[float],
    allow_lowest_price_claim: bool = False,
) -> None:
    """Raises ContentPolicyViolation if any AI-written text uses a banned
    claim, a "最安" claim the facts don't support, or a percentage / yen
    figure that isn't one of the real values it was given - i.e. an
    invented number. Every autonomous publish path calls this first."""
    allowed_yen = {int(v) for v in allowed_yen if v is not None}
    allowed_percents = {float(v) for v in allowed_percents if v is not None}

    for text in texts:
        if not text:
            continue
        for phrase in BANNED_PHRASES:
            if phrase in text:
                raise ContentPolicyViolation(f"禁止表現「{phrase}」を含んでいます: {text}")
        if "最安" in text and not allow_lowest_price_claim:
            raise ContentPolicyViolation(f"事実データで裏付けの無い「最安」表現を含んでいます: {text}")

        for m in _PERCENT_RE.finditer(text):
            value = float(m.group(1))
            if not _percent_matches(value, allowed_percents):
                raise ContentPolicyViolation(f"与えられていない数値「{m.group(0)}」を含んでいます: {text}")

        for regex in (_YEN_PREFIX_RE, _YEN_SUFFIX_RE):
            for m in regex.finditer(text):
                value = int(m.group(1).replace(",", ""))
                if value not in allowed_yen:
                    raise ContentPolicyViolation(f"与えられていない価格「{m.group(0)}」を含んでいます: {text}")

        for m in _MAN_YEN_RE.finditer(text):
            raw = m.group(1)
            decimals = len(raw.split(".")[1]) if "." in raw else 0
            value = float(raw)
            if not any(round(y / 10000, decimals) == value for y in allowed_yen):
                raise ContentPolicyViolation(f"与えられていない価格「{m.group(0)}」を含んでいます: {text}")


def product_copy_system_prompt(goal: str | None) -> str:
    """goal: "search_ctr" (win the click on the search results page - the
    title matters most), "on_page_conversion" (turn a visit into a shop
    click - the summary matters most), or None for routine copy."""
    if goal == "search_ctr":
        focus = (
            "今回の目的：検索結果でのクリック率改善。特に title を、実際の検索語と検索意図に合わせて改善すること。\n"
            + SEO_TITLE_PRINCIPLES
            + CRO_COPY_PRINCIPLES
        )
    elif goal == "on_page_conversion":
        focus = (
            "今回の目的：ページを見た人がショップで価格を確認する割合の改善。特に summary を、購入判断に必要な事実が一目で分かる文面に改善すること。\n"
            + CRO_COPY_PRINCIPLES
            + SEO_TITLE_PRINCIPLES
        )
    else:
        focus = SEO_TITLE_PRINCIPLES + CRO_COPY_PRINCIPLES

    return (
        "あなたはゴルフ用品の価格比較サイト「PAR.」の、成果に責任を持つアフィリエイトマーケター兼ファクトチェッカーです。\n"
        "与えられた事実データだけを根拠に、商品ページの文面を日本語で作成してください。\n\n"
        + COMPLIANCE_RULES
        + "\n"
        + focus
        + """
【出力形式】
- 必ず次のJSON形式のみ: {"title": "...", "summary": "...", "caution": "..."}
- title：ページタイトル・検索結果の見出しになる体言止めの短い見出し（商品名を含む）。「〜です。」のような文章にしない。
- summary：titleに入れなかった判断材料を1〜2文で。
- caution：「価格は変動する可能性があります」という主旨の注意書きを必ず含める。
- 価格は「¥58,000」の形式で、与えられた値そのままを書く。
"""
    )


def guide_system_prompt() -> str:
    return (
        "あなたはゴルフ用品の価格比較サイト「PAR.」の、成果に責任を持つSEOコンテンツ編集者です。\n"
        "実際に検索されているキーワードと、サイトに実在する商品リストだけを根拠に、新しい比較ガイド記事の下書きを作成してください。\n\n"
        + COMPLIANCE_RULES
        + "\n"
        + GUIDE_PRINCIPLES
        + """
【出力形式】
- 必ず次のJSON形式のみ:
  {"title": "...", "description": "...", "sections": [{"heading": "...", "paragraphs": ["..."]}]}
- title：検索されやすい具体的な文言（全角32文字程度まで）。
- description：記事の要約（80文字程度まで）。
- sections：2〜3個、各paragraphsは1〜2文。
"""
    )
