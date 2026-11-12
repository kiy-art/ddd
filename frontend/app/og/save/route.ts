// "Save this card to the iPhone photo library" page for the 社長's X posting
// routine (2026-11-12). The dashboard that lists the post drafts runs inside
// an embedded view where iOS blocks both the share sheet and long-press
// save, so its button opens this page in Safari instead: a real top-level
// page on our own origin, where navigator.share({files}) works.
//
// GET /og/save?src=/products/<slug>/opengraph-image
// `src` must be one of this site's own share-image paths - nothing else is
// ever fetched or shown.

const ALLOWED = /^\/(opengraph-image|og\/popular|products\/[^/?#]+\/opengraph-image|category\/[^/?#]+\/opengraph-image|guides\/[^/?#]+\/opengraph-image)(\?[A-Za-z0-9=&_%.-]*)?$/;

export async function GET(request: Request) {
  const src = new URL(request.url).searchParams.get("src") ?? "";
  if (!ALLOWED.test(src)) {
    return new Response("not found", { status: 404, headers: { "X-Robots-Tag": "noindex, nofollow" } });
  }
  // JSON.stringify + "<" escaping: safe to inline in a <script>.
  const srcJs = JSON.stringify(src).replace(/</g, "\\u003c");
  const html = `<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>画像を保存 | PAR.</title>
<style>
  body { margin: 0; background: #0B100D; color: #fff; font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif; }
  main { max-width: 34rem; margin: 0 auto; padding: 20px 16px 40px; }
  img { display: block; width: 100%; height: auto; border-radius: 12px; -webkit-touch-callout: default; }
  button { display: block; width: 100%; margin: 18px 0 10px; min-height: 60px; border: 0; border-radius: 999px; background: #FFE600; color: #0B100D; font-size: 20px; font-weight: 800; }
  button:disabled { opacity: 0.5; }
  p { color: #A7B3AD; font-size: 14px; line-height: 1.7; margin: 8px 0; }
  #msg { color: #fff; font-size: 16px; min-height: 1.7em; }
</style>
</head>
<body>
<main>
  <img id="pic" alt="Xの投稿に添付する画像">
  <button id="save" disabled>読み込み中…</button>
  <p id="msg"></p>
  <p>ボタンを押すとメニューが開くので、「画像を保存」を選んでください。写真アプリに入ります。</p>
  <p>メニューが開かないときは、上の画像を長押しして「“写真”に保存」を選んでください。</p>
</main>
<script>
(function () {
  var src = ${srcJs};
  var pic = document.getElementById("pic");
  var btn = document.getElementById("save");
  var msg = document.getElementById("msg");
  var file = null;
  pic.src = src;
  fetch(src).then(function (r) { if (!r.ok) throw new Error("load"); return r.blob(); }).then(function (blob) {
    file = new File([blob], "par-card.png", { type: "image/png" });
    btn.disabled = false;
    btn.textContent = "写真に保存する";
  }).catch(function () {
    btn.textContent = "画像を長押しして保存";
    msg.textContent = "ボタンが使えないため、画像を長押ししてください。";
  });
  btn.addEventListener("click", function () {
    if (!file) return;
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      navigator.share({ files: [file] }).then(function () {
        msg.textContent = "保存できたら、Xに戻って画像を添付してください。";
      }).catch(function (e) {
        if (e && e.name === "AbortError") return;
        msg.textContent = "メニューを開けませんでした。画像を長押しして保存してください。";
      });
    } else {
      var a = document.createElement("a");
      a.href = URL.createObjectURL(file);
      a.download = "par-card.png";
      a.click();
      msg.textContent = "保存されないときは、画像を長押しして保存してください。";
    }
  });
})();
</script>
</body>
</html>`;
  return new Response(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "X-Robots-Tag": "noindex, nofollow",
      "Cache-Control": "no-store",
    },
  });
}
