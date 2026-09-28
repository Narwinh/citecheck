import type { Metadata } from "next";

export const metadata: Metadata = { title: "Mock stream", robots: { index: false } };

export default function Layout({ children }: LayoutProps<"/dev/mock">) {
  return children;
}
