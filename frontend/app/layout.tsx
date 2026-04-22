import "./globals.css";
import type { Metadata } from "next";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Document Intelligence UI",
  description: "Upload, process, and chat with documents",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <main className="mx-auto min-h-screen w-full max-w-5xl px-4 py-8 md:px-6">
          <Navbar />
          {children}
        </main>
      </body>
    </html>
  );
}
