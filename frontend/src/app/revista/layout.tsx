import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Catálogo Revista | Black Horse Talabartería",
  description:
    "Catálogo editorial de monturas y talabartería artesanal — Black Horse, Bolivia.",
};

export default function RevistaLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* eslint-disable-next-line @next/next/no-page-custom-font */}
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link
        href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,700;0,800;1,500&display=swap"
        rel="stylesheet"
      />
      {children}
    </>
  );
}
