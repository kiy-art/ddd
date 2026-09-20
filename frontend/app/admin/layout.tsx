"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import AdminLoginForm from "@/components/AdminLoginForm";
import { AdminAuthProvider, useAdminAuth } from "@/lib/adminAuth";

function AdminShell({ children }: { children: React.ReactNode }) {
  const { status, logout } = useAdminAuth();
  const pathname = usePathname();

  if (status === "checking") {
    return (
      <div className="mx-auto max-w-7xl px-6 py-16">
        <p className="text-sm text-foreground/50">確認中...</p>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return (
      <div className="mx-auto flex max-w-7xl items-center justify-center px-6 py-24">
        <AdminLoginForm />
      </div>
    );
  }

  const links = [
    { href: "/admin", label: "ダッシュボード" },
    { href: "/admin/products", label: "商品管理" },
    { href: "/admin/logs", label: "エラーログ" },
  ];

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-5">
        <nav className="flex gap-5 text-sm">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={
                pathname === link.href
                  ? "font-semibold text-foreground"
                  : "text-foreground/50 hover:text-foreground"
              }
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <button onClick={logout} className="text-sm text-foreground/50 hover:text-red-600">
          ログアウト
        </button>
      </div>
      {children}
    </div>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminShell>{children}</AdminShell>
    </AdminAuthProvider>
  );
}
