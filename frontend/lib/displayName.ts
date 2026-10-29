// 2026-10-30 (社長指示「製品名はメーカー＋型番のみでよい」): the on-screen
// product name, shortened to "ブランド 型番" from the stored listing name.
// Display only - the stored name (DB, <title>, JSON-LD, alt text, search)
// is untouched, so nothing here can lose data. Rule-based and conservative:
// when the rules can't find a model, it falls back to a lightly cleaned
// name rather than guessing one.

// Same "same name, other script" pairs as backend/app/brands.py
// BRAND_NAME_SYNONYMS, plus the English spellings shops use.
const BRAND_ALIASES: Record<string, string[]> = {
  PING: ["PING", "ピン"],
  Titleist: ["Titleist", "TITLEIST", "タイトリスト"],
  Callaway: ["Callaway", "CALLAWAY", "キャロウェイ"],
  TaylorMade: ["TaylorMade", "TAYLORMADE", "TaylorMade Golf", "テーラーメイド"],
  Srixon: ["SRIXON", "Srixon", "スリクソン", "DUNLOP", "ダンロップ"],
  Bridgestone: ["Bridgestone", "BRIDGESTONE", "ブリヂストン", "ブリジストン"],
  Cobra: ["Cobra", "COBRA", "コブラ"],
  Mizuno: ["Mizuno", "MIZUNO", "ミズノ"],
  XXIO: ["XXIO", "ゼクシオ", "DUNLOP", "ダンロップ"],
  Honma: ["HONMA GOLF", "HONMA", "本間ゴルフ", "ホンマゴルフ", "ホンマ", "本間"],
  "Scotty Cameron": ["Scotty Cameron", "SCOTTY CAMERON", "スコッティキャメロン", "スコッティ・キャメロン"],
  Odyssey: ["ODYSSEY", "Odyssey", "オデッセイ"],
  Cleveland: ["Cleveland", "CLEVELAND", "クリーブランド"],
  "L.A.B Golf": ["L.A.B. Golf", "L.A.B Golf", "L.A.B GOLF", "LAB GOLF", "LABゴルフ", "ラブゴルフ", "ラヴゴルフ"],
  Yonex: ["Yonex", "YONEX", "ヨネックス"],
  Fourteen: ["Fourteen", "FOURTEEN", "フォーティーン", "フォーティン"],
  Miura: ["Miura", "三浦技研"],
  Bettinardi: ["Bettinardi", "ベティナルディ"],
  Wilson: ["Wilson", "ウイルソン"],
  Epon: ["Epon", "EPON", "エポン"],
  FootJoy: ["FootJoy", "Foot Joy", "FOOTJOY", "フットジョイ"],
  Bushnell: ["Bushnell", "BUSHNELL", "ブッシュネル"],
  Nikon: ["Nikon", "NIKON", "ニコン"],
  "Voice Caddie": ["Voice Caddie", "ボイスキャディ"],
  "Shot Navi": ["Shot Navi", "ショットナビ"],
  Garmin: ["Garmin", "GARMIN", "ガーミン"],
  Yupiteru: ["Yupiteru", "YUPITERU", "ユピテル"],
  LITE: ["LITE", "ライト"],
  Tabata: ["Tabata", "TABATA", "タバタ"],
  DAIYA: ["DAIYA", "ダイヤゴルフ", "ダイヤ"],
};

// Katakana spellings of model names that would otherwise be split into a
// stray Latin letter ("Zスター" -> "Z").
const MODEL_KANA: [RegExp, string][] = [
  [/Zスター/g, "Z-STAR "],
  [/ゼットスター/g, " "],
  [/ベレス/g, " BERES "],
  [/ツアーワールド/g, " TOUR WORLD "],
  [/T\/\/WORLD/g, " TOUR WORLD "],
  [/(\d)スター/g, "$1S "],
  [/プロ\s?V1x/g, "PRO V1x "],
  [/プロ\s?V1/g, "PRO V1 "],
];

// Everything from one of these on is the shaft / spec, not the model.
const SPEC_CUT = /(?:[\/／｜:：]|\s(?:ATTAS|VENTUS|Dynamic Gold|DG\b|ELDIO|TOUR AD|Tour AD|Speeder|SPEEDER|Diamana|N\.S\.PRO|NSPRO|NS PRO|MCI|Fujikura|FUJIKURA|ARMAQ|KBS|MODUS|Modus|モーダス|TENSEI|Tensei|TRAVIL|LIN-Q|ALTA|RAUNE|TOUR\s?2[.．]0|TOUR\s?(?:105|120|115)|for\b))/;

// Category / generic words in English that aren't part of a model name.
const GENERIC_EN = new Set([
  "golf", "driver", "iron", "irons", "wedge", "putter", "ball", "balls", "glove", "set", "new", "ccp", "rsl", "jp", "japan",
]);

