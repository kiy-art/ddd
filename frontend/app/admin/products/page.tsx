"use client";

import { useEffect, useState } from "react";

import BuyStatusBadge from "@/components/BuyStatusBadge";
import { useAdminAuth } from "@/lib/adminAuth";
import {
  adminApproveProduct,
  adminCreateProduct,
  adminDeleteProduct,
  adminDeletePrice,
  adminUpdateProduct,
  adminListProducts,
  adminAddPrice,
  adminGetPrices,
  CATEGORIES,
  CATEGORY_LABELS,
  PriceHistoryItem,
  Product,
} from "@/lib/api";

const emptyForm = {
  name: "",
  brand: "",
  category: CATEGORIES[0] as string,
  model_number: "",
  image_url: "",
  product_url: "",
  affiliate_url: "",
  initial_price: "",
  msrp: "",
  release_date: "",
  skill_level: "",
  performance_type: "",
  is_current_generation: "",
};

const SKILL_LEVEL_LABELS: Record<string, string> = {
  beginner: "初心者向け",
  all_levels: "オールレベル",
  advanced: "上級者向け",
};

const PERFORMANCE_TYPE_LABELS: Record<string, string> = {
  distance: "飛距離重視",
  forgiveness: "やさしさ重視",
  control: "操作性重視",
  balanced: "バランス型",
};

