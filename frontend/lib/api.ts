export interface PriceHistoryItem {
  id: number;
  price: number;
  recorded_at: string;
}

export interface Product {
  id: number;
  slug: string;
  name: string;
  brand: string;
  category: string;
  model_number: string | null;
  image_url: string | null;
  product_url: string | null;
  affiliate_url: string | null;
  current_price: number | null;
  previous_price: number | null;
  lowest_price: number | null;
  average_price: number | null;
  price_change_percent: number | null;
  buy_score: string;
  buy_signal_score: number | null;
  history_span_days: number;
  buy_reason: string | null;
  pending_review: boolean;
  ai_title: string | null;
  ai_summary: string | null;
  ai_caution: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductDetail extends Product {
  price_history: PriceHistoryItem[];
}

export interface ErrorLog {
  id: number;
  level: string;
  source: string;
  product_id: number | null;
  message: string;
  created_at: string;
}

export interface CsvImportResult {
  created_products: number;
  updated_products: number;
  prices_recorded: number;
  errors: string[];
}

export interface PriceAnomaly {
  price_history_id: number;
  product_id: number;
  product_name: string;
  product_slug: string;
  price: number;
  recorded_at: string;
  reference_price: number;
  ratio: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const CATEGORIES = ["driver", "iron", "wedge", "putter", "ball"] as const;
export type Category = (typeof CATEGORIES)[number];

export const CATEGORY_LABELS: Record<string, string> = {
  driver: "ドライバー",
  iron: "アイアン",
  wedge: "ウェッジ",
  putter: "パター",
  ball: "ボール",
};

export const BUY_SCORES = ["strong_buy", "buy", "neutral", "not_buy", "insufficient_data"] as const;

export const BUY_SCORE_LABELS: Record<string, string> = {
  strong_buy: "強い買い時",
  buy: "買い時",
  neutral: "様子見",
  not_buy: "買い時ではない",
  insufficient_data: "判定不能",
};

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Public API ---------------------------------------------------------

export function getProducts(params?: { category?: string; buy_score?: string; limit?: number }) {
  const qs = new URLSearchParams();
  if (params?.category) qs.set("category", params.category);
  if (params?.buy_score) qs.set("buy_score", params.buy_score);
  if (params?.limit) qs.set("limit", String(params.limit));
  const query = qs.toString();
  return apiFetch<Product[]>(`/api/products${query ? `?${query}` : ""}`);
}

export function getProduct(slug: string) {
  return apiFetch<ProductDetail>(`/api/products/${slug}`);
}

export function getCategoryProducts(category: string) {
  return apiFetch<Product[]>(`/api/categories/${category}`);
}

export interface BrandSummary {
  brand: string;
  product_count: number;
}

export function getBrands() {
  return apiFetch<BrandSummary[]>(`/api/brands`);
}

export function getBrandProducts(brand: string) {
  return apiFetch<Product[]>(`/api/brands/${encodeURIComponent(brand)}`);
}

export interface PriceAlert {
  id: number;
  product_id: number;
  email: string;
  target_price: number;
  created_at: string;
  notified_at: string | null;
}

export interface PriceAlertAdmin extends PriceAlert {
  product_name: string;
  product_slug: string;
  current_price: number | null;
  triggered: boolean;
}

export function createPriceAlert(slug: string, email: string, targetPrice: number) {
  return apiFetch<PriceAlert>(`/api/products/${slug}/alerts`, {
    method: "POST",
    body: JSON.stringify({ email, target_price: targetPrice }),
  });
}

export interface ContactMessage {
  id: number;
  name: string | null;
  email: string;
  message: string;
  created_at: string;
  read_at: string | null;
}

export function submitContactMessage(data: { name?: string; email: string; message: string }) {
  return apiFetch<ContactMessage>(`/api/contact`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// --- Admin API (client-side, Bearer token from localStorage) ------------

function adminHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export function adminListProducts(token: string) {
  return apiFetch<Product[]>(`/api/admin/products`, { headers: adminHeaders(token) });
}

export function adminCreateProduct(
  token: string,
  data: {
    name: string;
    brand: string;
    category: string;
    model_number?: string;
    image_url?: string;
    product_url?: string;
    affiliate_url?: string;
    initial_price?: number;
  }
) {
  return apiFetch<Product>(`/api/admin/products`, {
    method: "POST",
    headers: adminHeaders(token),
    body: JSON.stringify(data),
  });
}

export function adminUpdateProduct(token: string, id: number, data: Partial<Product>) {
  return apiFetch<Product>(`/api/admin/products/${id}`, {
    method: "PUT",
    headers: adminHeaders(token),
    body: JSON.stringify(data),
  });
}

export function adminDeleteProduct(token: string, id: number) {
  return apiFetch<void>(`/api/admin/products/${id}`, {
    method: "DELETE",
    headers: adminHeaders(token),
  });
}

export function adminGetPrices(token: string, id: number) {
  return apiFetch<PriceHistoryItem[]>(`/api/admin/products/${id}/prices`, {
    headers: adminHeaders(token),
  });
}

export function adminAddPrice(token: string, id: number, price: number) {
  return apiFetch<Product>(`/api/admin/products/${id}/prices`, {
    method: "POST",
    headers: adminHeaders(token),
    body: JSON.stringify({ price }),
  });
}

export function adminDeletePrice(token: string, priceHistoryId: number) {
  return apiFetch<Product>(`/api/admin/prices/${priceHistoryId}`, {
    method: "DELETE",
    headers: adminHeaders(token),
  });
}

export function adminGetPendingProducts(token: string) {
  return apiFetch<Product[]>(`/api/admin/pending-products`, { headers: adminHeaders(token) });
}

export function adminApproveProduct(token: string, id: number) {
  return apiFetch<Product>(`/api/admin/products/${id}/approve`, {
    method: "POST",
    headers: adminHeaders(token),
  });
}

export function adminDiscoverProducts(token: string) {
  return apiFetch<{ products_discovered: number; candidates_considered: number }>(
    `/api/admin/discover-products`,
    { method: "POST", headers: adminHeaders(token) }
  );
}

export function adminGetPriceAnomalies(token: string) {
  return apiFetch<PriceAnomaly[]>(`/api/admin/price-anomalies`, { headers: adminHeaders(token) });
}

export function adminFixPriceAnomalies(token: string) {
  return apiFetch<PriceAnomaly[]>(`/api/admin/price-anomalies/fix`, {
    method: "POST",
    headers: adminHeaders(token),
  });
}

export function adminGetPriceAlerts(token: string) {
  return apiFetch<PriceAlertAdmin[]>(`/api/admin/price-alerts`, { headers: adminHeaders(token) });
}

export interface PageStat {
  path: string;
  pageviews: number;
  active_users: number;
  bounce_rate: number;
  avg_engagement_seconds: number;
}

export function adminGetTopPages(token: string, days = 28) {
  return apiFetch<PageStat[]>(`/api/admin/analytics/top-pages?days=${days}`, { headers: adminHeaders(token) });
}

export function adminGetContactMessages(token: string) {
  return apiFetch<ContactMessage[]>(`/api/admin/contact-messages`, { headers: adminHeaders(token) });
}

export function adminMarkContactMessageRead(token: string, id: number) {
  return apiFetch<ContactMessage>(`/api/admin/contact-messages/${id}/read`, {
    method: "POST",
    headers: adminHeaders(token),
  });
}

export function adminGetLogs(token: string) {
  return apiFetch<ErrorLog[]>(`/api/admin/logs`, { headers: adminHeaders(token) });
}

export async function adminImportCsv(token: string, file: File): Promise<CsvImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_URL}/api/admin/import/csv`, {
    method: "POST",
    headers: adminHeaders(token),
    body: formData,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text().catch(() => res.statusText));
  }
  return res.json();
}

export function adminRunUpdate(token: string) {
  return apiFetch<{ products_checked: number; ai_regenerated: number }>(`/api/admin/run-update`, {
    method: "POST",
    headers: adminHeaders(token),
  });
}

export function adminFetchRakuten(token: string) {
  return apiFetch<{
    prices_updated: number;
    prices_skipped: number;
    products_discovered: number;
    candidates_considered: number;
    products_checked: number;
    ai_regenerated: number;
  }>(`/api/admin/fetch-rakuten`, {
    method: "POST",
    headers: adminHeaders(token),
  });
}

export async function verifyAdminToken(token: string): Promise<boolean> {
  try {
    await adminListProducts(token);
    return true;
  } catch {
    return false;
  }
}
