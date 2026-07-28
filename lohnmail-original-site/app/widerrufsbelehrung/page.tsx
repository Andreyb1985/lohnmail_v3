import type { Metadata } from "next";
import LegalDocument from "@/components/LegalDocument";

export const metadata: Metadata = {
  title: "Widerrufsbelehrung | LohnMail",
  description:
    "Informationen zum gesetzlichen Widerrufsrecht für Verbraucher bei LohnMail.",
};

export default function WithdrawalPage() {
  return (
    <LegalDocument
      eyebrow="Für Verbraucher"
      title="Widerrufsbelehrung"
      intro="Die folgenden Hinweise gelten für Verbraucher, die einen kostenpflichtigen Vertrag über LohnMail im Fernabsatz abschließen."
    >
      <section>
        <h2>Widerrufsrecht</h2>
        <p>
          Sie haben das Recht, binnen vierzehn Tagen ohne Angabe von Gründen
          diesen Vertrag zu widerrufen.
        </p>
        <p>
          Die Widerrufsfrist beträgt vierzehn Tage ab dem Tag des
          Vertragsschlusses.
        </p>
        <p>
          Um Ihr Widerrufsrecht auszuüben, müssen Sie uns
        </p>
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
          <br />
          E-Mail:{" "}
          <a href="mailto:support@lohn-mail.de">support@lohn-mail.de</a>
        </address>
        <p>
          mittels einer eindeutigen Erklärung, zum Beispiel durch einen mit der
          Post versandten Brief oder eine E-Mail, über Ihren Entschluss
          informieren, diesen Vertrag zu widerrufen. Sie können dafür das unten
          stehende Muster-Widerrufsformular verwenden; vorgeschrieben ist dessen
          Verwendung nicht.
        </p>
        <p>
          Zur Wahrung der Widerrufsfrist reicht es aus, dass Sie die Mitteilung
          über die Ausübung des Widerrufsrechts vor Ablauf der Widerrufsfrist
          absenden.
        </p>
        <p>
          Sie können Ihr Widerrufsrecht außerdem über unsere ständig verfügbare
          elektronische Funktion{" "}
          <a href="/widerruf">„Vertrag widerrufen“</a> ausüben. Nach dem
          Absenden erhalten Sie unverzüglich eine Eingangsbestätigung mit dem
          Inhalt sowie Datum und Uhrzeit Ihrer Erklärung per E-Mail.
        </p>
      </section>

      <section>
        <h2>Folgen des Widerrufs</h2>
        <p>
          Wenn Sie diesen Vertrag widerrufen, haben wir Ihnen alle Zahlungen, die
          wir von Ihnen erhalten haben, unverzüglich und spätestens binnen
          vierzehn Tagen ab dem Tag zurückzuzahlen, an dem Ihre Mitteilung über den
          Widerruf bei uns eingegangen ist.
        </p>
        <p>
          Für die Rückzahlung verwenden wir dasselbe Zahlungsmittel, das Sie bei
          der ursprünglichen Transaktion eingesetzt haben, sofern nicht
          ausdrücklich etwas anderes vereinbart wurde. Für die Rückzahlung werden
          Ihnen keine Entgelte berechnet.
        </p>
        <p>
          Haben Sie verlangt, dass eine Dienstleistung bereits während der
          Widerrufsfrist beginnen soll, müssen Sie einen angemessenen Betrag
          zahlen, der dem Anteil der bis zum Zeitpunkt Ihres Widerrufs bereits
          erbrachten Leistungen am Gesamtumfang der vertraglich vorgesehenen
          Leistungen entspricht.
        </p>
      </section>

      <section>
        <h2>Vorzeitiges Erlöschen bei digitalen Inhalten</h2>
        <p>
          Bei einem Vertrag über die Bereitstellung digitaler Inhalte, die sich
          nicht auf einem körperlichen Datenträger befinden, kann das
          Widerrufsrecht vorzeitig erlöschen, wenn Sie ausdrücklich zugestimmt
          haben, dass wir vor Ablauf der Widerrufsfrist mit der Vertragserfüllung
          beginnen, Sie Ihre Kenntnis vom dadurch eintretenden Verlust des
          Widerrufsrechts bestätigt haben und Ihnen eine Vertragsbestätigung nach
          den gesetzlichen Vorgaben bereitgestellt wurde.
        </p>
      </section>

      <section>
        <h2>Muster-Widerrufsformular</h2>
        <p>
          Wenn Sie den Vertrag widerrufen wollen, können Sie dieses Formular
          ausfüllen und per Post oder E-Mail an uns senden:
        </p>
        <div className="legal-form-template">
          <p>
            An Andrii Bakanov, LohnMail, Große Leining 22, 45141 Essen,
            Deutschland, E-Mail: support@lohn-mail.de
          </p>
          <p>
            Hiermit widerrufe(n) ich/wir (*) den von mir/uns (*) abgeschlossenen
            Vertrag über die Bereitstellung und Nutzung der Software LohnMail.
          </p>
          <p>Vertrag abgeschlossen am (*): ____________________</p>
          <p>Name des/der Verbraucher(s): ____________________</p>
          <p>Anschrift des/der Verbraucher(s): ____________________</p>
          <p>
            Unterschrift des/der Verbraucher(s), nur bei Mitteilung auf Papier:
            ____________________
          </p>
          <p>Datum: ____________________</p>
          <p>(*) Unzutreffendes streichen.</p>
        </div>
      </section>
    </LegalDocument>
  );
}
