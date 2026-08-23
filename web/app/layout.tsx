import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AMR Navigation Simulator Web",
  description: "Browser-based AMR robotics simulator with a Python planning API."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><header className="topbar"><Link href="/" className="brand">AMR Navigation Simulator</Link><nav><Link href="/simulator">Simulator</Link><Link href="/editor">Editor</Link><Link href="/experiments">Experiments</Link><Link href="/results">Results</Link><Link href="/about">About</Link></nav></header>{children}</body></html>;
}