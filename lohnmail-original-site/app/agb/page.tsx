import type { Metadata } from "next";
import LegalDocument from "@/components/LegalDocument";

export const metadata: Metadata = {
  title: "Allgemeine Geschäftsbedingungen | LohnMail",
  description:
    "Allgemeine Geschäftsbedingungen für Testzugang, Lizenzierung und Nutzung der LohnMail-Software.",
};

export default function TermsPage() {
  return (
    <LegalDocument
      eyebrow="Vertragsbedingungen"
      title="Allgemeine Geschäftsbedingungen"
      intro="Diese Bedingungen regeln den Testzugang, die Lizenzierung und die Nutzung der Software LohnMail."
    >
      <section>
        <h2>1. Anbieter und Geltungsbereich</h2>
        <p>
          Diese Allgemeinen Geschäftsbedingungen gelten für Verträge über die
          Bereitstellung und Nutzung von LohnMail zwischen Andrii Bakanov,
          handelnd unter „LohnMail“, Große Leining 22, 45141 Essen, Deutschland
          (nachfolgend „Anbieter“), und seinen Kunden.
        </p>
        <p>
          Kunden können Verbraucher im Sinne des § 13 BGB oder Unternehmer im
          Sinne des § 14 BGB sein. Abweichende Bedingungen eines Unternehmers
          gelten nur, wenn der Anbieter ihnen ausdrücklich in Textform zustimmt.
        </p>
      </section>

      <section>
        <h2>2. Vertragsgegenstand</h2>
        <p>
          LohnMail ist eine lokal ausführbare Software zur strukturierten
          Verarbeitung, Prüfung, Trennung, Verschlüsselung und zum
          E-Mail-Versand von Lohnabrechnungsdokumenten. Der konkrete
          Funktionsumfang ergibt sich aus der zum Zeitpunkt des Vertragsschlusses
          veröffentlichten Produktbeschreibung.
        </p>
        <p>
          Die Lizenz umfasst die Verwaltung beliebig vieler Mandanten und
          Unternehmen. Soweit nicht ausdrücklich anders vereinbart, wird eine
          zeitlich auf die Vertragsdauer beschränkte Lizenz für eine aktivierte
          Installation bereitgestellt.
        </p>
      </section>

      <section>
        <h2>3. Testzugang und Vertragsschluss</h2>
        <p>
          Das Absenden einer Testzugangsanfrage ist kostenlos und begründet noch
          keinen kostenpflichtigen Vertrag. Die Testphase beginnt mit der
          Aktivierung der Testlizenz und dauert 60 Tage. Ohne Auswahl einer
          kostenpflichtigen Zahlungsart endet die Testlizenz automatisch; es
          entstehen keine Kosten.
        </p>
        <p>
          Ein kostenpflichtiger Vertrag kommt zustande, wenn der Kunde in der
          Software oder im bereitgestellten Bestellprozess eine Zahlungsart
          auswählt, die Bestellung verbindlich absendet und der Anbieter oder der
          beauftragte Zahlungsdienstleister den Abschluss bestätigt
          beziehungsweise die kostenpflichtige Lizenz aktiviert.
        </p>
        <p>
          Hat der Kunde bereits während der Testphase eine Zahlungsart
          eingerichtet, bleibt die noch vorhandene Testzeit erhalten. Die erste
          Zahlung beziehungsweise Rechnung wird grundsätzlich erst zum Ende der
          Testphase fällig, sofern im Bestellprozess nichts Abweichendes
          ausgewiesen wird.
        </p>
        <p>
          Vertragssprache ist Deutsch. Vertrags- und Zahlungsbestätigungen werden
          elektronisch an die vom Kunden angegebene E-Mail-Adresse übermittelt.
        </p>
      </section>

      <section>
        <h2>4. Bereitstellung und technische Voraussetzungen</h2>
        <p>
          Die Software wird als Download für die jeweils angebotenen
          Betriebssysteme bereitgestellt. Der Kunde ist für ein kompatibles und
          hinreichend geschütztes Endgerät, die Installation sowie die
          erforderlichen Systemberechtigungen verantwortlich.
        </p>
        <p>
          Für Lizenzaktivierung, Lizenzprüfung, Zahlungsverwaltung und Updates
          kann eine Internetverbindung erforderlich sein. Für den Versand von
          Dokumenten muss der Kunde eine geeignete E-Mail-Infrastruktur
          konfigurieren und die erforderlichen Zugangsdaten bereithalten.
        </p>
      </section>

      <section>
        <h2>5. Nutzungsrecht</h2>
        <p>
          Für die Dauer einer aktiven Test- oder Vertragslizenz erhält der Kunde
          ein einfaches, nicht ausschließliches und nicht übertragbares Recht,
          LohnMail für eigene betriebliche oder private Zwecke zu nutzen.
        </p>
        <p>
          Die Weitervermietung, der Weiterverkauf, die öffentliche
          Zugänglichmachung sowie die Weitergabe von Lizenzschlüsseln an Dritte
          sind nicht gestattet. Dekompilierung, Reverse Engineering und sonstige
          Eingriffe in den Programmcode sind nur zulässig, soweit zwingendes Recht
          dies ausdrücklich erlaubt.
        </p>
        <p>
          Eine Lizenz kann grundsätzlich nur auf einer Installation gleichzeitig
          aktiviert sein. Ein Gerätewechsel ist über die vorgesehene
          Deaktivierungs- oder Supportfunktion möglich.
        </p>
      </section>

      <section>
        <h2>6. Pflichten des Kunden</h2>
        <p>Der Kunde ist insbesondere verpflichtet,</p>
        <ul>
          <li>
            Eingabedaten, Zuordnungen, Empfänger und Prüfergebnisse vor dem
            Versand sorgfältig zu kontrollieren,
          </li>
          <li>
            nur Daten zu verarbeiten und zu versenden, für deren Verarbeitung
            eine rechtliche Grundlage besteht,
          </li>
          <li>
            Zugangsdaten, Lizenzschlüssel und verwendete Endgeräte vor Zugriff
            Dritter zu schützen,
          </li>
          <li>
            angemessene Datensicherungen der verwendeten Dateien und
            Konfigurationen anzulegen,
          </li>
          <li>
            die Software nicht missbräuchlich oder zur Verletzung von Rechten
            Dritter einzusetzen.
          </li>
        </ul>
        <p>
          LohnMail ersetzt keine fachliche, steuerliche oder rechtliche Prüfung
          der Lohnabrechnung. Die Freigabe und der Versand verbleiben in der
          Verantwortung des Kunden.
        </p>
      </section>

      <section>
        <h2>7. Preise und Zahlungsbedingungen</h2>
        <p>
          Nach der kostenlosen Testphase beträgt der auf der Website derzeit
          ausgewiesene Preis 40&nbsp;€ pro Monat. Maßgeblich ist der im
          Bestellprozess als Gesamtpreis angezeigte Betrag. Soweit Umsatzsteuer
          anfällt, ist sie im Gesamtpreis enthalten und wird auf der Rechnung
          entsprechend den gesetzlichen Vorgaben ausgewiesen.
        </p>
        <p>
          Bei Kartenzahlung wird der fällige Monatsbetrag über Stripe automatisch
          zum jeweiligen Abrechnungszeitpunkt eingezogen. Bei Zahlung auf Rechnung
          beträgt das Zahlungsziel 14 Tage ab Rechnungsdatum. Rechnungen und
          Zahlungsinformationen werden elektronisch bereitgestellt.
        </p>
        <p>
          Schlägt eine Zahlung fehl oder bleibt eine Rechnung trotz Fälligkeit
          unbezahlt, kann der Anbieter die Lizenz nach angemessener Ankündigung
          vorübergehend sperren. Die Zahlungspflicht für bereits fällige Beträge
          bleibt bestehen.
        </p>
      </section>

      <section>
        <h2>8. Laufzeit und Kündigung</h2>
        <p>
          Der kostenpflichtige Vertrag läuft auf unbestimmte Zeit und wird
          monatlich abgerechnet. Er kann von beiden Parteien zum Ende des jeweils
          laufenden Abrechnungszeitraums gekündigt werden.
        </p>
        <p>
          Die Kündigung kann über die elektronische Funktion{" "}
          <a href="/kuendigen">„Verträge hier kündigen“</a>, über das
          bereitgestellte Stripe-Kundenportal oder per E-Mail an{" "}
          <a href="mailto:support@lohn-mail.de">support@lohn-mail.de</a> erklärt
          werden. Nach Wirksamwerden der Kündigung endet das Nutzungsrecht. Bereits
          begonnene und bezahlte Abrechnungszeiträume werden grundsätzlich nicht
          anteilig erstattet; zwingende Verbraucherrechte bleiben unberührt.
        </p>
        <p>
          Das Recht zur außerordentlichen Kündigung aus wichtigem Grund bleibt
          bestehen.
        </p>
      </section>

      <section>
        <h2>9. Updates, Support und Änderungen</h2>
        <p>
          Während einer aktiven Lizenz stellt der Anbieter erforderliche
          Sicherheits- und Funktionsupdates im Rahmen der technischen
          Weiterentwicklung bereit. Ein Anspruch auf bestimmte neue Funktionen
          besteht nicht, sofern diese nicht ausdrücklich Vertragsbestandteil
          geworden sind.
        </p>
        <p>
          Der Anbieter darf die Software verändern, wenn dies der Sicherheit,
          Rechtskonformität, Kompatibilität oder Weiterentwicklung dient und die
          vertragsgemäße Hauptfunktion nicht unzumutbar beeinträchtigt.
        </p>
      </section>

      <section>
        <h2>10. Verfügbarkeit</h2>
        <p>
          Die lokale Verarbeitung der Dokumente ist grundsätzlich unabhängig von
          einer dauerhaften Verbindung zur Website. Online-Funktionen wie
          Lizenzprüfung, Zahlung, Download oder Updates können aufgrund von
          Wartung, Sicherheitsmaßnahmen oder Störungen zeitweise nicht verfügbar
          sein. Eine ununterbrochene Verfügbarkeit wird nicht zugesagt.
        </p>
      </section>

      <section>
        <h2>11. Mängelrechte</h2>
        <p>
          Es gelten die gesetzlichen Mängelrechte. Der Kunde soll auftretende
          Fehler möglichst nachvollziehbar beschreiben und dem Anbieter
          Gelegenheit zur Prüfung und Nachbesserung geben.
        </p>
        <p>
          Gegenüber Unternehmern verjähren Ansprüche wegen Sach- oder
          Rechtsmängeln innerhalb von zwölf Monaten ab Bereitstellung, soweit
          gesetzlich zulässig. Dies gilt nicht bei Arglist, Vorsatz, grober
          Fahrlässigkeit oder zwingenden gesetzlichen Ansprüchen.
        </p>
      </section>

      <section>
        <h2>12. Haftung</h2>
        <p>
          Der Anbieter haftet unbeschränkt bei Vorsatz und grober Fahrlässigkeit,
          bei Schäden aus der Verletzung von Leben, Körper oder Gesundheit, nach
          dem Produkthaftungsgesetz sowie in allen weiteren Fällen zwingender
          gesetzlicher Haftung.
        </p>
        <p>
          Bei leicht fahrlässiger Verletzung einer wesentlichen Vertragspflicht
          ist die Haftung auf den vertragstypischen, vorhersehbaren Schaden
          begrenzt. Im Übrigen ist die Haftung für leichte Fahrlässigkeit
          ausgeschlossen.
        </p>
        <p>
          Der Anbieter haftet nicht für Fehler, die auf unrichtigen
          Ausgangsdaten, einer fehlerhaften E-Mail-Konfiguration, unterlassener
          Kontrolle durch den Kunden oder fehlenden Datensicherungen beruhen,
          soweit der Anbieter diese Umstände nicht zu vertreten hat.
        </p>
      </section>

      <section>
        <h2>13. Datenschutz und lokale Dokumente</h2>
        <p>
          Die Verarbeitung personenbezogener Daten durch den Anbieter richtet
          sich nach der <a href="/datenschutz">Datenschutzerklärung</a>.
          Lohnabrechnungen und Mitarbeiterlisten werden grundsätzlich lokal
          verarbeitet und nicht an den Lizenzserver übermittelt.
        </p>
        <p>
          Übermittelt der Kunde im Rahmen einer Supportanfrage freiwillig
          Dokumente oder personenbezogene Daten, soll er diese zuvor auf das für
          die Fehleranalyse erforderliche Maß beschränken und nach Möglichkeit
          anonymisieren.
        </p>
      </section>

      <section>
        <h2>14. Widerrufsrecht für Verbraucher</h2>
        <p>
          Verbrauchern steht das gesetzliche Widerrufsrecht zu. Einzelheiten
          ergeben sich aus der{" "}
          <a href="/widerrufsbelehrung">Widerrufsbelehrung</a>. Gesetzliche
          Verbraucherrechte werden durch diese AGB nicht eingeschränkt.
        </p>
      </section>

      <section>
        <h2>15. Anwendbares Recht und Gerichtsstand</h2>
        <p>
          Es gilt das Recht der Bundesrepublik Deutschland unter Ausschluss des
          UN-Kaufrechts. Bei Verbrauchern gilt diese Rechtswahl nur, soweit ihnen
          dadurch nicht der Schutz zwingender Vorschriften ihres gewöhnlichen
          Aufenthaltsstaats entzogen wird.
        </p>
        <p>
          Ist der Kunde Kaufmann, juristische Person des öffentlichen Rechts oder
          öffentlich-rechtliches Sondervermögen, ist Essen ausschließlicher
          Gerichtsstand. Der Anbieter bleibt berechtigt, am allgemeinen
          Gerichtsstand des Kunden zu klagen.
        </p>
      </section>

      <section>
        <h2>16. Schlussbestimmungen</h2>
        <p>
          Sollte eine Bestimmung dieser AGB ganz oder teilweise unwirksam sein,
          bleibt die Wirksamkeit der übrigen Bestimmungen unberührt. An die Stelle
          der unwirksamen Bestimmung treten die gesetzlichen Vorschriften.
        </p>
        <p>
          Der Anbieter ist nicht verpflichtet und nicht bereit, an einem
          Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle
          teilzunehmen.
        </p>
      </section>
    </LegalDocument>
  );
}
