import {
  Check,
  Contrast,
  LoaderCircle,
  Minus,
  PencilLine,
  X,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/cn";
import type { ClaimState } from "@/lib/research";

// Every state has an icon and a word, so it never relies on colour alone.
export const STATE_META: Record<
  ClaimState,
  { label: string; icon: LucideIcon; text: string; soft: string; border: string }
> = {
  verifying: {
    label: "Checking",
    icon: LoaderCircle,
    text: "text-ink-faint",
    soft: "bg-paper-sunken",
    border: "border-rule",
  },
  supported: {
    label: "Supported",
    icon: Check,
    text: "text-supported",
    soft: "bg-supported-soft",
    border: "border-supported/50",
  },
  partial: {
    label: "Partial",
    icon: Contrast,
    text: "text-partial",
    soft: "bg-partial-soft",
    border: "border-partial/50",
  },
  unsupported: {
    label: "Unsupported",
    icon: X,
    text: "text-unsupported",
    soft: "bg-unsupported-soft",
    border: "border-unsupported/50",
  },
  rewritten: {
    label: "Revised",
    icon: PencilLine,
    text: "text-supported",
    soft: "bg-supported-soft",
    border: "border-supported/50",
  },
  removed: {
    label: "Removed",
    icon: Minus,
    text: "text-unsupported",
    soft: "bg-unsupported-soft",
    border: "border-unsupported/50",
  },
};

export function VerdictTag({ state, className }: { state: ClaimState; className?: string }) {
  const meta = STATE_META[state];
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 font-mono text-[0.6875rem] leading-none tracking-wide uppercase",
        meta.text,
        meta.soft,
        meta.border,
        className,
      )}
    >
      <Icon
        aria-hidden
        className={cn("size-3", state === "verifying" && "animate-spin motion-reduce:animate-none")}
        strokeWidth={2.25}
      />
      {meta.label}
    </span>
  );
}
