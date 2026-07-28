import type { Metadata } from "next";
import LegalRequestForm from "@/components/LegalRequestForm";

export const metadata: Metadata = {
  title: "Vertrag widerrufen | LohnMail",
  description:
    "Elektronische Widerrufsfunktion für online geschlossene LohnMail-Verträge.",
};

export default function WithdrawalRequestPage() {
  return (
    <>
      <section className="page-intro legal-action-intro">
        <div className="container">
          <span className="eyebrow">Elektronische Widerrufsfunktion</span>
          <h1>Vertrag widerrufen</h1>
          <p>
            Verbraucher können hier innerhalb der gesetzlichen Widerrufsfrist
            eine eindeutige Widerrufserklärung übermitteln.
          </p>
        </div>
      </section>

      <section className="section page-section legal-request-page">
        <div className="container legal-request-layout">
          <div>
            <h2>Angaben zum Vertrag</h2>
            <p>
              Nach dem Absenden erhalten Sie unverzüglich eine Bestätigung mit
              Inhalt, Datum und Uhrzeit Ihrer Erklärung per E-Mail.
            </p>
            <p>
              Weitere Informationen finden Sie in der{" "}
              <a href="/widerrufsbelehrung">Widerrufsbelehrung</a>.
            </p>
          </div>
          <LegalRequestForm mode="withdrawal" />
        </div>
      </section>
    </>
  );
}