export default function AdminProductsPage() {
  const { token } = useAdminAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);

  const pendingProducts = products.filter((p) => p.pending_review);
  const publishedProducts = products.filter((p) => !p.pending_review);

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleSelectAllPending = () => {
    setSelectedIds((prev) =>
      prev.size === pendingProducts.length ? new Set() : new Set(pendingProducts.map((p) => p.id))
    );
  };

  const handleBulkApprove = async () => {
    if (!token || selectedIds.size === 0) return;
    setBulkBusy(true);
    try {
      await Promise.all([...selectedIds].map((id) => adminApproveProduct(token, id)));
      setSelectedIds(new Set());
      await load();
    } finally {
      setBulkBusy(false);
    }
  };

  const handleBulkDelete = async () => {
    if (!token || selectedIds.size === 0) return;
    if (!confirm(`選択した${selectedIds.size}件を却下（削除）しますか？`)) return;
    setBulkBusy(true);
    try {
      await Promise.all([...selectedIds].map((id) => adminDeleteProduct(token, id)));
      setSelectedIds(new Set());
      await load();
    } finally {
      setBulkBusy(false);
    }
  };

  const load = async () => {
    if (!token) return;
    const data = await adminListProducts(token);
    setProducts(data);
    setLoading(false);
  };

  useEffect(() => {
    if (!token) return;
    let ignore = false;
    adminListProducts(token).then((data) => {
      if (!ignore) {
        setProducts(data);
        setLoading(false);
      }
    });
    return () => {
      ignore = true;
    };
  }, [token]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError(null);
    try {
      await adminCreateProduct(token, {
        name: form.name,
        brand: form.brand,
        category: form.category,
        model_number: form.model_number || undefined,
        image_url: form.image_url || undefined,
        product_url: form.product_url || undefined,
        affiliate_url: form.affiliate_url || undefined,
        initial_price: form.initial_price ? Number(form.initial_price) : undefined,
        msrp: form.msrp ? Number(form.msrp) : undefined,
        release_date: form.release_date || undefined,
        skill_level: form.skill_level || undefined,
        performance_type: form.performance_type || undefined,
        is_current_generation: form.is_current_generation ? form.is_current_generation === "true" : undefined,
      });
      setForm(emptyForm);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-xl font-semibold text-foreground">商品管理</h1>

      <form
        onSubmit={handleCreate}
        className="grid grid-cols-1 gap-3 rounded-2xl border border-border bg-card p-5 sm:grid-cols-3"
      >
        <h2 className="col-span-full font-display font-medium text-foreground">商品追加</h2>
        <Field label="商品名" required value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
        <Field label="ブランド" required value={form.brand} onChange={(v) => setForm({ ...form, brand: v })} />
        <label className="flex flex-col gap-1 text-sm">
          カテゴリ
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="rounded-lg border border-border bg-background px-3 py-2 text-foreground"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABELS[c]}
              </option>
            ))}
          </select>
        </label>
        <Field label="型番" value={form.model_number} onChange={(v) => setForm({ ...form, model_number: v })} />
        <Field
          label="初期価格 (円)"
          type="number"
          value={form.initial_price}
          onChange={(v) => setForm({ ...form, initial_price: v })}
        />
        <Field label="画像URL" value={form.image_url} onChange={(v) => setForm({ ...form, image_url: v })} />
        <Field
          label="商品ページURL"
          value={form.product_url}
          onChange={(v) => setForm({ ...form, product_url: v })}
        />
        <Field
          label="アフィリエイトURL"
          value={form.affiliate_url}
          onChange={(v) => setForm({ ...form, affiliate_url: v })}
        />
        <Field
          label="メーカー希望小売価格 (円)"
          type="number"
          value={form.msrp}
          onChange={(v) => setForm({ ...form, msrp: v })}
        />
        <Field
          label="発売日"
          type="date"
          value={form.release_date}
          onChange={(v) => setForm({ ...form, release_date: v })}
        />
        <SelectField
          label="対象スキルレベル"
          value={form.skill_level}
          options={SKILL_LEVEL_LABELS}
          onChange={(v) => setForm({ ...form, skill_level: v })}
        />
        <SelectField
          label="性能タイプ"
          value={form.performance_type}
          options={PERFORMANCE_TYPE_LABELS}
          onChange={(v) => setForm({ ...form, performance_type: v })}
        />
        <SelectField
          label="現行モデルか"
          value={form.is_current_generation}
          options={{ true: "現行モデル", false: "型落ちモデル" }}
          onChange={(v) => setForm({ ...form, is_current_generation: v })}
        />
        {error && <p className="col-span-full text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          className="col-span-full w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white"
        >
          追加
        </button>
      </form>

      {loading && <p className="text-sm text-foreground/50">読み込み中...</p>}

      {pendingProducts.length > 0 && (
        <div className="flex flex-col gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-5">
          <div>
            <h2 className="font-display font-medium text-foreground">
              承認待ち（{pendingProducts.length}件）
            </h2>
            <p className="mt-1 text-sm text-foreground/60">
              自動検出された商品です。ブランド・カテゴリ・価格・画像が正しいか確認してから承認してください。
              承認するまでサイトには表示されません。
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 border-b border-amber-200 pb-3 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selectedIds.size > 0 && selectedIds.size === pendingProducts.length}
                onChange={toggleSelectAllPending}
              />
              全て選択（{selectedIds.size}件選択中）
            </label>
            <button
              onClick={handleBulkApprove}
              disabled={selectedIds.size === 0 || bulkBusy}
              className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              選択した{selectedIds.size}件を承認
            </button>
            <button
              onClick={handleBulkDelete}
              disabled={selectedIds.size === 0 || bulkBusy}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-40"
            >
              選択した{selectedIds.size}件を却下（削除）
            </button>
          </div>

          <div className="flex flex-col gap-3">
            {pendingProducts.map((product) => (
              <ProductRow
                key={product.id}
                product={product}
                token={token!}
                expanded={expandedId === product.id}
                onToggle={() => setExpandedId(expandedId === product.id ? null : product.id)}
                onChanged={load}
                pending
                selected={selectedIds.has(product.id)}
                onToggleSelect={() => toggleSelect(product.id)}
              />
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {publishedProducts.map((product) => (
          <ProductRow
            key={product.id}
            product={product}
            token={token!}
            expanded={expandedId === product.id}
            onToggle={() => setExpandedId(expandedId === product.id ? null : product.id)}
            onChanged={load}
          />
        ))}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  required,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  type?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      {label}
      <input
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-border bg-background px-3 py-2 text-foreground"
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Record<string, string>;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-border bg-background px-3 py-2 text-foreground"
      >
        <option value="">未設定</option>
        {Object.entries(options).map(([v, label2]) => (
          <option key={v} value={v}>
            {label2}
          </option>
        ))}
      </select>
    </label>
  );
}

function ProductRow({
  product,
  token,
  expanded,
  onToggle,
  onChanged,
  pending = false,
  selected = false,
  onToggleSelect,
}: {
  product: Product;
  token: string;
  expanded: boolean;
  onToggle: () => void;
  onChanged: () => void;
  pending?: boolean;
  selected?: boolean;
  onToggleSelect?: () => void;
}) {
  const [prices, setPrices] = useState<PriceHistoryItem[]>([]);
  const [newPrice, setNewPrice] = useState("");
  const [edit, setEdit] = useState({
    name: product.name,
    brand: product.brand,
    category: product.category,
    model_number: product.model_number ?? "",
    image_url: product.image_url ?? "",
    product_url: product.product_url ?? "",
    affiliate_url: product.affiliate_url ?? "",
    msrp: product.msrp !== null ? String(product.msrp) : "",
    release_date: product.release_date ?? "",
    skill_level: product.skill_level ?? "",
    performance_type: product.performance_type ?? "",
    is_current_generation: product.is_current_generation === null ? "" : String(product.is_current_generation),
  });

  useEffect(() => {
    if (expanded) {
      adminGetPrices(token, product.id).then(setPrices);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expanded]);

  const handleSave = async () => {
    await adminUpdateProduct(token, product.id, {
      name: edit.name,
      brand: edit.brand,
      category: edit.category,
      model_number: edit.model_number || undefined,
      image_url: edit.image_url || undefined,
      product_url: edit.product_url || undefined,
      affiliate_url: edit.affiliate_url || undefined,
      msrp: edit.msrp ? Number(edit.msrp) : null,
      release_date: edit.release_date || null,
      skill_level: edit.skill_level || null,
      performance_type: edit.performance_type || null,
      is_current_generation: edit.is_current_generation ? edit.is_current_generation === "true" : null,
    });
    onChanged();
  };

  const handleDelete = async () => {
    if (!confirm(`「${product.name}」を削除しますか？`)) return;
    await adminDeleteProduct(token, product.id);
    onChanged();
  };

  const handleApprove = async () => {
    await adminApproveProduct(token, product.id);
    onChanged();
  };

  const handleAddPrice = async () => {
    if (!newPrice) return;
    await adminAddPrice(token, product.id, Number(newPrice));
    setNewPrice("");
    setPrices(await adminGetPrices(token, product.id));
    onChanged();
  };

  const handleDeletePrice = async (priceId: number, price: number) => {
    if (!confirm(`¥${price.toLocaleString("ja-JP")} の価格履歴を削除しますか？（誤った価格データの削除用）`)) return;
    await adminDeletePrice(token, priceId);
    setPrices(await adminGetPrices(token, product.id));
    onChanged();
  };

  return (
    <div className="rounded-2xl border border-border bg-card">
      <div className="flex w-full flex-wrap items-center justify-between gap-3 p-4">
        <div className="flex flex-1 items-center gap-3">
          {pending && (
            <input
              type="checkbox"
              checked={selected}
              onChange={onToggleSelect}
              onClick={(e) => e.stopPropagation()}
              className="h-4 w-4 shrink-0"
            />
          )}
          <button onClick={onToggle} className="flex-1 text-left">
            <div className="font-semibold">{product.name}</div>
            <div className="text-xs text-foreground/50">
              {CATEGORY_LABELS[product.category]} ・ {product.brand} ・{" "}
              {product.current_price ? `¥${product.current_price.toLocaleString("ja-JP")}` : "価格未登録"}
            </div>
          </button>
        </div>
        <button onClick={onToggle}>
          {pending ? (
            <span className="rounded-full bg-amber-200 px-3 py-1 text-xs font-semibold text-amber-900">
              承認待ち
            </span>
          ) : (
            <BuyStatusBadge buyScore={product.buy_score} />
          )}
        </button>
      </div>

      {expanded && (
        <div className="flex flex-col gap-4 border-t border-border p-5">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Field label="商品名" value={edit.name} onChange={(v) => setEdit({ ...edit, name: v })} />
            <Field label="ブランド" value={edit.brand} onChange={(v) => setEdit({ ...edit, brand: v })} />
            <label className="flex flex-col gap-1 text-sm">
              カテゴリ
              <select
                value={edit.category}
                onChange={(e) => setEdit({ ...edit, category: e.target.value })}
                className="rounded-lg border border-border bg-background px-3 py-2 text-foreground"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {CATEGORY_LABELS[c]}
                  </option>
                ))}
              </select>
            </label>
            <Field
              label="型番"
              value={edit.model_number}
              onChange={(v) => setEdit({ ...edit, model_number: v })}
            />
            <Field label="画像URL" value={edit.image_url} onChange={(v) => setEdit({ ...edit, image_url: v })} />
            <Field
              label="商品ページURL"
              value={edit.product_url}
              onChange={(v) => setEdit({ ...edit, product_url: v })}
            />
            <Field
              label="アフィリエイトURL"
              value={edit.affiliate_url}
              onChange={(v) => setEdit({ ...edit, affiliate_url: v })}
            />
            <Field
              label="メーカー希望小売価格 (円)"
              type="number"
              value={edit.msrp}
              onChange={(v) => setEdit({ ...edit, msrp: v })}
            />
            <Field
              label="発売日"
              type="date"
              value={edit.release_date}
              onChange={(v) => setEdit({ ...edit, release_date: v })}
            />
            <SelectField
              label="対象スキルレベル"
              value={edit.skill_level}
              options={SKILL_LEVEL_LABELS}
              onChange={(v) => setEdit({ ...edit, skill_level: v })}
            />
            <SelectField
              label="性能タイプ"
              value={edit.performance_type}
              options={PERFORMANCE_TYPE_LABELS}
              onChange={(v) => setEdit({ ...edit, performance_type: v })}
            />
            <SelectField
              label="現行モデルか"
              value={edit.is_current_generation}
              options={{ true: "現行モデル", false: "型落ちモデル" }}
              onChange={(v) => setEdit({ ...edit, is_current_generation: v })}
            />
          </div>
          <div className="flex gap-2">
            {pending && (
              <button
                onClick={handleApprove}
                className="rounded-full bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white"
              >
                承認して公開
              </button>
            )}
            <button
              onClick={handleSave}
              className="rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white"
            >
              保存
            </button>
            <button
              onClick={handleDelete}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
            >
              {pending ? "却下（削除）" : "削除"}
            </button>
          </div>

          <div className="border-t border-border pt-4">
            <h3 className="mb-2 text-sm font-display font-medium text-foreground">価格履歴</h3>
            <div className="mb-3 flex gap-2">
              <input
                type="number"
                placeholder="新しい価格"
                value={newPrice}
                onChange={(e) => setNewPrice(e.target.value)}
                className="w-40 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
              />
              <button
                onClick={handleAddPrice}
                className="rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white"
              >
                価格を追加
              </button>
            </div>
            <ul className="max-h-48 overflow-y-auto text-sm text-foreground/60">
              {prices
                .slice()
                .reverse()
                .map((p) => (
                  <li key={p.id} className="flex items-center justify-between gap-2 border-b border-border py-1">
                    <span>{new Date(p.recorded_at).toLocaleString("ja-JP")}</span>
                    <span className="flex items-center gap-2">
                      ¥{p.price.toLocaleString("ja-JP")}
                      <button
                        onClick={() => handleDeletePrice(p.id, p.price)}
                        title="この価格データを削除（誤検出の修正用）"
                        className="rounded px-1.5 py-0.5 text-xs font-semibold text-red-600 hover:bg-red-50"
                      >
                        削除
                      </button>
                    </span>
                  </li>
                ))}
              {prices.length === 0 && <li className="py-1 text-foreground/35">価格履歴がありません</li>}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
