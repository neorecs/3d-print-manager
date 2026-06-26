import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "3D Print Manager",
  description: "Centrale beheerlaag voor 3D-printactiviteiten",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="nl">
      <body>{children}</body>
    </html>
  );
}
