import Link from "next/link";
import {
  AlertTriangle,
  BarChart,
  FileText,
  Hash,
  Lock,
  Mail,
  Scissors,
  Send,
  Table,
  X,
  Zap,
} from "@/components/icons";

const problems = [
  "PDF-Dateien müssen manuell getrennt werden.",
  "Personalnummern müssen einzeln geprüft werden.",
  "E-Mail-Adressen müssen manuell gesucht oder abgeglichen werden.",
  "Abrechnungen müssen korrekt zugeordnet werden.",
  "Mitarbeitende ohne E-Mail müssen separat behandelt werden.",
  "Fehler sind schwer nachvollziehbar.",
  "Papier, Toner und Umschläge verursachen laufende Kosten.",
  "Der gesamte Prozess bindet wertvolle Arbeitszeit.",
];

const workflow = [
  { icon: FileText, label: "PDF importieren" },
  { icon: Table, label: "Excel-Liste laden" },
  { icon: Hash, label: "Personalnummer erkennen" },
  { icon: Scissors, label: "Dokumente trennen" },
  { icon: Lock, label: "PDF verschlüsseln" },
  { icon: Mail, label: "E-Mail vorbereiten" },
  { icon: Send, label: "Versenden" },
  { icon: BarChart, label: "Bericht erstellen" },
];

export default function ProcessPage() {
  return (
    <>
      <section className="page-intro">
        <div className="container">
          <span className="eyebrow">
            <Zap size={14} /> So funktioniert es
          </span>
          <h1>Ein klarer Ablauf statt manueller Einzelschritte.</h1>
          <p>
            LohnMail führt PDF, Mitarbeiterdaten, Prüfung und Versand in einem
            nachvollziehbaren Monatslauf zusammen.
          </p>
        </div>
      </section>

      <section className="section page-section">
        <div className="container">
          <span className="eyebrow">
            <AlertTriangle size={14} /> Das Problem
          </span>
          <h2 className="section-title">
            Der manuelle Versand kostet Zeit, Geld und Nerven
          </h2>
          <p className="section-lead">
            Sammel-PDFs müssen getrennt, Personalnummern geprüft, E-Mail-Adressen
            gesucht und fehlende Daten manuell nachbearbeitet werden. Besonders bei
            vielen Mitarbeitenden wird dieser Prozess schnell unübersichtlich.
          </p>

          <div className="problem-grid">
            {problems.map((problem) => (
              <div className="problem-item" key={problem}>
                <X size={17} />
                <span>{problem}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-alt page-section">
        <div className="container center">
          <span className="eyebrow">
            <Zap size={14} /> Die Lösung
          </span>
          <h2 className="section-title">LohnMail übernimmt den Prozess für Sie</h2>
          <p className="section-lead">
            Die Software importiert das Abrechnungs-PDF, liest Personalnummern,
            verknüpft die E-Mail-Adressen, trennt und verschlüsselt die Dokumente und
            bereitet den Versand vor.
          </p>
          <p className="section-lead">
            Berichte und Protokolle zeigen anschließend, welche Dokumente verarbeitet,
            versendet oder noch offen sind.
          </p>

          <div className="workflow">
            {workflow.map((step, index) => {
              const Icon = step.icon;
              return (
                <div className="workflow-step" key={step.label}>
                  <span className="workflow-num">{index + 1}</span>
                  <div className="workflow-icon">
                    <Icon size={20} />
                  </div>
                  <h3>{step.label}</h3>
                </div>
              );
            })}
          </div>

          <div className="section-action">
            <Link className="btn btn-primary" href="/software">
              Software ansehen
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
