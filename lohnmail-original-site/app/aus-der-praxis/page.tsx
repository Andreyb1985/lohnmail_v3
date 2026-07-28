import Link from "next/link";
import {
  Building,
  CheckCircle,
  ClipboardList,
  Home,
  Mail,
  Users,
} from "@/components/icons";

const audience = [
  { icon: Home, label: "Pflegeeinrichtungen und Seniorenzentren" },
  { icon: Building, label: "Mittelständische Unternehmen" },
  { icon: ClipboardList, label: "Steuerkanzleien" },
  { icon: Users, label: "HR- und Payroll-Abteilungen" },
  { icon: Building, label: "Organisationen mit mehreren Standorten" },
  { icon: Mail, label: "Lohnbuchhaltungen mit vielen Abrechnungen" },
];

export default function PracticePage() {
  return (
    <>
      <section className="page-intro">
        <div className="container">
          <span className="eyebrow">
            <Users size={14} /> Aus der Praxis
          </span>
          <h1>Von einem Lohnbuchhalter für den echten Monatslauf entwickelt.</h1>
          <p>
            LohnMail basiert auf realen Anforderungen aus dem Arbeitsalltag und nicht
            auf theoretischen Annahmen.
          </p>
        </div>
      </section>

      <section className="section page-section">
        <div className="container praxis-grid">
          <div className="praxis-text">
            <p>
              LohnMail wurde nicht als theoretisches Softwareprojekt entwickelt,
              sondern direkt aus dem Alltag der Lohnbuchhaltung heraus.
            </p>
            <p>
              Der Entwickler arbeitet selbst als Lohnbuchhalter und kennt die typischen
              Herausforderungen beim monatlichen Versand: Zeitdruck, sensible Daten,
              fehlende E-Mail-Adressen, manuelle Kontrolle, Rückfragen und die
              Notwendigkeit einer sauberen Dokumentation.
            </p>
            <p>
              Deshalb ist LohnMail konsequent auf den praktischen Einsatz ausgerichtet:
              verständlich, lokal, übersichtlich und auf reale Arbeitsabläufe abgestimmt.
            </p>
          </div>

          <div className="trust-card">
            <span className="trust-label">
              <CheckCircle size={14} /> Bereits im Unternehmenseinsatz
            </span>
            <h2>GeSoB GmbH · rund 500 Mitarbeitende</h2>
            <p>
              LohnMail wurde bei der <strong>GeSoB GmbH</strong> in einer
              Unternehmensumgebung mit rund <strong>500 Mitarbeitenden</strong>{" "}
              integriert und anhand realer Abläufe weiterentwickelt.
            </p>
          </div>
        </div>

        <div className="container">
          <p className="praxis-claim">
            Entwickelt von einem Lohnbuchhalter.
            <span className="sep">·</span>
            Getestet im Unternehmensalltag.
            <span className="sep">·</span>
            Optimiert für HR und Payroll.
          </p>
        </div>
      </section>

      <section className="section section-alt page-section">
        <div className="container">
          <span className="eyebrow">
            <Users size={14} /> Für wen ist LohnMail geeignet?
          </span>
          <h2 className="section-title">
            Für Organisationen mit regelmäßigen Lohnabrechnungen
          </h2>
          <p className="section-lead">
            Besonders sinnvoll für Unternehmen mit etwa 50 bis 1.000 oder mehr
            Mitarbeitenden und für Teams, die mehrere Mandanten betreuen.
          </p>

          <div className="audience-page-grid">
            {audience.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label}>
                  <Icon size={19} />
                  <span>{item.label}</span>
                </div>
              );
            })}
          </div>

          <div className="section-action">
            <Link className="btn btn-primary" href="/testzugang">
              Im eigenen Unternehmen testen
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
