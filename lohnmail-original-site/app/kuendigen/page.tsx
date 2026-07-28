import type { Metadata } from "next";
import LegalRequestForm from "@/components/LegalRequestForm";

export const metadata: Metadata = {
  title: "LohnMail-Vertrag kündigen",
  description:
    "Elektronische Kündigungsfunktion für laufende LohnMail-Abonnements.",
};

export default function CancellationPage() {
  return (
    <>
      <section className="page-intro legal-action-intro">
        <div className="container">
          <span className="eyebrow">Vertragsverwaltung</span>
          <h1>Verträge hier kündigen</h1>
          <p>
            Übermitteln Sie hier eine ordentliche oder außerordentliche Kündigung
            Ihres laufenden LohnMail-Abonnements.
          </p>
        </div>
      </section>

      <section className="section page-section legal-request-page">
        <div className="container legal-request-layout">
          <div>
            <h2>Kündigung übermitteln</h2>
            <p>
              Ohne Angabe eines Wunschdatums wirkt die Kündigung zum
              nächstmöglichen Zeitpunkt. Nach dem Absenden erhalten Sie sofort
              eine Eingangsbestätigung per E-Mail.
            </p>
            <p>
              Eine Kündigung ist zusätzlich über das bereitgestellte
              Stripe-Kundenportal oder per E-Mail möglich.
            </p>
          </div>
          <LegalRequestForm mode="cancellation" />
        </div>
      </section>
    </>
  );
}
