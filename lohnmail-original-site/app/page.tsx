import Link from "next/link";
import HeroBenefitsCarousel from "@/components/HeroBenefitsCarousel";
import {
  BarChart,
  CheckCircle,
  Clock,
  Mail,
  Monitor,
  Shield,
} from "@/components/icons";

const overviewLinks = [
  {
    href: "/so-funktioniert-es",
    icon: Clock,
    number: "01",
    title: "Ein klarer Monatslauf",
    text: "Vom Sammel-PDF über die Prüfung bis zum dokumentierten Versand.",
  },
  {
    href: "/software",
    icon: Monitor,
    number: "02",
    title: "Vor dem Versand prüfen",
    text: "Fehlende Daten, Warnungen und offene Fälle rechtzeitig erkennen.",
  },
  {
    href: "/sicherheit",
    icon: Shield,
    number: "03",
    title: "Lokal und nachvollziehbar",
    text: "Sensible Lohndaten bleiben in Ihrer kontrollierten Arbeitsumgebung.",
  },
  {
    href: "/vorteile",
    icon: BarChart,
    number: "04",
    title: "Weniger Aufwand jeden Monat",
    text: "Zeit, Papier, Material und wiederkehrende manuelle Arbeit sparen.",
  },
];

export default function OverviewPage() {
  return (
    <>
      <section className="hero shell-hero">
        <div className="container hero-grid">
          <div>
            <span className="eyebrow">
              <Mail size={14} /> Digitaler Lohnabrechnungsversand
            </span>
            <h1>
              Lohnabrechnungen{" "}
              <span className="accent">sicher und papierlos</span> versenden
            </h1>
            <p className="hero-sub">
              Vom Sammel-PDF bis zum dokumentierten Versand: LohnMail ordnet, prüft,
              verschlüsselt und versendet Ihre Abrechnungen in einem klaren lokalen Workflow.
            </p>
            <div className="hero-actions">
              <Link href="/testzugang" className="btn btn-primary btn-lg">
                2 Monate kostenlos testen
              </Link>
              <Link href="/software" className="btn btn-secondary btn-lg">
                Software ansehen
              </Link>
            </div>
            <div className="hero-trust">
              <CheckCircle size={19} />
              <span>
                Bereits bei der <strong>GeSoB GmbH</strong> mit rund{" "}
                <strong>500 Mitarbeitenden</strong> im realen Payroll-Alltag eingesetzt.
              </span>
            </div>
          </div>

          <HeroBenefitsCarousel />
        </div>
      </section>

      <section className="home-facts" aria-label="LohnMail auf einen Blick">
        <div className="container home-facts-grid">
          <div>
            <strong>Lokale Verarbeitung</strong>
            <span>Daten bleiben in Ihrer Umgebung</span>
          </div>
          <div>
            <strong>Unbegrenzt viele Mandanten</strong>
            <span>Eine Anwendung, flexible Nutzung</span>
          </div>
          <div>
            <strong>Windows &amp; macOS</strong>
            <span>Für Ihre Arbeitsumgebung</span>
          </div>
          <div>
            <strong>40 € / Monat</strong>
            <span>Endpreis · 2 Monate kostenlos testen</span>
          </div>
        </div>
      </section>

      <section className="section overview-section">
        <div className="container">
          <div className="page-heading-row">
            <div>
              <span className="eyebrow">LohnMail im Überblick</span>
              <h2 className="section-title">Alles für einen kontrollierten digitalen Versand</h2>
            </div>
            <p className="section-lead">
              Entwickelt von einem Lohnbuchhalter, der den monatlichen Zeitdruck und die
              typischen Fehlerquellen selbst kennt.
            </p>
          </div>

          <div className="overview-links">
            {overviewLinks.map((item) => {
              const Icon = item.icon;
              return (
                <Link href={item.href} className="overview-link" key={item.href}>
                  <span className="overview-number">{item.number}</span>
                  <span className="overview-icon">
                    <Icon size={20} />
                  </span>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                  <span className="overview-arrow" aria-hidden="true">
                    →
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      </section>
    </>
  );
}
