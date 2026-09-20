"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { verifyAdminToken } from "@/lib/api";

const STORAGE_KEY = "golf_deals_admin_token";

interface AdminAuthValue {
  token: string | null;
  status: "checking" | "authenticated" | "unauthenticated";
  login: (token: string) => Promise<boolean>;
  logout: () => void;
}

const AdminAuthContext = createContext<AdminAuthValue | null>(null);

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<AdminAuthValue["status"]>("checking");

  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    if (!stored) {
      Promise.resolve().then(() => setStatus("unauthenticated"));
      return;
    }
    verifyAdminToken(stored).then((ok) => {
      if (ok) {
        setToken(stored);
        setStatus("authenticated");
      } else {
        localStorage.removeItem(STORAGE_KEY);
        setStatus("unauthenticated");
      }
    });
  }, []);

  const login = async (candidate: string) => {
    const ok = await verifyAdminToken(candidate);
    if (ok) {
      localStorage.setItem(STORAGE_KEY, candidate);
      setToken(candidate);
      setStatus("authenticated");
    }
    return ok;
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setStatus("unauthenticated");
  };

  return (
    <AdminAuthContext.Provider value={{ token, status, login, logout }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth(): AdminAuthValue {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) throw new Error("useAdminAuth must be used within AdminAuthProvider");
  return ctx;
}
