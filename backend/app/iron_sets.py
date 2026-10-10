"""Iron price basis: irons are priced as a standard 5-6 club set.

Why this exists (社長指示 2026-10-10): Rakuten/Yahoo iron listings mix
single irons (単品 ≈ ¥30,000), "pick 1-6本" selectable listings whose
headline price is the single-club option, and 5/6本 sets (≈ ¥100,000+).
Taking whichever listing matched made a set-priced model look absurdly
cheap next to the others. So for the iron category only:

- a price is taken only from a listing that is clearly ONE 5- or 6-club set
  (is_standard_set);
- an iron product whose own name says it is a single club, a selectable
  multi-count listing, another set size, a full club set or an iron cover
  is hidden from the public site (is_non_standard_listing).

Wedges, drivers etc. are unaffected - one club is the normal unit there.
"""

import re
import unicodedata

STANDARD_SET_SIZES = (5, 6)

# "5本セット", "6本組", "(5本)", "1本 3本 4本 5本 6本 セット" - every count named.
_COUNT_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*本(?!日)")
# A "#from-to" range: "#6-PW", "6I-PW", "6I PW", "#5～PW", "#6～9、PW",
# "(#5-9,Pw,Aw)", "3-9P", "#7-PW、SW" - from #n through PW (or 9), plus each
# wedge listed right after it.
_RANGE = re.compile(
    r"(?<!\d)#?([3-9])\s*I?\s*(?:[-~～〜]\s*(9|PW|P)|\s+(PW|P))(?![A-Z])"
    r"((?:\s*[,、，.・]?\s*(?:PW|AW|SW|GW|PS|AS|P|A|S)(?![A-Z0-9]))*)",
    re.IGNORECASE,
)
_WEDGE_TOKEN = re.compile(r"PW|AW|SW|GW|PS|AS|P|A|S", re.IGNORECASE)

_SINGLE_MARKERS = re.compile(r"単品|バラ売り|ばら売り|1本売り")
# Not an iron set at all, even though "アイアン" is in the name.
_NOT_AN_IRON_SET = re.compile(r"クラブセット|キャディ\s*バッグ付|アイアンカバー|ヘッドカバー|\d+\s*個セット")


def _normalize(name: str) -> str:
    return unicodedata.normalize("NFKC", name or "")


def club_counts(name: str) -> set[int]:
    """Every club count the listing name states (empty when it states none)."""
    text = _normalize(name)
    counts = {int(n) for n in _COUNT_PATTERN.findall(text)}
    for start, dash_end, space_end, extras in _RANGE.findall(text):
        end = dash_end or space_end
        through = 9 - int(start) + 1 + (0 if end == "9" else 1)
        counts.add(through + len(_WEDGE_TOKEN.findall(extras)))
    if _SINGLE_MARKERS.search(text):
        counts.add(1)
    return counts


def set_size(name: str) -> int | None:
    """The one set size the listing is for, or None when it names none or
    several (a "1本 3本 5本 6本" selectable listing has no single size)."""
    counts = club_counts(name)
    return next(iter(counts)) if len(counts) == 1 else None


def is_standard_set(name: str) -> bool:
    """True only for a listing that is clearly a single 5- or 6-club set."""
    if _NOT_AN_IRON_SET.search(_normalize(name)):
        return False
    return set_size(name) in STANDARD_SET_SIZES


def is_non_standard_listing(name: str) -> bool:
    """True when the name itself says this is NOT a 5-6本 set - a single
    club, a selectable multi-count listing, another set size, a full club
    set or an iron cover. A name that states no count at all ("G430 アイアン")
    is not judged here (its price is taken from set listings instead)."""
    text = _normalize(name)
    if _NOT_AN_IRON_SET.search(text):
        return True
    counts = club_counts(text)
    return bool(counts) and not (len(counts) == 1 and next(iter(counts)) in STANDARD_SET_SIZES)
