import type { Metadata } from "next";
import LegalDocument from "@/components/LegalDocument";

export const metadata: Metadata = {
  title: "Datenschutzerklärung | LohnMail",
  description:
    "Informationen zur Verarbeitung personenbezogener Daten auf der LohnMail-Website und im Lizenzsystem.",
};

export default function PrivacyPage() {
  return (
    <LegalDocument
      eyebrow="Datenschutz"
      title="Datenschutzerklärung"
      intro="Hier erfahren Sie, welche personenbezogenen Daten beim Besuch der Website, bei einer Anfrage und bei der Lizenzierung von LohnMail verarbeitet werden."
    >
      <section>
        <h2>1. Verantwortlicher</h2>
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
      </section>

      <section>
        <h2>2. Aufruf der Website und Server-Protokolle</h2>
        <p>
          Beim Aufruf der Website werden technisch erforderliche Informationen
          verarbeitet. Dazu können IP-Adresse, Zeitpunkt des Zugriffs, aufgerufene
          Seite, übertragene Datenmenge, Referrer, Browser und Betriebssystem
          gehören. Diese Daten dienen der sicheren und stabilen Bereitstellung der
          Website.
        </p>
        <p>
          Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO. Unser berechtigtes
          Interesse liegt im sicheren, störungsfreien und missbrauchsgeschützten
          Betrieb des Angebots.
        </p>
        <p>
          Die Website wird über Vercel bereitgestellt. Dabei kann Vercel Inc.,
          USA, als Auftragsverarbeiter technische Zugriffsdaten verarbeiten.
          Soweit Daten in Drittländer übermittelt werden, erfolgt dies auf
          Grundlage der anwendbaren Garantien nach Art. 44 ff. DSGVO.
        </p>
      </section>

      <section>
        <h2>3. Kontakt- und Testzugangsanfragen</h2>
        <p>
          Wenn Sie das Kontaktformular verwenden, verarbeiten wir insbesondere
          Firmenname oder Bezeichnung, Ansprechpartner, E-Mail-Adresse,
          gegebenenfalls Telefonnummer, Mitarbeiterzahl und Ihre Nachricht. Die
          Angaben werden ausschließlich zur Bearbeitung der Anfrage, zur
          Bereitstellung des Testzugangs und zur vorvertraglichen Kommunikation
          verwendet.
        </p>
        <p>
          Rechtsgrundlagen sind Art. 6 Abs. 1 lit. b DSGVO, soweit die Anfrage
          einen Vertrag oder dessen Anbahnung betrifft, und Art. 6 Abs. 1 lit. f
          DSGVO für allgemeine Anfragen.
        </p>
        <p>
          Der Versand der Formularnachricht erfolgt über einen SMTP-Dienst von
          Google. Anbieter für Nutzer im Europäischen Wirtschaftsraum ist Google
          Ireland Limited, Gordon House, Barrow Street, Dublin 4, Irland.
        </p>
      </section>

      <section>
        <h2>4. Widerrufs- und Kündigungserklärungen</h2>
        <p>
          Nutzen Sie die elektronischen Funktionen zum Widerruf oder zur
          Kündigung, verarbeiten wir Ihren Namen, Ihre E-Mail-Adresse, Angaben zur
          Identifizierung des Vertrags, den gewünschten Beendigungszeitpunkt und
          gegebenenfalls einen Kündigungsgrund oder eine ergänzende Mitteilung.
        </p>
        <p>
          Die Daten werden zur Entgegennahme, Bestätigung und Bearbeitung Ihrer
          Erklärung verarbeitet. Rechtsgrundlagen sind Art. 6 Abs. 1 lit. b und
          lit. c DSGVO. Die Eingangsbestätigung wird über den in Abschnitt 3
          genannten E-Mail-Dienst versendet.
        </p>
      </section>

      <section>
        <h2>5. Testphase, Lizenzierung und Kundenverwaltung</h2>
        <p>
          Für Test- und Vertragslizenzen verarbeiten wir die zur Verwaltung der
          Lizenz erforderlichen Daten. Dazu können Name oder Firma, E-Mail-Adresse,
          Rechnungsanschrift, Unternehmensnummer, Lizenzschlüssel,
          Lizenzstatus, Laufzeiten, eine technische Installationskennung sowie
          Zahlungs- und Abonnementreferenzen gehören.
        </p>
        <p>
          Die Verarbeitung ist zur Bereitstellung und Verwaltung der Lizenz, zur
          Missbrauchsvermeidung und zur Vertragsabwicklung erforderlich. Grundlage
          sind Art. 6 Abs. 1 lit. b und lit. f DSGVO.
        </p>
        <p>
          Das Lizenzsystem wird über Vercel betrieben. Vertrags- und Lizenzdaten
          werden in einer von Supabase bereitgestellten Datenbank gespeichert.
          Supabase kann dabei als Auftragsverarbeiter tätig werden. Bei
          Drittlandübermittlungen werden die gesetzlichen Voraussetzungen der
          Art. 44 ff. DSGVO beachtet.
        </p>
      </section>

      <section>
        <h2>6. Zahlungsabwicklung über Stripe</h2>
        <p>
          Für Karten- und Rechnungszahlungen nutzen wir Stripe. Verantwortlicher
          Anbieter im Europäischen Wirtschaftsraum ist grundsätzlich Stripe
          Payments Europe, Limited, 1 Grand Canal Street Lower, Grand Canal Dock,
          Dublin, Irland.
        </p>
        <p>
          An Stripe werden die für Zahlung, Rechnung und Abonnement erforderlichen
          Daten übermittelt. Dazu können Name, Firma, E-Mail-Adresse,
          Rechnungsanschrift, Zahlungsart, Preis, Währung, Transaktions- und
          Abonnementdaten gehören. Vollständige Karten- oder Bankdaten werden nicht
          auf unserem Webserver gespeichert.
        </p>
        <p>
          Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO. Für gesetzlich
          vorgeschriebene Buchführungs- und Nachweispflichten gilt zusätzlich Art.
          6 Abs. 1 lit. c DSGVO. Stripe verarbeitet bestimmte Daten auch in eigener
          Verantwortlichkeit nach den dort geltenden Datenschutzbestimmungen.
        </p>
      </section>

      <section>
        <h2>7. Lokale Verarbeitung in LohnMail</h2>
        <p>
          Lohnabrechnungen, Mitarbeiterlisten und die aus ihnen erzeugten
          Einzeldokumente werden grundsätzlich lokal auf dem vom Kunden
          eingesetzten Gerät verarbeitet. Diese Inhalte werden nicht zur
          Verarbeitung an unsere Website, den Lizenzserver, Stripe oder Supabase
          übertragen.
        </p>
        <p>
          Der Versand der Abrechnungen erfolgt über die vom Kunden in LohnMail
          konfigurierte E-Mail-Infrastruktur. Für diese Verarbeitung ist der
          jeweilige Kunde datenschutzrechtlich verantwortlich.
        </p>
      </section>

      <section>
        <h2>8. Cookies, Reichweitenmessung und Schriftarten</h2>
        <p>
          Auf der LohnMail-Website setzen wir derzeit keine eigenen
          Marketing-Cookies und keine Dienste zur personalisierten Werbung oder
          Reichweitenmessung ein. Technisch erforderliche Speicherungen können
          durch Hosting- oder Sicherheitsfunktionen erfolgen.
        </p>
        <p>
          Beim Wechsel zu Stripe gelten die dortigen technischen und
          datenschutzrechtlichen Einstellungen. Die auf dieser Website verwendeten
          Schriftarten werden lokal ausgeliefert; beim Seitenaufruf wird deshalb
          keine Verbindung zu Google Fonts hergestellt.
        </p>
      </section>

      <section>
        <h2>9. Empfänger und Drittlandübermittlungen</h2>
        <p>
          Personenbezogene Daten erhalten nur Stellen, die sie für die genannten
          Zwecke benötigen. Dazu zählen Hosting-, Datenbank-, E-Mail- und
          Zahlungsdienstleister sowie Behörden, soweit eine gesetzliche Pflicht
          besteht. Auftragsverarbeiter werden nach Art. 28 DSGVO verpflichtet.
        </p>
        <p>
          Bei Übermittlungen außerhalb des Europäischen Wirtschaftsraums stützen
          wir uns, abhängig vom Anbieter, auf einen Angemessenheitsbeschluss,
          Standardvertragsklauseln oder eine andere gesetzlich anerkannte
          Übermittlungsgrundlage.
        </p>
      </section>

      <section>
        <h2>10. Speicherdauer</h2>
        <p>
          Anfragedaten werden gelöscht, wenn die Anfrage abschließend bearbeitet
          ist und keine gesetzlichen oder vertraglichen Gründe für eine weitere
          Speicherung bestehen. Vertrags-, Rechnungs- und Zahlungsdaten werden für
          die Dauer des Vertrags und anschließend entsprechend den handels- und
          steuerrechtlichen Aufbewahrungsfristen gespeichert.
        </p>
        <p>
          Technische Protokolldaten werden nur so lange vorgehalten, wie dies für
          Betrieb, Sicherheit und Fehleranalyse erforderlich ist. Daten können
          länger gespeichert werden, wenn dies zur Geltendmachung, Ausübung oder
          Verteidigung von Rechtsansprüchen notwendig ist.
        </p>
      </section>

      <section>
        <h2>11. Ihre Rechte</h2>
        <p>Sie haben nach Maßgabe der DSGVO insbesondere das Recht auf:</p>
        <ul>
          <li>Auskunft über Ihre verarbeiteten Daten nach Art. 15 DSGVO,</li>
          <li>Berichtigung unrichtiger Daten nach Art. 16 DSGVO,</li>
          <li>Löschung nach Art. 17 DSGVO,</li>
          <li>Einschränkung der Verarbeitung nach Art. 18 DSGVO,</li>
          <li>Datenübertragbarkeit nach Art. 20 DSGVO,</li>
          <li>Widerspruch gegen Verarbeitungen nach Art. 21 DSGVO,</li>
          <li>Widerruf einer Einwilligung mit Wirkung für die Zukunft.</li>
        </ul>
        <p>
          Zur Ausübung Ihrer Rechte genügt eine Nachricht an{" "}
          <a href="mailto:support@lohn-mail.de">support@lohn-mail.de</a>. Zudem
          besteht ein Beschwerderecht bei einer Datenschutzaufsichtsbehörde.
        </p>
      </section>

      <section>
        <h2>12. Datensicherheit und Änderungen</h2>
        <p>
          Die Website nutzt TLS-Verschlüsselung. Wir treffen angemessene
          technische und organisatorische Maßnahmen, um personenbezogene Daten vor
          Verlust, unbefugtem Zugriff und Veränderung zu schützen.
        </p>
        <p>
          Wir aktualisieren diese Erklärung, wenn sich Funktionen, Dienstleister
          oder gesetzliche Anforderungen ändern. Es gilt die auf dieser Seite
          veröffentlichte Fassung.
        </p>
      </section>
    </LegalDocument>
  );
}
