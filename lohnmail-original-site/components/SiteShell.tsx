"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import BrandLogo from "./BrandLogo";
import {
  BarChart,
  ClipboardList,
  Euro,
  LayoutDashboard,
  Menu,
  Monitor,
  Send,
  Shield,
  Users,
  X,
  Zap,
} from "./icons";

const navigation = [
  { href: "/", label: "Übersicht", icon: LayoutDashboard },
  { href: "/so-funktioniert-es", label: "So funktioniert es", icon: Zap },
  { href: "/software", label: "Die Software", icon: Monitor },
  { href: "/funktionen", label: "Funktionen", icon: ClipboardList },
  { href: "/vorteile", label: "Vorteile", icon: BarChart },
  { href: "/sicherheit", label: "Sicherheit", icon: Shield },
  { href: "/aus-der-praxis", label: "Aus der Praxis", icon: Users },
  { href: "/preis", label: "Preis", icon: Euro },
];

const utilityTitles: Record<string, string> = {
  "/testzugang": "Testzugang",
  "/impressum": "Impressum",
  "/datenschutz": "Datenschutz",
  "/agb": "AGB",
  "/widerrufsbelehrung": "Widerruf",
  "/widerruf": "Vertrag widerrufen",
  "/kuendigen": "Vertrag kündigen",
};

export default function SiteShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const activePage =
    navigation.find((item) =>
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
    )?.label ?? utilityTitles[pathname] ?? "LohnMail";

  return (
    <div className={`site-shell${menuOpen ? " menu-open" : ""}`}>
      <aside className="site-sidebar" aria-label="Hauptnavigation">
        <Link className="sidebar-brand" href="/" aria-label="LohnMail Startseite">
          <BrandLogo />
        </Link>

        <nav className="sidebar-nav">
          <span className="sidebar-label">Website</span>
          {navigation.map((item) => {
            const Icon = item.icon;
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

            return (
              <Link
                className={`sidebar-link${active ? " active" : ""}`}
                href={item.href}
                key={item.href}
                aria-current={active ? "page" : undefined}
              >
                <Icon size={19} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-trial">
            <strong>2 Monate kostenlos</strong>
            <span>Zahlungsart erst zum Ende der Testphase wählen.</span>
          </div>
          <Link className="sidebar-test-button" href="/testzugang">
            <Send size={16} />
            Testzugang anfragen
          </Link>
        </div>
      </aside>

      <button
        className="sidebar-overlay"
        type="button"
        aria-label="Menü schließen"
        onClick={() => setMenuOpen(false)}
      />

      <div className="site-main">
        <header className="shell-topbar">
          <button
            className="shell-menu-button"
            type="button"
            aria-label={menuOpen ? "Menü schließen" : "Menü öffnen"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((current) => !current)}
          >
            {menuOpen ? <X size={21} /> : <Menu size={21} />}
          </button>

          <Link className="shell-mobile-brand" href="/">
            <BrandLogo />
          </Link>

          <div className="shell-page-title">
            <strong>{activePage}</strong>
            <span>Digitaler Lohnabrechnungsversand</span>
          </div>

          <div className="shell-actions">
            <a className="shell-email" href="mailto:support@lohn-mail.de">
              support@lohn-mail.de
            </a>
            <Link className="shell-test-link" href="/testzugang">
              Kostenlos testen
              <span aria-hidden="true">›</span>
            </Link>
          </div>
        </header>

        <main>{children}</main>

        <footer className="shell-footer">
          <div>
            <strong>LohnMail</strong>
            <span>Aus der Praxis der Lohnbuchhaltung entwickelt.</span>
          </div>
          <div className="shell-footer-links">
            <a href="mailto:support@lohn-mail.de">Kontakt</a>
            <Link href="/impressum">Impressum</Link>
            <Link href="/datenschutz">Datenschutz</Link>
            <Link href="/agb">AGB</Link>
            <Link href="/widerrufsbelehrung">Widerrufsbelehrung</Link>
            <Link className="legal-action-link" href="/widerruf">
              Vertrag widerrufen
            </Link>
            <Link className="legal-action-link" href="/kuendigen">
              Verträge hier kündigen
            </Link>
          </div>
        </footer>
      </div>
    </div>
  );
}
