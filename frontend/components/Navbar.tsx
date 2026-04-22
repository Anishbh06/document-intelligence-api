"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/", label: "Upload" },
  { href: "/documents", label: "Documents" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="mb-6 flex items-center justify-between rounded-2xl bg-white px-6 py-4 shadow-soft">
      <Link
        href="/"
        className="text-lg font-bold tracking-tight text-slate-900"
      >
        📄 Doc Intelligence
      </Link>
      <div className="flex items-center gap-1">
        {NAV_LINKS.map((link) => {
          const isActive =
            link.href === "/"
              ? pathname === "/"
              : pathname.startsWith(link.href);
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
      </div>
    </nav>
  );
}
