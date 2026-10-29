import TrackedCta from "@/components/TrackedCta";

/**
 * Approval #004 / DQ-19 (A, 2026-10-30): the one PR "partner offer" slot on
 * product pages, placed right after the shop comparison table.
 *
 * Offer: じゃらんゴルフ (ValueCommerce program 2121336, 定額700円税別 per
 * instant booking, paid after the round is played; request bookings don't
 * count). Rules from the program page (checked 2026-10-30):
 *  - "PR" shown on the slot itself; the page already carries the
 *    affiliate-ad notice near the top.
 *  - Link text is the advertiser's own material only (ad text 2661154) - no
 *    claims about points, prices or "No.1".
 *  - Must not look like the site is run by じゃらんゴルフ / Recruit.
 *  - The 1x1 gifbanner is the advertiser's impression counter (= N1 for
 *    this slot until a first-party impression count exists).
 * Clicks are recorded as shop "partner" (cta_type partner_offer), which
 * kpi.py keeps apart from the shop click rate.
 */
const JALAN_GOLF_HREF = "https://ck.jp.ap.valuecommerce.com/servlet/referral?sid=3782576&pid=892736410";
const JALAN_GOLF_IMP = "https://ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3782576&pid=892736410";

export default function PartnerOfferJalanGolf({
  productId,
  category,
}: {
  productId?: number;
  category?: string;
}) {
  return (
    <aside
      aria-label="広告"
      className="rounded-2xl border border-border bg-card px-5 py-4 sm:px-6"
    >
      <div className="flex items-center gap-2">
        <span className="rounded border border-foreground/30 px-1.5 py-0.5 text-[11px] font-semibold text-foreground/70">
          PR
        </span>
        <span className="text-xs text-foreground/60">クラブを選んだら、次はラウンドの予定も</span>
      </div>
      <TrackedCta
        href={JALAN_GOLF_HREF}
        target="_blank"
        rel="nofollow noopener noreferrer sponsored"
        event="partner_offer_click"
        params={{ cta_type: "partner_offer", partner: "jalan_golf", placement: "product_after_compare" }}
        productId={productId}
        category={category}
        placement="product_after_compare"
        shop="partner"
        className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-brand underline-offset-4 hover:underline"
      >
        じゃらんゴルフで人気のゴルフ場を予約する！
        <span aria-hidden="true">↗</span>
      </TrackedCta>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={JALAN_GOLF_IMP} width={1} height={1} alt="" className="block h-px w-px" />
      <p className="mt-1 text-[11px] text-foreground/50">
        外部サイト（じゃらんゴルフ）へ移動します。PAR.はじゃらんゴルフの運営元ではありません。
      </p>
    </aside>
  );
}
