"""STEP58: which category a golf listing actually belongs to, judged from
its name - shared by discovery (so a new listing is filed correctly) and
app/category_migration.py (so an already-misfiled one can be moved).

Why this exists: discovery files a listing under the category whose
search keyword found it. Rakuten's search returns loosely related items
too - a putter search also returns practice pins and ball markers, a ball
search returns gloves and marker sets - so those were filed as putters or
balls. They then showed up as "関連商品" on putter/ball pages while the
glove/rangefinder pages stayed empty.

Deliberately conservative - a wrong move is worse than leaving an item
where it is:
- a club/ball listing that names its own product ("... ドライバー",
  "... ゴルフボール 1ダース") stays put even if it also mentions a bundled
  extra ("グローブプレゼント", "マーカー付き");
- compound words that contain a club/ball noun but mean an accessory
  ("ボールマーカー", "パターマット", "パター練習") are read as the
  accessory, not the club/ball;
- nothing is ever moved INTO a club/ball category by this module - it only
  recognizes glove / rangefinder / other.
"""

import re

CLUB_BALL_CATEGORIES = ("driver", "iron", "wedge", "putter", "ball")

# Accessory compounds that contain a club/ball noun - removed before
# checking whether a listing names a club or ball itself.
_ACCESSORY_COMPOUNDS = re.compile(
    r"ボールマーカー|ボール\s*マーカー|ボールケース|ボールポーチ|ボールホルダー|ボールポケット|ボールクリーナー"
    r"|ボール拾い|ボールリトリーバー|パターマット|パター\s*練習|パター用|パターカバー|パターグリップ"
    r"|ドライバー用|アイアン用|ウェッジ用|アイアンカバー|ドライバーカバー"
)

# The listing names a club or ball itself.
_CORE_PRODUCT = re.compile(r"ドライバー|アイアン|ウェッジ|ウエッジ|パター|ボール|\b1W\b|\d+ダース", re.IGNORECASE)

_RANGEFINDER = re.compile(
    r"距離計|距離測定|レーザー距離|レンジファインダー|coolshot|ピンシーカー|ゴルフナビ|GPSナビ|GPSゴルフ",
    re.IGNORECASE,
)
# "グローブライド" is a company (Globeride, maker of ONOFF clubs), not a glove.
_GLOVE = re.compile(r"グローブ(?!ライド)|手袋|\bglove\b", re.IGNORECASE)
# Small on-course / practice accessories with no category of their own.
_OTHER = re.compile(
    r"ピンフラッグ|フラッグ|グリーンフォーク|マーカー|練習用\s*カップ|パッティングカップ|練習器|練習機"
    r"|パッティング練習|練習マット|スイング練習|ゴルフネット|練習ネット|ボール拾い|ボールリトリーバー"
    r"|スコアカード|ティーセット|ゴルフティー|ボールケース|ボールポーチ|ボールホルダー|パターマット"
)
# A bundled extra ("グローブプレゼント", "マーカー付き") - not what's for sale.
_BUNDLED_EXTRA = re.compile(r"(?:グローブ|手袋|マーカー|ティー)\s*(?:付き|付|プレゼント|おまけ|セット付)")


def infer_category(item_name: str) -> str | None:
    """"rangefinder" | "glove" | "other" when the name says so, else None
    (no opinion - keep whatever category the listing already has)."""
    name = _BUNDLED_EXTRA.sub(" ", item_name)
    if _RANGEFINDER.search(name):
        return "rangefinder"
    names_club_or_ball = bool(_CORE_PRODUCT.search(_ACCESSORY_COMPOUNDS.sub(" ", name)))
    if _GLOVE.search(name) and not names_club_or_ball:
        return "glove"
    if _OTHER.search(name) and not names_club_or_ball:
        return "other"
    return None


def corrected_category(item_name: str, current: str) -> str | None:
    """The category `item_name` should move to from `current`, or None to
    leave it. Only ever moves out of a club/ball category, or from "other"
    to the more specific glove/rangefinder."""
    inferred = infer_category(item_name)
    if inferred is None or inferred == current:
        return None
    if current in CLUB_BALL_CATEGORIES:
        return inferred
    if current == "other" and inferred in ("glove", "rangefinder"):
        return inferred
    return None
