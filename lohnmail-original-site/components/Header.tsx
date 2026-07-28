"use client";

import { useState } from "react";
import BrandLogo from "./BrandLogo";
import { Menu, X } from "./icons";

const links = [
  { href: "#funktionen", label: "Funktionen" },
  { href: "#praxis", label: "Aus der Praxis" },
  { href: "#sicherheit", label: "Sicherheit" },
  { href: "#preis", label: "Preis" },
  { href: "#kontakt", label: "Kontakt" },
];

export default function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header className="site-header">
      <div className="container header-inner">
        <a href="#top" className="logo" aria-label="LohnMail – Startseite">
          <BrandLogo />
        </a>

        <nav className={`main-nav${open ? " open" : ""}`} aria-label="Hauptnavigation">
          {links.map((l) => (
            <a key={l.href} href={l.href} onClick={() => setOpen(false)}>
              {l.label}
            </a>
          ))}
        </nav>

        <div className="header-cta">
          <a href="#kontakt" className="btn btn-primary" style={{ padding: "10px 20px", fontSize: 15 }}>
            Kostenlos testen
          </a>
          <button
            className="nav-toggle"
            aria-label={open ? "Menü schließen" : "Menü öffnen"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
    </header>
  );
}
