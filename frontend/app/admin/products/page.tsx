"use client";

import { useEffect, useState } from "react";

import BuyStatusBadge from "@/components/BuyStatusBadge";
import { useAdminAuth } from "@/lib/adminAuth";
import {
  adminCreateProduct,
  adminDeleteProduct,
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
};

export default function AdminProductsPage() {
  const { token } = useAdminAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

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
      });
      setForm(emptyForm);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold">商品管理</h1>

      <form
        onSubmit={handleCreate}
        className="grid grid-cols-1 gap-3 rounded-xl border border-zinc-200 bg-white p-4 sm:grid-cols-3 dark:border-zinc-800 dark:bg-zinc-900"
      >
        <h2 className="col-span-full font-semibold">商品追加</h2>
        <Field label="商品名" required value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
        <Field label="ブランド" required value={form.brand} onChange={(v) => setForm({ ...form, brand: v })} />
        <label className="flex flex-col gap-1 text-sm">
          カテゴリ
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-800"
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
        {error && <p className="col-span-full text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          className="col-span-full w-fit rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white dark:bg-white dark:text-zinc-900"
        >
          追加
        </button>
      </form>

      {loading && <p className="text-sm text-zinc-500">読み込み中...</p>}

      <div className="flex flex-col gap-3">
        {products.map((product) => (
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
        className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-800"
      />
    </label>
  );
}

function ProductRow({
  product,
  token,
  expanded,
  onToggle,
  onChanged,
}: {
  product: Product;
  token: string;
  expanded: boolean;
  onToggle: () => void;
  onChanged: () => void;
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
    });
    onChanged();
  };

  const handleDelete = async () => {
    if (!confirm(`「${product.name}」を削除しますか？`)) return;
    await adminDeleteProduct(token, product.id);
    onChanged();
  };

  const handleAddPrice = async () => {
    if (!newPrice) return;
    await adminAddPrice(token, product.id, Number(newPrice));
    setNewPrice("");
    setPrices(await adminGetPrices(token, product.id));
    onChanged();
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      <button
        onClick={onToggle}
        className="flex w-full flex-wrap items-center justify-between gap-3 p-4 text-left"
      >
        <div>
          <div className="font-semibold">{product.name}</div>
          <div className="text-xs text-zinc-500">
            {CATEGORY_LABELS[product.category]} ・ {product.brand} ・{" "}
            {product.current_price ? `¥${product.current_price.toLocaleString("ja-JP")}` : "価格未登録"}
          </div>
        </div>
        <BuyStatusBadge buyScore={product.buy_score} />
      </button>

      {expanded && (
        <div className="flex flex-col gap-4 border-t border-zinc-200 p-4 dark:border-zinc-800">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Field label="商品名" value={edit.name} onChange={(v) => setEdit({ ...edit, name: v })} />
            <Field label="ブランド" value={edit.brand} onChange={(v) => setEdit({ ...edit, brand: v })} />
            <label className="flex flex-col gap-1 text-sm">
              カテゴリ
              <select
                value={edit.category}
                onChange={(e) => setEdit({ ...edit, category: e.target.value })}
                className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-800"
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
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white dark:bg-white dark:text-zinc-900"
            >
              保存
            </button>
            <button
              onClick={handleDelete}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
            >
              削除
            </button>
          </div>

          <div className="border-t border-zinc-200 pt-4 dark:border-zinc-800">
            <h3 className="mb-2 text-sm font-semibold">価格履歴</h3>
            <div className="mb-3 flex gap-2">
              <input
                type="number"
                placeholder="新しい価格"
                value={newPrice}
                onChange={(e) => setNewPrice(e.target.value)}
                className="w-40 rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
              />
              <button
                onClick={handleAddPrice}
                className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white dark:bg-white dark:text-zinc-900"
              >
                価格を追加
              </button>
            </div>
            <ul className="max-h-48 overflow-y-auto text-sm text-zinc-600 dark:text-zinc-400">
              {prices
                .slice()
                .reverse()
                .map((p) => (
                  <li key={p.id} className="flex justify-between border-b border-zinc-100 py-1 dark:border-zinc-800">
                    <span>{new Date(p.recorded_at).toLocaleString("ja-JP")}</span>
                    <span>¥{p.price.toLocaleString("ja-JP")}</span>
                  </li>
                ))}
              {prices.length === 0 && <li className="py-1 text-zinc-400">価格履歴がありません</li>}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
