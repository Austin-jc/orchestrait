import "./globals.css";
import "reactflow/dist/style.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Orchestrait",
  description: "Local-first multi-model orchestrator",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
