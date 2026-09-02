import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { AuthProvider } from "@/lib/auth-context";
import { Providers } from "@/components/Providers";
import { AmbientBackdrop } from "@/components/backdrop";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "RecoveryOS — Autonomous Revenue Recovery",
  description:
    "Autonomous payment recovery powered by AI diagnosis, deterministic policy guardrails, and secure execution.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script src="https://checkout.razorpay.com/v1/checkout.js" async />
      </head>
      <body className="relative min-h-full transition-colors duration-300">
        <Providers>
          <AmbientBackdrop />
          <AuthProvider>
            <div className="relative z-10">{children}</div>
          </AuthProvider>
        </Providers>
      </body>
    </html>
  );
}
