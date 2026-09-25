"use client";

import { useState } from "react";

import GolfMotif from "@/components/GolfMotif";

export default function Newsletter() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <section className="relative overflow-hidden border-t border-border bg-card px-6 py-20 sm:py-28">
      <GolfMotif
        variant="flag"
        className="pointer-events-none absolute -left-10 top-0 h-48 w-48 text-brand/[0.08] sm:h-64 sm:w-64"
      />
      <div className="relative mx-auto flex max-w-3xl flex-col items-center gap-6 text-center">
        <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Coming Soon</span>
        <h2 className="font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
          買い時が来たら、
          <br />
          通知を受け取る。
        </h2>
        <p className="max-w-md text-sm leading-relaxed text-foreground/60">
          メール通知機能は準備中です。先行登録いただくと、公開時に一番にお知らせします。
        </p>

        {submitted ? (
          <p className="rounded-full bg-brand/10 px-6 py-3 text-sm font-medium text-brand dark:text-brand-light">
            ありがとうございます。準備でき次第ご連絡します。
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="flex w-full max-w-sm flex-col gap-3 sm:flex-row">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="flex-1 rounded-full border border-border bg-background px-5 py-3 text-sm text-foreground placeholder:text-foreground/35 focus:border-brand focus:outline-none"
            />
            <button
              type="submit"
              className="rounded-full bg-brand px-6 py-3 text-sm font-semibold text-white transition-transform hover:scale-[1.03]"
            >
              先行登録
            </button>
          </form>
        )}
      </div>
    </section>
  );
}
