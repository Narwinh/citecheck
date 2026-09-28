import Link from "next/link";

import { ThemeToggle } from "./theme-toggle";

const NAV = [
  { href: "/", label: "Ask" },
  { href: "/eval", label: "Evaluation" },
  { href: "/about", label: "How it works" },
];

export function SiteHeader() {
  return (
    <header className="relative z-10 border-b border-rule">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 sm:px-8">
        <Link href="/" className="group flex items-baseline gap-2 text-ink no-underline">
          <span className="font-serif text-xl tracking-tight">CiteCheck</span>
          <span className="hidden font-mono text-[0.62rem] tracking-[0.12em] text-ink-faint uppercase sm:inline">
            verified research
          </span>
        </Link>
        <nav aria-label="Main" className="ml-auto flex items-center gap-4 sm:gap-6">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="font-mono text-[0.72rem] tracking-wide text-ink-muted no-underline hover:text-ink"
            >
              {item.label}
            </Link>
          ))}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
