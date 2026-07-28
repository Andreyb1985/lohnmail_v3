"use client";

import { useState } from "react";
import { Monitor } from "./icons";

const views = [
  {
    label: "Übersicht",
    image: "/dashboard-current.jpg",
    mobileImage: "/dashboard-mobile.jpg",
    alt: "LohnMail Dashboard mit Status des aktuellen Monatslaufs",
    title: "Der Monatslauf auf einen Blick",
    text: "Mitarbeitende, versendete Abrechnungen, fehlende E-Mail-Adressen und Systemstatus sind sofort sichtbar.",
  },
  {
    label: "Prüfung",
    image: "/pruefung-current.jpg",
    mobileImage: "/pruefung-mobile.jpg",
    alt: "Prüfübersicht mit Fehlern und Warnungen in LohnMail",
    title: "Fehler erkennen, bevor sie teuer werden",
    text: "Kritische Fehler, Warnungen und Hinweise werden gesammelt dargestellt und lassen sich gezielt bearbeiten.",
  },
  {
    label: "Berichte",
    image: "/berichte-current.jpg",
    mobileImage: "/berichte-mobile.jpg",
    alt: "Berichtsansicht mit Versandstatus und Monatsdaten in LohnMail",
    title: "Jeder Lauf bleibt nachvollziehbar",
    text: "Versandstatus, offene Fälle und Exporte stehen für interne Kontrolle und spätere Rückfragen bereit.",
  },
];

function MobileSoftwarePreview({
  active,
  alt,
}: {
  active: number;
  alt: string;
}) {
  if (active === 0) {
    return (
      <div className="software-mobile-preview dashboard-mobile-preview" role="img" aria-label={alt}>
        <div className="dashboard-mobile-title" />
        <div className="software-mobile-kpis dashboard-mobile-kpis">
          <div className="software-mobile-crop dashboard-mobile-kpi-1" />
          <div className="software-mobile-crop dashboard-mobile-kpi-2" />
          <div className="software-mobile-crop dashboard-mobile-kpi-3" />
          <div className="software-mobile-crop dashboard-mobile-kpi-4" />
        </div>
        <div className="software-mobile-crop dashboard-mobile-status" />
      </div>
    );
  }

  if (active === 1) {
    return (
      <div className="software-mobile-preview pruefung-mobile-preview" role="img" aria-label={alt}>
        <div className="pruefung-mobile-title" />
        <div className="software-mobile-kpis pruefung-mobile-kpis">
          <div className="software-mobile-crop pruefung-mobile-kpi-1" />
          <div className="software-mobile-crop pruefung-mobile-kpi-2" />
          <div className="software-mobile-crop pruefung-mobile-kpi-3" />
          <div className="software-mobile-crop pruefung-mobile-kpi-4" />
        </div>
        <div className="software-mobile-crop pruefung-mobile-filters" />
        <div className="software-mobile-crop pruefung-mobile-table" />
      </div>
    );
  }

  return (
    <div className="software-mobile-preview berichte-mobile-preview" role="img" aria-label={alt}>
      <div className="berichte-mobile-title" />
      <div className="software-mobile-kpis berichte-mobile-kpis">
        <div className="software-mobile-crop berichte-mobile-kpi-1" />
        <div className="software-mobile-crop berichte-mobile-kpi-2" />
        <div className="software-mobile-crop berichte-mobile-kpi-4" />
        <div className="software-mobile-crop berichte-mobile-kpi-5" />
      </div>
      <div className="berichte-mobile-files">
        <div className="software-mobile-crop berichte-mobile-file-1" />
        <div className="software-mobile-crop berichte-mobile-file-2" />
      </div>
      <div className="software-mobile-crop berichte-mobile-chart" />
    </div>
  );
}

export default function SoftwareShowcase() {
  const [active, setActive] = useState(0);
  const view = views[active];

  return (
    <section className="section section-alt software-section" id="software" aria-labelledby="software-title">
      <div className="container center">
        <span className="eyebrow"><Monitor size={14} /> Die Software</span>
        <h2 className="section-title" id="software-title">Alles im Blick, bevor Sie auf Senden klicken</h2>
        <p className="section-lead">Klare Statusanzeigen statt verstreuter Listen und manueller Zwischenkontrollen.</p>

        <div className="software-tabs" role="tablist" aria-label="Ansichten der LohnMail Software">
          {views.map((item, index) => (
            <button
              key={item.label}
              type="button"
              role="tab"
              aria-selected={active === index}
              aria-controls="software-view"
              className={active === index ? "active" : ""}
              onClick={() => setActive(index)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div
          className="software-frame software-mobile-composite-frame"
          id="software-view"
          role="tabpanel"
        >
          <MobileSoftwarePreview active={active} alt={view.alt} />

          <picture className="software-desktop-picture">
            <source media="(max-width: 720px)" srcSet={view.mobileImage} />
            <img src={view.image} alt={view.alt} width="1440" height="900" />
          </picture>
        </div>

        <div className="software-caption" aria-live="polite">
          <h3>{view.title}</h3>
          <p>{view.text}</p>
        </div>
      </div>
    </section>
  );
}
