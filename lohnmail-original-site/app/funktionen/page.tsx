import Link from "next/link";
import {
  AlertTriangle,
  BarChart,
  ClipboardList,
  FileText,
  Hash,
  Key,
  Lock,
  Mail,
  Monitor,
  Scissors,
  Send,
  Table,
  Users,
} from "@/components/icons";

const features = [
  {
    icon: FileText,
    title: "PDF-Import",
    text: "Komplette Sammel-PDFs aus Ihrer bestehenden Lohnsoftware importieren.",
  },
  {
    icon: Table,
    title: "Excel-Abgleich",
    text: "Personalnummern automatisch mit E-Mail-Adressen aus einer Excel-Liste verknüpfen.",
  },
  {
    icon: Scissors,
    title: "Automatische PDF-Trennung",
    text: "Sammel-PDFs automatisch in einzelne Mitarbeiterdokumente aufteilen.",
  },
  {
    icon: Hash,
    title: "Personalnummer-Erkennung",
    text: "Dokumente anhand der Personalnummer den richtigen Mitarbeitenden zuordnen.",
  },
  {
    icon: Lock,
    title: "PDF-Verschlüsselung",
    text: "Sensible Lohnabrechnungen vor dem Versand zuverlässig schützen.",
  },
  {
    icon: Send,
    title: "E-Mail-Versand",
    text: "Abrechnungen direkt versenden oder den Versand kontrolliert vorbereiten.",
  },
  {
    icon: Users,
    title: "Mitarbeitende ohne E-Mail",
    text: "Fehlende E-Mail-Adressen automatisch sammeln und separat ausweisen.",
  },
  {
    icon: AlertTriangle,
    title: "Prüfung und Fehlerübersicht",
    text: "Warnungen und Fehler sichtbar machen, bevor der Versand gestartet wird.",
  },
  {
    icon: ClipboardList,
    title: "Versandprotokoll",
    text: "Jeden Versand nachvollziehbar und sauber dokumentieren.",
  },
  {
    icon: BarChart,
    title: "Berichte und Exporte",
    text: "Auswertungen für Versand, fehlende E-Mails und offene Fälle erstellen.",
  },
  {
    icon: Monitor,
    title: "Lokale Verarbeitung",
    text: "Die Anwendung lokal in Ihrer eigenen Arbeitsumgebung ausführen.",
  },
  {
    icon: Key,
    title: "Lizenzverwaltung",
    text: "Lizenzen und beliebig viele Mandanten zentral und kontrolliert verwalten.",
  },
];

export default function FeaturesPage() {
  return (
    <>
      <section className="page-intro">
        <div className="container">
          <span className="eyebrow">
            <ClipboardList size={14} /> Funktionen
          </span>
          <h1>Alles, was der digitale Abrechnungsversand braucht.</h1>
          <p>
            Von der Datenübernahme bis zum fertigen Bericht bleibt jeder Schritt in
            einem übersichtlichen Arbeitsablauf.
          </p>
        </div>
      </section>

      <section className="section page-section">
        <div className="container">
          <div className="features-grid">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <article className="feature-card" key={feature.title}>
                  <div className="feature-icon">
                    <Icon size={21} />
                  </div>
                  <h2>{feature.title}</h2>
                  <p>{feature.text}</p>
                </article>
              );
            })}
          </div>

          <div className="feature-callout">
            <div>
              <Mail size={22} />
              <span>
                <strong>Ohne Mandantenlimit:</strong> Nutzen Sie LohnMail für beliebig
                viele Unternehmen und Mandanten.
              </span>
            </div>
            <Link className="btn btn-primary" href="/preis">
              Preis ansehen
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
