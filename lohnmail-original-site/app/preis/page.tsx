import Link from "next/link";
import { Check, Euro } from "@/components/icons";

const included = [
  "Unbegrenzt viele Mandanten und Unternehmen",
  "PDF-Import",
  "Excel-Abgleich",
  "Automatische Dokumententrennung",
  "Personalnummer-Erkennung",
  "PDF-Verschlüsselung",
  "E-Mail-Versand",
  "Prüfübersicht",
  "Versandprotokoll",
  "Berichte und Exporte",
  "Lizenzverwaltung",
  "Lokale Verarbeitung",
];

export default function PricingPage() {
  return (
    <>
      <section className="page-intro">
        <div className="container">
          <span className="eyebrow">
            <Euro size={14} /> Preis
          </span>
          <h1>Eine klare Lizenz. Alle wichtigen Funktionen.</h1>
          <p>
            Keine komplizierten Pakete und kein Mandantenlimit. Testen Sie den
            vollständigen Funktionsumfang zwei Monate kostenlos.
          </p>
        </div>
      </section>

      <section className="section page-section pricing-page">
        <div className="container pricing-layout">
          <div className="pricing-summary">
            <span className="pricing-plan">LohnMail Professional</span>
            <div className="pricing-price">
              40&nbsp;€ <span>/ Monat</span>
            </div>
            <small className="pricing-tax-note">
              Endpreis. Soweit Umsatzsteuer anfällt, ist sie enthalten.
            </small>
            <p>
              Für Unternehmen, HR-Abteilungen, Lohnbuchhaltungsteams und
              Steuerkanzleien.
            </p>
            <div className="pricing-trial">
              <strong>2 Monate kostenlos testen</strong>
              Während der Testphase 0 €. Danach flexibel per Karte oder Rechnung
              weiter nutzen.
            </div>
            <Link className="btn btn-primary btn-lg" href="/testzugang">
              Kostenlos testen
            </Link>
          </div>

          <div className="pricing-included">
            <span className="eyebrow">In der Lizenz enthalten</span>
            <h2>Sie kaufen den vollständigen Arbeitsablauf.</h2>
            <ul>
              {included.map((item) => (
                <li key={item}>
                  <Check size={17} />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}
