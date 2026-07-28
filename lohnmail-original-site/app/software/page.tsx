import Link from "next/link";
import SoftwareShowcase from "@/components/SoftwareShowcase";
import { CheckCircle } from "@/components/icons";

const softwarePoints = [
  "Aktuellen Monatslauf sofort überblicken",
  "Fehler und Warnungen vor dem Versand erkennen",
  "Mitarbeitende ohne E-Mail separat bearbeiten",
  "Versandstatus und offene Fälle nachvollziehen",
  "Berichte und Exporte zentral bereitstellen",
  "Beliebig viele Mandanten sauber verwalten",
];

export default function SoftwarePage() {
  return (
    <>
      <SoftwareShowcase />

      <section className="section page-section">
        <div className="container software-page-grid">
          <div>
            <span className="eyebrow">Für den Monatslauf gebaut</span>
            <h2 className="section-title">Übersichtlich an den entscheidenden Stellen</h2>
            <p className="section-lead">
              Die Navigation der Anwendung folgt dem tatsächlichen Ablauf in der
              Lohnbuchhaltung: Verarbeitung, Prüfung, Versand und Berichte.
            </p>
          </div>

          <div className="software-point-list">
            {softwarePoints.map((point) => (
              <div key={point}>
                <CheckCircle size={18} />
                <span>{point}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="container section-action">
          <Link className="btn btn-primary" href="/testzugang">
            2 Monate kostenlos testen
          </Link>
        </div>
      </section>
    </>
  );
}
