"""Same-model grouping (dry-run only): finds products that are the SAME
model and the SAME spec but are listed as separate rows because each shop
sells them with a different shaft / head option / title wording
(e.g. 'Spider ZT STANDARD' x4, 'SRIXON ZXi5 6本セット' x3 shafts).

Design (docs/departments/04_SE/01_部内検討/2026-11-19_同一モデル統合の設計とdry-run案.md):

- This module is PURE: it reads Product-like objects and returns a plan.
  It never writes to the DB. A later, separately-approved apply step would
  reuse title_migration's merge mechanics.
- Conservative by construction. A product only gets a key when it matches
  exactly ONE row of MODEL_LINES (an explicit allow-list of model lines).
  Anything else has no key and is never grouped. Adding a model line is a
  one-row change, so false merges cannot happen outside the list.
- The key is (brand, category, line, variant axes, generation, set size).
  Shaft names are deliberately NOT part of the key (they are the thing we
  want to ignore), but every axis that changes what the buyer gets is.
- Anything unclear goes to the review list with a reason; only groups whose
  members all have a clear key and a consistent price are 'auto' candidates.
"""

import dataclasses
import re
import statistics
import unicodedata

from app import iron_sets

# (brand, category, canonical line name, pattern that must match,
#  pattern that must NOT match). Matched against the NFKC-lowered name.
MODEL_LINES: list[tuple[str, str, str, str, str | None]] = [
    ("TaylorMade", "putter", "Spider ZT", r"spider\s*[-]?\s*zt|スパイダー\s*[-]?\s*zt|スパイダー.*ゼロトルク", r"5k"),
    ("Srixon", "iron", "ZXi5", r"zxi\s*5", None),
    ("Srixon", "iron", "ZXi7", r"zxi\s*7", None),
    ("Srixon", "iron", "ZX4 Mk II", r"(?<![a-z])zx\s*4(?!\d)", None),  # generation split below
    ("Srixon", "iron", "ZX5 Mk II", r"(?<![a-z])zx\s*5(?!\d)", r"zxi"),
    ("Srixon", "iron", "ZX7 Mk II", r"(?<![a-z])zx\s*7(?!\d)", r"zxi"),
]

_MK2 = re.compile(r"mk\s*[-]?\s*(?:ii|2)\b|マーク\s*(?:ii|2|ツー)")
_YEAR = re.compile(r"(?<!\d)(20[12]\d)(?!\d)")
_LEFT = re.compile(r"(?<![a-z])lh(?![a-z])|left|レフト|左|lefty")
_LADY = re.compile(r"lady|ladies|women|ウィメンズ|レディ")
_LOFT = re.compile(r"ロフト(?:角)?\s*([\d.]+)\s*度")
_LENGTH = re.compile(r"(\d{2}(?:\.\d)?)\s*(?:インチ|inch)")
_BULK = re.compile(r"まとめ買い|\d+\s*(?:ダース|個セット|枚|双|足|パック)")
# putter variant axes - each one changes the head/length the buyer gets
_VARIANTS = {
    "max": re.compile(r"(?<![a-z])max(?![a-z])|マックス"),
    "long": re.compile(r"(?<![a-z])long(?![a-z])|ロング"),
    "counterbalance": re.compile(r"counter\s*-?\s*balance|c-?balance|カウンター\s*バランス"),
    "midlength": re.compile(r"中尺"),
    "single_line": re.compile(r"single\s*line|シングル\s*ライン"),
    "black": re.compile(r"(?<![a-z])black(?![a-z])|ブラック"),
    "standard": re.compile(r"standard|(?<![a-z])std(?![a-z])|スタンダード"),
}


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").lower()


@dataclasses.dataclass(frozen=True)
class ModelKey:
    brand: str
    category: str
    line: str
    variants: tuple[str, ...]
    generation: str  # "MkII" / "2025" / "" (none stated)
    set_size: int | None
    loft: str  # "" or e.g. "3.5"
    length: tuple[str, ...]  # inches stated, e.g. ("36", "38")
    handed: str  # "" (right/unstated) / "LH"
    lady: bool
    bulk: bool

    def label(self) -> str:
        parts = [self.brand, self.category, self.line]
        if self.variants:
            parts.append("/".join(self.variants))
        if self.generation:
            parts.append(self.generation)
        if self.set_size:
            parts.append(f"{self.set_size}本")
        if self.loft:
            parts.append(f"ロフト{self.loft}度")
        if self.length:
            parts.append("/".join(self.length) + "インチ")
        if self.handed:
            parts.append(self.handed)
        if self.lady:
            parts.append("レディース")
        if self.bulk:
            parts.append("まとめ買い")
        return " ".join(parts)


