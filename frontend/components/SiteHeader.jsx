"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Logo from "./Logo";

const NAV = [
  { href: "/#start", label: "Analyze a repo", short: "Analyze", match: (p) => p === "/" },
  { href: "/reports", label: "My reports", short: "Reports", match: (p) => p.startsWith("/reports") },
];

export default function SiteHeader() {
  const pathname = usePathname() || "/";
  return (
    <header className="border-b border-rule">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5 text-ink">
          <Logo />
          <span className="font-display text-xl font-semibold tracking-tight">CodeAtlas</span>
        </Link>
        <nav aria-label="Main" className="flex items-center gap-1 text-sm">
          {NAV.map((item) => {
            const active = item.match(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`whitespace-nowrap rounded-md px-2.5 py-2 transition-colors sm:px-3 ${
                  active ? "text-ink font-medium" : "text-muted hover:text-ink"
                }`}
              >
                <span className="sm:hidden">{item.short}</span>
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}