// Japanese category / filler words, stripped in the kana fallback.
const GENERIC_JA = /(ゴルフ用レーザー距離計|レーザー距離計|ゴルフ距離計|距離計|ゴルフグローブ|グローブ|ゴルフボール|ボール|ドライバー|フェアウェイウッド|ユーティリティ|アイアンセット|アイアン|ウェッジ|パター|ゴルフ|右打用|左打用|右用|左用|メンズ|レディース|通常生産品|日本正規品|正規品|まとめ買い|送料無料|日本全国|シリーズ|モデル|スチール|カーボン|軟鉄)/g;

function stripNoise(raw: string): string {
  let s = raw;
  s = s.replace(/[【\[［〔][^】\]］〕]*[】\]］〕]/g, " "); // shop tags
  s = s.replace(/[「」『』、,]/g, " ");
  s = s.replace(/\d{1,2}\/\d{1,2}\s*\d{1,2}:\d{2}/g, " "); // "10/4 20:00"
  s = s.replace(/\d{1,2}\/\d{1,2}\s?(?:まで|限定)/g, " ");
  s = s.replace(/抽選で\S*/g, " ");
  s = s.replace(/[(（][^A-Za-z0-9)）]*[)）]/g, " ");
  s = s.replace(/最大\s?\d+[％%]\s?OFF/gi, " ");
  s = s.replace(/\d+[％%]\s?OFF/gi, " ");
  s = s.replace(/\(?\d+\s?(?:個入り?|球入り?|個|球|枚入り?|枚セット|本組|本セット|ダース)\)?/g, " ");
  s = s.replace(/\(#[^)]*\)/g, " ");
  s = s.replace(/[(（][^)）]*[ぁ-んァ-ヶ一-龯][^)）]*[)）]/g, " "); // notes in Japanese
  s = s.replace(/[(（]\d{2}[)）]/g, " ");
  s = s.replace(/\('\d\d\)/g, " ");
  s = s.replace(/レビュー\d+件超え/g, " ");
  s = s.replace(/20\d\d\s?(?:年)?(?:\d{1,2}月)?\s?(?:発売|モデル)?/g, " "); // years
  s = s.replace(/\d+(?:\.\d+)?度(?:\/\d+(?:\.\d+)?度)*/g, " "); // lofts
  for (const [re, to] of MODEL_KANA) s = s.replace(re, to);
  return s.replace(/\s+/g, " ").trim();
}

function removeBrand(s: string, brand: string): string {
  const aliases = [...(BRAND_ALIASES[brand] ?? []), brand].sort((a, b) => b.length - a.length);
  let out = s;
  for (const alias of aliases) {
    const esc = alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    // Katakana aliases only as a whole word ("ピン" must not eat "ピンシーカー").
    const isKana = /^[ァ-ヶー・]+$/.test(alias);
    const re = isKana ? new RegExp(`(?<![ァ-ヶー])${esc}(?![ァ-ヶー型])`, "g") : new RegExp(esc, "gi");
    out = out.replace(re, " ");
  }
  return out.replace(/\s+/g, " ").trim();
}

const norm = (t: string) => t.toLowerCase().replace(/[^a-z0-9]/g, "");

function latinModel(s: string): string {
  const cut = s.replace(/^[\s\/／｜:：ー]+/, "").replace(SPEC_CUT, "\u0000").split("\u0000")[0];
  const kept: string[] = [];
  let joined = "";
  for (const tok of cut.split(/\s+/)) {
    // Keep only the Latin/number part of a token ("3Sグレード" -> "3S").
    const latin = tok.replace(/[^A-Za-z0-9.\-+]/g, "").replace(/^[.\-+]+|[.\-+]+$/g, "");
    if (!latin || !/[A-Za-z0-9]/.test(latin)) continue;
    if (GENERIC_EN.has(latin.toLowerCase())) continue;
    if (/^#?\d{1,2}[iI](?:-?P[Ww])?$|^P[Ww]$/.test(latin)) continue; // club numbers ("5I", "6I-PW")
    const n = norm(latin);
    if (!n || joined.includes(n)) continue; // same model written twice
    kept.push(latin);
    joined += n;
  }
  return kept.slice(0, 5).join(" ");
}

export function displayName(p: { name: string; brand: string; model_number?: string | null }): string {
  const brand = p.brand?.trim() ?? "";
  const body = removeBrand(stripNoise(p.name), brand);

  let model = latinModel(body);
  if (model.replace(/\s/g, "").length <= 2) {
    // Too little Latin text to be the model ("V6", nothing at all):
    // use the cleaned Japanese name instead, or the stored model number.
    const kana = body.replace(/^[\s\/／｜:：ー]+/, "").replace(SPEC_CUT, "\u0000").split("\u0000")[0].replace(GENERIC_JA, " ").replace(/[()（）]/g, " ").replace(/\s+/g, " ").trim();
    const kanaModel = kana.replace(/[\s.\-]/g, "").length > model.replace(/\s/g, "").length ? kana : model;
    model = kanaModel || removeBrand(p.model_number ?? "", brand);
  }
  if (!model) return p.name; // nothing safe to show - keep the original
  return brand ? `${brand} ${model}` : model;
}
