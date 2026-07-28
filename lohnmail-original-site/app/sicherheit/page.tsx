import Link from "next/link";
import {
  CheckCircle,
  ClipboardList,
  Hash,
  Lock,
  Monitor,
  Search,
  Shield,
} from "@/components/icons";

const security = [
  {
    icon: Monitor,
    title: "Lokale Verarbeitung",
    text: "Die Anwendung läuft lokal auf Ihrem Computer. Ihre Lohndaten bleiben in Ihrer Arbeitsumgebung.",
  },
  {
    icon: Lock,
    title: "PDF-Verschlüsselung",
    text: "Sensible Abrechnungen können vor dem Versand geschützt werden.",
  },
  {
    icon: Hash,
    title: "Klare Zuordnung",
    text: "Personalnummern verbinden Dokumente mit den richtigen Mitarbeitenden.",
  },
  {
    icon: Search,
    title: "Prüfung vor dem Versand",
    text: "Fehlende E-Mail-Adressen, Warnungen und offene Fälle werden vorab sichtbar.",
  },
  {
    icon: ClipboardList,
    title: "Saubere Protokolle",
    text: "Verarbeitung und Versand bleiben auch bei späteren Rückfragen nachvollziehbar.",
  },
  {
    icon: Shield,
    title: "Kontrollierter Prozess",
    text: "Unübersichtliche Zwischenschritte werden durch einen klaren Workflow ersetzt.",
  },
];

export default function SecurityPage() {
  return (
    <>
      <section className="page-intro">
        <div className="container">
          <span className="eyebrow">
            <Shield size={14} /> Sicherheit
          </span>
          <h1>Sensible Lohndaten verdienen einen sicheren Prozess.</h1>
          <p>
            LohnMail unterstützt eine korrekte Zuordnung, eine bewusste Prüfung vor
            dem Versand und eine nachvollziehbare Dokumentation.
          </p>
        </div>
      </section>

      <section className="section page-section">
        <div className="container security-page-grid">
          {security.map((item) => {
            const Icon = item.icon;
            return (
              <article className="security-page-item" key={item.title}>
                <div>
                  <Icon size={21} />
                </div>
                <span>
                  <h2>{item.title}</h2>
                  <p>{item.text}</p>
                </span>
              </article>
            );
          })}
        </div>
      </section>

      <section className="section section-alt page-section">
        <div className="container security-statement">
          <div className="security-statement-icon">
            <CheckCircle size={34} />
          </div>
          <div>
            <span className="eyebrow">Kontrolle vor Geschwindigkeit</span>
            <h2>Erst prüfen. Dann verschlüsselt senden.</h2>
            <p>
              LohnMail macht kritische Fälle sichtbar, bevor ein Dokument versendet
              wird. So bleibt die Entscheidung bei der Lohnbuchhaltung.
            </p>
          </div>
          <Link className="btn btn-primary" href="/testzugang">
            Sicher testen
          </Link>
        </div>
      </section>
    </>
  );
}
