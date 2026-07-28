import ContactForm from "@/components/ContactForm";
import { CheckCircle, Mail } from "@/components/icons";

const trialPoints = [
  "Voller Funktionsumfang",
  "Zahlungsart erst zum Testende wählen",
  "Für Windows und macOS",
  "Danach Karte oder Rechnung",
];

export default function TrialPage() {
  return (
    <>
      <section className="page-intro trial-intro">
        <div className="container">
          <span className="eyebrow">
            <Mail size={14} /> Testzugang
          </span>
          <h1>LohnMail zwei Monate kostenlos testen.</h1>
          <p>
            Füllen Sie das Formular aus. Anschließend können Sie Ihre Version für
            Windows oder macOS auswählen.
          </p>

          <div className="trial-points">
            {trialPoints.map((point) => (
              <span key={point}>
                <CheckCircle size={16} />
                {point}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="section page-section contact-page">
        <div className="container contact-page-layout">
          <div>
            <span className="eyebrow">Ihre Anfrage</span>
            <h2 className="section-title">Testzugang anfragen</h2>
            <p className="section-lead">
              Wir melden uns zeitnah bei Ihnen und unterstützen Sie beim Einstieg.
            </p>
            <p className="contact-email">
              <a href="mailto:support@lohn-mail.de">support@lohn-mail.de</a>
            </p>
          </div>
          <ContactForm />
        </div>
      </section>
    </>
  );
}
