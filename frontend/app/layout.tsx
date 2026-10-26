import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gemelo digital agricola - Moche y Chavimochic",
  description:
    "Plataforma de modelado de paisaje, red de polinizadores y optimizacion bajo cambio climatico.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
