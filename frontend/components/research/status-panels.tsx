"use client";

import { Clock, Coffee, RotateCcw, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { KeyInput } from "@/components/key-input";
import { cn } from "@/lib/cn";

function useNow(active: boolean) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [active]);
  return now;
}

function Panel({
  icon: Icon,
  tone = "neutral",
  title,
  children,
}: {
  icon: typeof Clock;
  tone?: "neutral" | "warn";
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      role="status"
      className={cn(
        "rounded-md border p-5 sm:p-6",
        tone === "warn" ? "border-partial/50 bg-partial-soft/40" : "border-rule bg-paper-raised",
      )}
    >
      <div className="flex items-start gap-3">
        <Icon aria-hidden className={cn("mt-1 size-5 shrink-0", tone === "warn" ? "text-partial" : "text-ink-muted")} />
        <div className="min-w-0 flex-1 space-y-3">
          <h2 className="font-serif text-xl leading-snug">{title}</h2>
          {children}
        </div>
      </div>
    </div>
  );
}

function RetryButton({ onClick, disabled, label = "Try again" }: { onClick: () => void; disabled?: boolean; label?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 rounded-md border border-rule-strong px-3 py-1.5 font-sans text-sm text-ink hover:bg-paper-sunken disabled:cursor-not-allowed disabled:opacity-50"
    >
      <RotateCcw aria-hidden className="size-3.5" />
      {label}
    </button>
  );
}

export function WarmingPanel({ since, demoHref }: { since: number; demoHref: string }) {
  const seconds = Math.floor((useNow(true) - since) / 1000);
  return (
    <Panel icon={Coffee} title="Warming up the research engine…">
      <p className="font-serif text-ink-muted">
        The backend runs on a free server that sleeps when nobody is using it. Waking it usually takes
        under a minute; your question will start by itself.
      </p>
      <div className="flex flex-wrap items-center gap-4">
        <span className="font-mono text-xs text-ink-faint tabular-nums">waiting {seconds}s</span>
        <Link href={demoHref} className="font-mono text-xs">
          Watch a recorded demo instead
        </Link>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-paper-sunken" aria-hidden>
        <div className="h-full w-1/3 animate-[warm_1.6s_ease-in-out_infinite] rounded-full bg-accent/60 motion-reduce:animate-none" />
      </div>
    </Panel>
  );
}

export function RateLimitedPanel({ retryAt, message, onRetry }: { retryAt: number; message: string; onRetry: () => void }) {
  const left = Math.max(0, Math.ceil((retryAt - useNow(true)) / 1000));
  const minutes = Math.floor(left / 60);
  return (
    <Panel icon={Clock} title="You've reached the free question limit.">
      <p className="font-serif text-ink-muted">{message}</p>
      <p className="font-mono text-xs text-ink-faint tabular-nums">
        next free question in {minutes > 0 ? `${minutes} min ` : ""}
        {left % 60}s
      </p>
      <KeyInput onSaved={onRetry} />
      <RetryButton onClick={onRetry} disabled={left > 0} />
    </Panel>
  );
}

export function FailedPanel({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Panel icon={TriangleAlert} tone="warn" title="The research didn't finish.">
      <p className="font-serif text-ink-muted">{message}</p>
      <RetryButton onClick={onRetry} />
    </Panel>
  );
}

export function PipelineErrorPanel({
  code,
  message,
  onRetry,
}: {
  code: string;
  message: string;
  onRetry: () => void;
}) {
  const title =
    code === "quota"
      ? "Today's free model quota is used up."
      : code === "unavailable"
        ? "The model service is busy right now."
        : "Something went wrong.";
  return (
    <Panel icon={TriangleAlert} tone="warn" title={title}>
      <p className="font-serif text-ink-muted">{message}</p>
      {code === "quota" && <KeyInput onSaved={onRetry} />}
      <RetryButton onClick={onRetry} />
    </Panel>
  );
}
