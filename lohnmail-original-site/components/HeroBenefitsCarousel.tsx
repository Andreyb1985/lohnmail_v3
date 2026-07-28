"use client";

import { useEffect, useState } from "react";
import { Building, CheckCircle, Clock, Shield } from "./icons";

const slides = [
  {
    label: "Zeit",
    kicker: "Weniger manuelle Arbeit",
    title: "Zeit sparen. Fehler reduzieren.",
    text: "PDF importieren, Personalnummern zuordnen, Dokumente trennen, prüfen und versenden – in einem klaren Monatslauf.",
  },
  {
    label: "Sicherheit",
    kicker: "Sensible Daten im Griff",
    title: "Lokal. Sicher. Nachvollziehbar.",
    text: "Ihre Lohndaten bleiben in Ihrer Arbeitsumgebung. Warnungen werden vor dem Versand sichtbar und alle Schritte dokumentiert.",
  },
  {
    label: "Mandanten",
    kicker: "Ohne Mandantenlimit",
    title: "Beliebig viele Unternehmen verwalten.",
    text: "Nutzen Sie LohnMail für so viele Unternehmen und Mandanten, wie Ihre Lohnbuchhaltung betreut – ohne zusätzliche Begrenzung.",
  },
];

export default function HeroBenefitsCarousel() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (reducedMotion.matches) return;

    const timer = window.setInterval(() => {
      setActive((current) => (current + 1) % slides.length);
    }, 6500);

    return () => window.clearInterval(timer);
  }, []);

  const slide = slides[active];

  return (
    <div className={`hero-benefits hero-benefits-${active + 1}`} aria-label="Die wichtigsten Vorteile von LohnMail">
      <div className="hero-benefits-tabs" role="tablist" aria-label="Vorteil auswählen">
        {slides.map((item, index) => (
          <button
            key={item.label}
            type="button"
            role="tab"
            aria-selected={active === index}
            aria-controls="hero-benefit-panel"
            className={active === index ? "active" : ""}
            onClick={() => setActive(index)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="hero-benefit-panel" id="hero-benefit-panel" role="tabpanel">
        <div className="hero-benefit-copy">
          <span className="hero-benefit-kicker">{slide.kicker}</span>
          <h2>{slide.title}</h2>
          <p>{slide.text}</p>
        </div>

        {active === 0 && (
          <div className="hero-process" aria-label="Automatisierter Ablauf">
            <span><Clock size={17} /><b>Import</b><small>PDF &amp; Excel</small></span>
            <span><CheckCircle size={17} /><b>Zuordnung</b><small>automatisch</small></span>
            <span><CheckCircle size={17} /><b>Versand</b><small>kontrolliert</small></span>
            <span><CheckCircle size={17} /><b>Bericht</b><small>vollständig</small></span>
          </div>
        )}

        {active === 1 && (
          <div className="hero-security-points">
            <strong><Shield size={26} /> LOKAL</strong>
            <span><CheckCircle size={16} /> Keine unnötige Cloud-Abhängigkeit</span>
            <span><CheckCircle size={16} /> Prüfung vor dem Versand</span>
            <span><CheckCircle size={16} /> Vollständige Protokolle</span>
          </div>
        )}

        {active === 2 && (
          <div className="hero-company-list">
            <span><Building size={17} /><b>Unternehmen Nord</b><small>bereit</small></span>
            <span><Building size={17} /><b>Unternehmen Mitte</b><small>bereit</small></span>
            <span className="unlimited"><b>+</b><strong>Weitere Mandanten</strong><small>ohne Limit</small></span>
          </div>
        )}
      </div>

      <div className="hero-benefits-footer">
        <button type="button" aria-label="Vorheriger Vorteil" onClick={() => setActive((active - 1 + slides.length) % slides.length)}>←</button>
        <span>{String(active + 1).padStart(2, "0")} / 03</span>
        <button type="button" aria-label="Nächster Vorteil" onClick={() => setActive((active + 1) % slides.length)}>→</button>
      </div>
    </div>
  );
}
