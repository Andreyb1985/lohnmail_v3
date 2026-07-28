"use client";

import { useState } from "react";
import { CheckCircle, Clock, Monitor } from "./icons";

export default function ContactForm() {
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSending(true);
    setError("");

    const formData = new FormData(e.currentTarget);
    const payload = Object.fromEntries(formData.entries());

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const result = (await response.json().catch(() => null)) as
        | { ok?: boolean; error?: string }
        | null;

      if (!response.ok || !result?.ok) {
        throw new Error(result?.error || "Die Anfrage konnte nicht gesendet werden.");
      }

      setSent(true);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Die Anfrage konnte nicht gesendet werden. Bitte versuchen Sie es erneut.",
      );
    } finally {
      setSending(false);
    }
  }

  if (sent) {
    return (
      <div className="contact-wrap download-screen" role="status">
        <div className="download-heading">
          <div className="success-icon">
            <CheckCircle size={28} />
          </div>
          <div>
            <h3>Vielen Dank. Ihre Anfrage ist eingegangen.</h3>
            <p>Ihre Anfrage wurde an <strong>support@lohn-mail.de</strong> gesendet.</p>
          </div>
        </div>

        <div className="download-options" aria-label="Verfügbare LohnMail-Versionen">
          <div className="download-placeholder" aria-disabled="true">
            <span className="platform-icon"><Monitor size={24} /></span>
            <span>
              <strong>Für Windows</strong>
              <small>Windows 10 und 11 · EXE</small>
            </span>
            <span className="download-status">
              <Clock size={14} />
              In Vorbereitung
            </span>
          </div>
          <div className="download-placeholder" aria-disabled="true">
            <span className="platform-icon platform-text">MAC</span>
            <span>
              <strong>Für macOS</strong>
              <small>Apple Silicon und Intel · DMG</small>
            </span>
            <span className="download-status">
              <Clock size={14} />
              In Vorbereitung
            </span>
          </div>
        </div>

        <p className="download-note">
          Die Download-Dateien werden derzeit vorbereitet. Sobald Ihre Version
          freigeschaltet ist, erhalten Sie den Downloadlink per E-Mail.
        </p>
      </div>
    );
  }

  return (
    <div className="contact-wrap">
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="form-honeypot" aria-hidden="true">
          <label htmlFor="website">Website</label>
          <input id="website" name="website" type="text" tabIndex={-1} autoComplete="off" />
        </div>

        <div className="form-field">
          <label htmlFor="firma">Firmenname *</label>
          <input id="firma" name="firmenname" type="text" required autoComplete="organization" />
        </div>

        <div className="form-field">
          <label htmlFor="name">Ansprechpartner *</label>
          <input id="name" name="ansprechpartner" type="text" required autoComplete="name" />
        </div>

        <div className="form-field">
          <label htmlFor="email">E-Mail *</label>
          <input id="email" name="email" type="email" required autoComplete="email" />
        </div>

        <div className="form-field">
          <label htmlFor="tel">Telefonnummer</label>
          <input id="tel" name="telefon" type="tel" autoComplete="tel" />
        </div>

        <div className="form-field full">
          <label htmlFor="anzahl">Anzahl Mitarbeitende</label>
          <select id="anzahl" name="mitarbeitende" defaultValue="">
            <option value="" disabled>
              Bitte auswählen
            </option>
            <option value="1-49">1 – 49</option>
            <option value="50-199">50 – 199</option>
            <option value="200-499">200 – 499</option>
            <option value="500-1000">500 – 1000</option>
            <option value="1000+">mehr als 1000</option>
          </select>
        </div>

        <div className="form-field full">
          <label htmlFor="nachricht">Nachricht</label>
          <textarea id="nachricht" name="nachricht" rows={4} />
        </div>

        <label className="form-check">
          <input type="checkbox" name="datenschutz" required />
          <span>
            Ich habe die{" "}
            <a href="/datenschutz" style={{ textDecoration: "underline" }}>
              Datenschutzerklärung
            </a>{" "}
            zur Verarbeitung meiner Angaben bei Kontakt- und Testzugangsanfragen
            zur Kenntnis genommen. *
          </span>
        </label>

        <button type="submit" className="btn btn-primary btn-lg" disabled={sending}>
          {sending ? "Wird gesendet…" : "Testzugang anfragen"}
        </button>

        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}
      </form>
    </div>
  );
}
