import type { Metadata } from "next";
import { geistMono, geistSans } from "./fonts";
import "./globals.css";
import { QueryProvider } from "@/components/QueryProvider";
import { ChallengeProvider } from "@/lib/auth/challenge-context";

export const metadata: Metadata = {
  title: "Virtual Closet — NikaCommerce",
  description: "Transforma fotos planas de prendas en catálogos profesionales con IA",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <QueryProvider>
          <ChallengeProvider>{children}</ChallengeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
