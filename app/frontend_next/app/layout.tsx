import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap", variable: "--font-inter" });

export const metadata: Metadata = {
  title: { default: "3D Print Manager", template: "%s · 3D Print Manager" },
  description: "Centrale beheerlaag voor 3D-printactiviteiten",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html className={inter.variable} lang="nl">
      <body>{children}</body>
    </html>
  );
}
