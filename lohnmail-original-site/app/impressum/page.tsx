import type { Metadata } from "next";
import LegalDocument from "@/components/LegalDocument";

export const metadata: Metadata = {
  title: "Impressum | LohnMail",
  description: "Anbieterkennzeichnung und Kontaktinformationen von LohnMail.",
};

export default function ImpressumPage() {
  return (
    <LegalDocument
      eyebrow="Anbieterkennzeichnung"
      title="Impressum"
      intro="Angaben zum Anbieter von LohnMail gemäß § 5 Digitale-Dienste-Gesetz (DDG)."
    >
      <section>
        <h2>Anbieter</h2>
        <address>
          <strong>Andrii Bakanov</strong>
          <br />
          handelnd unter „LohnMail“
          <br />
          Große Leining 22
          <br />
          45141 Essen
          <br />
          Deutschland
        </address>
      </section>

      <section>
        <h2>Kontakt</h2>
        <p>
          E-Mail:{" "}
          <a href="mailto:support@lohn-mail.de">support@lohn-mail.de</a>
        </p>
        <p>
          Für Support-, Vertrags- und Lizenzanfragen steht außerdem das{" "}
          <a href="/testzugang">Kontaktformular</a> zur Verfügung.
        </p>
      </section>

      <section>
        <h2>Verantwortlich für Inhalte</h2>
        <p>
          Verantwortlich für journalistisch-redaktionelle Inhalte im Sinne des
          § 18 Abs. 2 MStV:
        </p>
        <address>
          Andrii Bakanov
          <br />
          Große Leining 22
          <br />
          45141 Essen
        </address>
      </section>

      <section>
        <h2>Verbraucherstreitbeilegung</h2>
        <p>
          Wir sind nicht verpflichtet und nicht bereit, an einem
          Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle
          teilzunehmen.
        </p>
      </section>

      <section>
        <h2>Haftung für Links</h2>
        <p>
          Unsere Seiten können Links zu externen Angeboten enthalten. Für deren
          Inhalte sind ausschließlich die jeweiligen Anbieter verantwortlich.
          Rechtswidrige Inhalte werden nach Kenntnis unverzüglich entfernt.
        </p>
      </section>
    </LegalDocument>
  );
}
