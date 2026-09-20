"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import AdminLoginForm from "@/components/AdminLoginForm";
import { AdminAuthProvider, useAdminAuth } from "@/lib/adminAuth";

function AdminShell({ children }: { children: React.ReactNode }) {
  const { status, logout } = useAdminAuth();
  const pathname = usePathname();

  if (status === "checking") {
    return <p className="text-sm text-zinc-500">確認中...</p>;
  }

  if (status === "unauthenticated") {
    return <AdminLoginForm />;
  }

  const links = [
    { href: "/admin", label: "ダッシュボード" },
    { href: "/admin/products", label: "商品管理" },
    { href: "/admin/logs", label: "エラーログ" },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-200 pb-4 dark:border-zinc-800">
        <nav className="flex gap-4 text-sm">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={
                pathname === link.href
                  ? "font-semibold text-zinc-900 dark:text-white"
                  : "text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
              }
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <button onClick={logout} className="text-sm text-zinc-500 hover:text-red-600">
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
