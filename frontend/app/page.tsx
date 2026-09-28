import Link from "next/link";

import { ThemeToggle } from "@/components/theme-toggle";

// Placeholder until the landing page is built in Stage 10.
export default function Home() {
  return (
    <main className="relative z-10 mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
      <div className="flex items-center justify-between">
        <p className="kicker">CiteCheck</p>
        <ThemeToggle />
      </div>
      <h1 className="mt-6 font-serif text-5xl leading-[1.05] font-light tracking-tight sm:text-6xl">
        Answers you can <em className="font-normal">check.</em>
      </h1>
      <p className="mt-4 max-w-xl font-serif text-lg text-ink-muted">
        The interface is being built. For now, the design system lives in the sandbox.
      </p>
      <ul className="mt-8 space-y-2 font-mono text-sm">
        <li>
          <Link href="/dev/components">/dev/components</Link>
        </li>
        <li>
          <Link href="/dev/mock">/dev/mock</Link>
        </li>
      </ul>
    </main>
  );
}
