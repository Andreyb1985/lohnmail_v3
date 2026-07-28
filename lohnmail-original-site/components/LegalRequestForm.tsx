"use client";

import { useState } from "react";
import Link from "next/link";
import { CheckCircle } from "./icons";

type RequestMode = "withdrawal" | "cancellation";

export default function LegalRequestForm({ mode }: { mode: RequestMode }) {
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [receivedAt, setReceivedAt] = useState("");
  const isWithdrawal = mode === "withdrawal";

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSending(true);
    setError("");

    const formData = new FormData(event.currentTarget);
    const payload = Object.fromEntries(formData.entries());

    try {
      const response = await fetch("/api/legal-request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await response.json().catch(() => null)) as
        | { ok?: boolean; error?: string; receivedAt?: string }
        | null;

      if (!response.ok || !result?.ok) {
        throw new Error(
          result?.error || "Die Erklärung konnte nicht übermittelt werden.",
        );
      }

      setReceivedAt(result.receivedAt || "");
      setSent(true);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Die Erklärung konnte nicht übermittelt werden. Bitte versuchen Sie es erneut.",
      );
    } finally {
      setSending(false);
    }
  }

  if (sent) {
    return (
      <div className="contact-wrap legal-request-success" role="status">
        <div className="download-heading">
          <div className="success-icon">
            <CheckCircle size={28} />
          </div>
          <div>
            <h2>
              {isWithdrawal
                ? "Ihr Widerruf ist eingegangen."
                : "Ihre Kündigung ist eingegangen."}
            </h2>
            <p>
              Die Eingangsbestätigung wurde an Ihre E-Mail-Adresse gesendet.
            </p>
          </div>
        </div>
        {receivedAt ? (
          <p className="legal-request-time">
            Eingang: <strong>{receivedAt}</strong>
          </p>
        ) : null}
        <p>
          Bewahren Sie die Bestätigungs-E-Mail als Nachweis auf. Bei Rückfragen
          erreichen Sie uns unter{" "}
          <a href="mailto:support@lohn-mail.de">support@lohn-mail.de</a>.
        </p>
      </div>
    );
  }

  return (
    <div className="contact-wrap legal-request-wrap">
      <form className="form-grid" onSubmit={handleSubmit}>
        <input type="hidden" name="art" value={mode} />

        <div className="form-honeypot" aria-hidden="true">
          <label htmlFor={`${mode}-website`}>Website</label>
          <input
            id={`${mode}-website`}
            name="website"
            type="text"
            tabIndex={-1}
            autoComplete="off"
          />
        </div>

        <div className="form-field">
          <label htmlFor={`${mode}-name`}>Vor- und Nachname *</label>
          <input
            id={`${mode}-name`}
            name="name"
            type="text"
            required
            autoComplete="name"
          />
        </div>

        <div className="form-field">
          <label htmlFor={`${mode}-email`}>E-Mail für die Bestätigung *</label>
          <input
            id={`${mode}-email`}
            name="email"
            type="email"
            required
            autoComplete="email"
          />
        </div>

        <div className="form-field full">
          <label htmlFor={`${mode}-reference`}>
            Vertrags- oder Lizenzreferenz *
          </label>
          <input
            id={`${mode}-reference`}
            name="vertragsreferenz"
            type="text"
            required
            placeholder="z. B. Lizenzschlüssel, Rechnungsnummer oder Vertrags-E-Mail"
          />
        </div>

        {!isWithdrawal ? (
          <>
            <div className="form-field">
              <label htmlFor="kuendigungsart">Art der Kündigung *</label>
              <select
                id="kuendigungsart"
                name="kuendigungsart"
                defaultValue="ordentlich"
                required
              >
                <option value="ordentlich">Ordentliche Kündigung</option>
                <option value="ausserordentlich">
                  Außerordentliche Kündigung
                </option>
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="wunschdatum">Gewünschtes Vertragsende</label>
              <input id="wunschdatum" name="wunschdatum" type="date" />
            </div>

            <div className="form-field full">
              <label htmlFor="grund">
                Kündigungsgrund bei außerordentlicher Kündigung
              </label>
              <textarea id="grund" name="grund" rows={4} />
            </div>
          </>
        ) : (
          <div className="form-field full">
            <label htmlFor="mitteilung">Ergänzende Mitteilung</label>
            <textarea id="mitteilung" name="mitteilung" rows={4} />
          </div>
        )}

        <p className="legal-request-privacy">
          Hinweise zur Verarbeitung Ihrer Angaben finden Sie in der{" "}
          <Link href="/datenschutz">Datenschutzerklärung</Link>.
        </p>

        <button
          type="submit"
          className="btn btn-primary btn-lg"
          disabled={sending}
        >
          {sending
            ? "Wird übermittelt…"
            : isWithdrawal
              ? "Widerruf bestätigen"
              : "jetzt kündigen"}
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
