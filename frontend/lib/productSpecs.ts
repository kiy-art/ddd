import { CATEGORY_LABELS, type Product } from "@/lib/api";
import { PERFORMANCE_TYPE_LABELS, SKILL_LEVEL_LABELS } from "@/lib/badges";

// STEP61: labels and display order for the seller-stated specs the backend
// parses from Rakuten listings (backend app/spec_extractor.py SPEC_FIELDS).
export const SPEC_ORDER: { key: string; label: string }[] = [
  { key: "set", label: "番手構成" },
  { key: "loft", label: "ロフト角" },
  { key: "lie", label: "ライ角" },
  { key: "bounce", label: "バンス角" },
  { key: "head_volume", label: "ヘッド体積" },
  { key: "length", label: "クラブ長さ" },
  { key: "weight", label: "クラブ重量" },
  { key: "shaft", label: "シャフト" },
  { key: "flex", label: "フレックス" },
  { key: "balance", label: "バランス" },
  { key: "material", label: "ヘッド素材" },
  { key: "construction", label: "構造" },
  { key: "cover", label: "カバー" },
];

export function specRows(product: Pick<Product, "specs">): { key: string; label: string; value: string }[] {
  const specs = product.specs ?? {};
  return SPEC_ORDER.filter((s) => specs[s.key]).map((s) => ({ ...s, value: specs[s.key] }));
}

function releaseLabel(iso: string | null): string | null {
  if (!iso) return null;
  const [y, m] = iso.split("-").map(Number);
  return y && m ? `${y}年${m}月` : null;
}

/**
 * A short, factual description built only from stored facts - brand,
 * category, the maker's own positioning (hand-researched, see backend
 * backend/data/product_facts.csv), release date, generation and list price.
 * Nothing is generated or guessed: a fact that isn't stored is simply
 * not mentioned.
 */
export function describeProduct(product: Product): string[] {
  const category = CATEGORY_LABELS[product.category] ?? "ゴルフ用品";
  const lines: string[] = [`${product.brand}の${category}「${product.name}」。`];

  const performance = product.performance_type ? PERFORMANCE_TYPE_LABELS[product.performance_type] : null;
  const skill = product.skill_level ? SKILL_LEVEL_LABELS[product.skill_level] : null;
  if (performance || skill) {
    lines.push(`メーカーの位置づけは${[performance, skill].filter(Boolean).map((t) => `「${t}」`).join("・")}のモデルです。`);
  }

  const released = releaseLabel(product.release_date);
  const generation =
    product.is_current_generation === true
      ? "現行モデル"
      : product.is_current_generation === false
        ? "後継モデルが出ている型落ちモデル"
        : null;
  if (released || generation) {
    lines.push(
      [released ? `${released}発売` : null, generation].filter(Boolean).join("の") + "です。"
    );
  }
  if (product.msrp) {
    lines.push(`メーカー希望小売価格は¥${product.msrp.toLocaleString("ja-JP")}です。`);
  }
  return lines;
}
