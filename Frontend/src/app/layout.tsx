import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Livguard Quotation Management System",
  description: "Enterprise quotation, payment verification, and order confirmation platform for Livguard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 antialiased">{children}</body>
    </html>
  );
}
