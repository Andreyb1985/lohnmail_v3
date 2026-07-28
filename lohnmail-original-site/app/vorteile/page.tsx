import Link from "next/link";
import {
  BarChart,
  Check,
  CheckCircle,
  Clock,
  Euro,
  Leaf,
  Monitor,
  Search,
  Shield,
  Users,
  X,
  Zap,
} from "@/components/icons";

const benefits = [
  {
    icon: Clock,
    title: "Zeitersparnis",
    text: "Weniger manuelle Arbeit bei der monatlichen Verarbeitung und Verteilung.",
  },
  {
    icon: CheckCircle,
    title: "Weniger Fehler",
    text: "Automatische Zuordnung reduziert das Risiko falscher Empfänger.",
  },
  {
    icon: Shield,
    title: "Mehr Sicherheit",
    text: "Sensible Dokumente strukturiert verarbeiten und verschlüsselt versenden.",
  },
  {
    icon: Search,
    title: "Bessere Nachvollziehbarkeit",
    text: "Berichte und Protokolle schaffen Transparenz für offene Fälle.",
  },
  {
    icon: Euro,
    title: "Geringere Kosten",
    text: "Weniger Papier, Umschläge, Druck und manuelle Arbeitszeit.",
  },
  {
    icon: Zap,
    title: "Schnellere Prozesse",
    text: "Den monatlichen Versand deutlich schneller abschließen.",
  },
  {
    icon: Users,
    title: "Praxisnah entwickelt",
    text: "Aus realen Payroll-Prozessen heraus entwickelt und optimiert.",
  },
  {
    icon: Monitor,
    title: "Lokale Kontrolle",
    text: "Die Verarbeitung bleibt in der Arbeitsumgebung des Unternehmens.",
  },
];

const sustainable = [
  "Weniger Papierverbrauch",
  "Weniger Druckaufwand",
  "Weniger Toner und Umschläge",
  "Weniger physische Ablage",
  "Weniger interne Verteilungswege",
  "Ein regelmäßiger Beitrag zum Umweltschutz",
];

const manualSteps = [
  "500 Abrechnungen drucken",
  "500 Dokumente sortieren",
  "500 Umschläge vorbereiten",
  "500 Abrechnungen verteilen",
  "Fehlende Dokumente nachverfolgen",
];

const digitalSteps = [
  "PDF und Excel-Liste importieren",
  "Automatische Zuordnung und Trennung",
  "Prüfung vor dem Versand",
  "Verschlüsselter E-Mail-Versand",
  "Vollständiges Versandprotokoll",
];

export default function BenefitsPage() {
  return (
    <>
      <section className="page-intro">
        <div className="container">
          <span className="eyebrow">
            <BarChart size={14} /> Vorteile
          </span>
          <h1>Jeden Monat weniger Aufwand und mehr Kontrolle.</h1>
          <p>
            LohnMail spart wiederkehrende Arbeit, reduziert Fehlerquellen und macht
            den gesamten Versand nachvollziehbar.
          </p>
        </div>
      </section>

      <section className="section page-section">
        <div className="container">
          <div className="benefits-grid">
            {benefits.map((benefit) => {
              const Icon = benefit.icon;
              return (
                <article className="benefit" key={benefit.title}>
                  <h2>
                    <Icon size={19} />
                    {benefit.title}
                  </h2>
                  <p>{benefit.text}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="section sustain page-section">
        <div className="container sustainability-layout">
          <div>
            <span className="eyebrow">
              <Leaf size={14} /> Nachhaltigkeit
            </span>
            <h2 className="section-title">
              Weniger Papier. Weniger Umschläge. Mehr Verantwortung.
            </h2>
            <p className="section-lead">
              Jede digital versendete Lohnabrechnung reduziert Papierverbrauch,
              Druckaufwand, Toner, Umschläge und interne Verteilungswege.
            </p>
          </div>
          <div className="sustain-grid">
            {sustainable.map((item) => (
              <div className="sustain-item" key={item}>
                <Leaf size={17} />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section page-section">
        <div className="container">
          <span className="eyebrow">
            <Clock size={14} /> Rechenbeispiel
          </span>
          <h2 className="section-title">500 Mitarbeitende. Zwei sehr unterschiedliche Abläufe.</h2>
          <p className="section-lead">
            Je größer das Unternehmen, desto stärker macht sich die Automatisierung bemerkbar.
          </p>

          <div className="savings-grid">
            <div className="savings-col manual">
              <h3>Manueller Prozess · jeden Monat</h3>
              <ul>
                {manualSteps.map((step) => (
                  <li key={step}>
                    <X size={16} />
                    {step}
                  </li>
                ))}
              </ul>
            </div>
            <div className="savings-col digital">
              <h3>Mit LohnMail · jeden Monat</h3>
              <ul>
                {digitalSteps.map((step) => (
                  <li key={step}>
                    <Check size={16} />
                    {step}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="section-action">
            <Link className="btn btn-primary" href="/testzugang">
              Kostenlos testen
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
