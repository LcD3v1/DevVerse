import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DevVerse System",
  description: "Dashboard do ecossistema DevVerse para estudos, XP, IA e tarefas."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
