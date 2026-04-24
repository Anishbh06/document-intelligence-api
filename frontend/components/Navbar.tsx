"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearAuth, getToken } from "@/lib/auth";
import { useEffect, useState } from "react";


const NAV_LINKS = [
  { href: "/", label: "Upload" },
  { href: "/documents", label: "Documents" },
];

export default function Navbar() {
  const pathname = usePathname();
  const [loggedIn, setLoggedIn] = useState(false);


  useEffect(() => {
    setLoggedIn(Boolean(getToken()));
  }, [pathname]); // re-check on every route change

  const handleLogout = () => {
    clearAuth();
    setLoggedIn(false);
    // Use hard navigation to guarantee redirect — router.push can lose a
    // race against AuthGuard returning null during the same render cycle.
    window.location.replace("/login");
  };


  return (
    <nav className="mb-6 flex items-center justify-between rounded-2xl bg-white px-6 py-4 shadow-soft">
      <Link href="/" className="text-lg font-bold tracking-tight text-slate-900">
        📄 Doc Intelligence
      </Link>

      <div className="flex items-center gap-1">
        {loggedIn &&
          NAV_LINKS.map((link) => {
            const isActive =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {link.label}
              </Link>
            );
          })}

        {loggedIn ? (
          <button
            onClick={handleLogout}
            className="ml-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
          >
            Sign out
          </button>
        ) : (
          <Link
            href="/login"
            className="ml-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
          >
            Sign in
          </Link>
        )}
      </div>
    </nav>
  );
}
