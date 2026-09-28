const LINKS = [
  { href: "https://github.com/Narwinh/citecheck", label: "Source on GitHub" },
  { href: "https://narwinh.github.io", label: "Portfolio" },
];

export function SiteFooter() {
  return (
    <footer className="relative z-10 border-t border-rule">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-6 sm:px-8">
        <p className="font-serif text-sm text-ink-muted">
          CiteCheck, by Naveen. Every number on this site comes from a committed eval run.
        </p>
        <ul className="ml-auto flex gap-5 font-mono text-[0.72rem]">
          {LINKS.map((l) => (
            <li key={l.href}>
              <a href={l.href} target="_blank" rel="noreferrer">
                {l.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </footer>
  );
}
