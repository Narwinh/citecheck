import type { Metadata } from "next";

export const metadata: Metadata = { title: "Component sandbox", robots: { index: false } };

export default function Layout({ children }: LayoutProps<"/dev/components">) {
  return children;
}