def extract_key(brand: str, category: str, name: str) -> tuple[ModelKey | None, str]:
    """(key, reason). key is None when the product must not be grouped;
    reason says why ('表外' = not in MODEL_LINES, or what is ambiguous)."""
    text = _norm(name)
    hits = [
        row
        for row in MODEL_LINES
        if row[0] == brand and row[1] == category and re.search(row[3], text) and not (row[4] and re.search(row[4], text))
    ]
    if not hits:
        return None, "表外(MODEL_LINESに該当なし)"
    if len(hits) > 1:
        return None, "複数ラインに該当(曖昧)"
    line = hits[0][2]

    if line == "ZX4 Mk II" and not _MK2.search(text):
        line = "ZX4"  # first generation is a different model
    elif "Mk II" in line and not _MK2.search(text):
        return None, "世代(Mk II)が名前から確認できない"
    # A stated year is part of the key; "no year" and "2023" are different
    # keys on purpose (can't prove they are the same release) - the dry-run
    # report does not merge them.
    year = _YEAR.search(text)
    generation = year.group(1) if year else ""

    set_size = None
    if category == "iron":
        set_size = iron_sets.set_size(name)
        if set_size is None or iron_sets.is_non_standard_listing(name):
            return None, "アイアンの本数が1つに決まらない/単品・選択式"

    variants: tuple[str, ...] = ()
    if category == "putter":
        found = sorted(v for v, pat in _VARIANTS.items() if pat.search(text))
        variants = tuple(found)
        if not variants:
            return None, "型(standard/MAX/long等)が名前に無い"

    key = ModelKey(
        brand=brand,
        category=category,
        line=line,
        variants=variants,
        generation=generation,
        set_size=set_size,
        loft=(_LOFT.search(text).group(1) if _LOFT.search(text) else ""),
        length=tuple(sorted(set(_LENGTH.findall(text)))),
        handed="LH" if _LEFT.search(text) else "",
        lady=bool(_LADY.search(text)),
        bulk=bool(_BULK.search(text)),
    )
    return key, ""


@dataclasses.dataclass
class Group:
    key: ModelKey
    members: list  # Product-like
    survivor: object
    status: str  # "auto" | "review"
    reasons: list[str]


@dataclasses.dataclass
class GroupingPlan:
    products_checked: int
    keyed: int
    groups: list[Group]
    unkeyed: list[tuple[object, str]]
    plan_lines: list[str]

    @property
    def auto_groups(self) -> list[Group]:
        return [g for g in self.groups if g.status == "auto"]


MAX_PRICE_SPREAD = 1.25  # max/min current_price in a group; above -> review


def _pick_survivor(members: list, impressions: dict[str, int]) -> object:
    return sorted(
        members,
        key=lambda p: (
            bool(getattr(p, "pending_review", False)),
            -impressions.get(p.slug, 0),
            -len(getattr(p, "price_history", None) or []),
            getattr(p, "id", 0),
        ),
    )[0]


def plan_model_grouping(products: list, impressions: dict[str, int] | None = None) -> GroupingPlan:
    impressions = impressions or {}
    buckets: dict[ModelKey, list] = {}
    unkeyed: list[tuple[object, str]] = []
    for product in products:
        key, reason = extract_key(product.brand, product.category, product.name)
        if key is None:
            unkeyed.append((product, reason))
        else:
            buckets.setdefault(key, []).append(product)

    groups: list[Group] = []
    for key, members in buckets.items():
        if len(members) < 2:
            continue
        reasons: list[str] = []
        prices = [p.current_price for p in members if getattr(p, "current_price", None)]
        if prices and max(prices) / min(prices) > MAX_PRICE_SPREAD:
            reasons.append(f"価格差が大きい(¥{min(prices):,}〜¥{max(prices):,}、{MAX_PRICE_SPREAD}倍超)")
        if sum(1 for p in members if not getattr(p, "pending_review", False)) == 0:
            reasons.append("全員が審査待ち(公開済みが無い)")
        if prices and statistics.median(prices) and any(p < statistics.median(prices) * 0.6 for p in prices):
            reasons.append("中央値の6割未満の価格がある(単品・別仕様の疑い)")
        survivor = _pick_survivor(members, impressions)
        groups.append(Group(key, members, survivor, "review" if reasons else "auto", reasons))
    groups.sort(key=lambda g: (-len(g.members), g.key.label()))

    lines = [
        f"対象商品: {len(products)}件 / キー付与: {len(products) - len(unkeyed)}件 / キー無し: {len(unkeyed)}件",
        f"グループ: {len(groups)}件(自動候補 {sum(g.status == 'auto' for g in groups)} / 要確認 {sum(g.status == 'review' for g in groups)})",
        f"統合すると減る商品: 自動候補 {sum(len(g.members) - 1 for g in groups if g.status == 'auto')}件",
        "",
    ]
    for i, g in enumerate(groups, start=1):
        pr = [p.current_price for p in g.members if getattr(p, "current_price", None)]
        span = f"¥{min(pr):,}〜¥{max(pr):,}" if pr else "価格なし"
        lines.append(
            f"[G{i:02d}] {g.key.label()}  存続 id={g.survivor.id} slug={g.survivor.slug}"
            f" <- 統合 id={[p.id for p in g.members if p is not g.survivor]}  {span}  "
            + ("【自動候補】" if g.status == "auto" else "【要確認: " + " / ".join(g.reasons) + "】")
        )
        for p in g.members:
            lines.append(f"      id={p.id} ¥{(p.current_price or 0):,} {p.name}")
    lines.append("")
    lines.append("これはdry-runです。DBは変更していません。")
    return GroupingPlan(len(products), len(products) - len(unkeyed), groups, unkeyed, lines)
