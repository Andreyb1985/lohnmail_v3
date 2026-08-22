import type { Metadata } from "next";
import { Inter, Archivo } from "next/font/google";
import Script from "next/script";
import SiteShell from "@/components/SiteShell";
import "./globals.css";

const GTM_ID = "GTM-PM4HMG2G";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const archivo = Archivo({
  subsets: ["latin"],
  variable: "--font-archivo",
  display: "swap",
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "LohnMail – Lohnabrechnungen automatisch und sicher per E-Mail versenden",
  description:
    "LohnMail automatisiert den Versand von Lohnabrechnungen: PDF-Import, Excel-Abgleich, Personalnummer-Erkennung, Verschlüsselung, E-Mail-Versand und Berichte. 2 Monate kostenlos testen.",
  keywords: [
    "Lohnabrechnung per E-Mail versenden",
    "Lohnabrechnungen digital versenden",
    "Lohnbuchhaltung Software",
    "Payroll Software Deutschland",
    "Lohnabrechnung PDF automatisch trennen",
    "Lohnabrechnung verschlüsselt versenden",
    "Digitale Lohnabrechnung",
    "HR Software Lohnabrechnung",
    "Lohnabrechnungen papierlos versenden",
    "Lohnabrechnung automatisieren",
  ],
  openGraph: {
    title: "LohnMail – Lohnabrechnungen automatisch, sicher und papierlos versenden",
    description:
      "LohnMail automatisiert den Versand Ihrer Lohnabrechnungen — vom PDF-Import bis zum verschlüsselten E-Mail-Versand. 2 Monate kostenlos testen.",
    locale: "de_DE",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de" className={`${inter.variable} ${archivo.variable}`}>
      <head>
        <Script id="google-tag-manager" strategy="afterInteractive">
          {`(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','${GTM_ID}');`}
        </Script>
      </head>
      <body>
        <noscript>
          <iframe
            src={`https://www.googletagmanager.com/ns.html?id=${GTM_ID}`}
            height="0"
            width="0"
            style={{ display: "none", visibility: "hidden" }}
            title="Google Tag Manager"
          />
        </noscript>
        <SiteShell>{children}</SiteShell>
      </body>
    </html>
  );
}
