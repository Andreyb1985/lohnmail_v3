import nodemailer from "nodemailer";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type ContactRequest = {
  firmenname?: unknown;
  ansprechpartner?: unknown;
  email?: unknown;
  telefon?: unknown;
  mitarbeitende?: unknown;
  nachricht?: unknown;
  datenschutz?: unknown;
  website?: unknown;
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function readText(value: unknown, maxLength: number) {
  return typeof value === "string" ? value.trim().slice(0, maxLength) : "";
}

function readSingleLine(value: unknown, maxLength: number) {
  return readText(value, maxLength).replace(/\s+/g, " ");
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as ContactRequest;

    // Unsichtbares Honeypot-Feld: Bots erhalten eine neutrale Erfolgsantwort.
    if (readText(payload.website, 200)) {
      return NextResponse.json({ ok: true });
    }

    const data = {
      firmenname: readSingleLine(payload.firmenname, 160),
      ansprechpartner: readSingleLine(payload.ansprechpartner, 160),
      email: readSingleLine(payload.email, 254).toLowerCase(),
      telefon: readSingleLine(payload.telefon, 80),
      mitarbeitende: readSingleLine(payload.mitarbeitende, 40),
      nachricht: readText(payload.nachricht, 4000),
    };
    const privacyAccepted = payload.datenschutz === "on" || payload.datenschutz === true;

    if (
      !data.firmenname ||
      !data.ansprechpartner ||
      !EMAIL_PATTERN.test(data.email) ||
      !privacyAccepted
    ) {
      return NextResponse.json(
        { ok: false, error: "Bitte prüfen Sie die Pflichtfelder." },
        { status: 400 },
      );
    }

    const smtpUser = process.env.SMTP_USER;
    const smtpPass = process.env.SMTP_PASS;

    if (!smtpUser || !smtpPass) {
      console.error("SMTP configuration is incomplete.");
      return NextResponse.json(
        { ok: false, error: "Der E-Mail-Versand ist noch nicht konfiguriert." },
        { status: 503 },
      );
    }

    const smtpPort = Number(process.env.SMTP_PORT || "587");
    const smtpSecure = process.env.SMTP_SECURE === "true" || smtpPort === 465;
    const fromAddress = process.env.SMTP_FROM || smtpUser;
    const contactAddress = process.env.CONTACT_TO || "support@lohn-mail.de";

    const transporter = nodemailer.createTransport({
      host: process.env.SMTP_HOST || "smtp.gmail.com",
      port: smtpPort,
      secure: smtpSecure,
      requireTLS: !smtpSecure,
      connectionTimeout: 10_000,
      greetingTimeout: 10_000,
      socketTimeout: 15_000,
      auth: {
        user: smtpUser,
        pass: smtpPass,
      },
    });

    const optionalValue = (value: string, fallback: string) => value || fallback;
    const rows = [
      ["Firmenname", data.firmenname],
      ["Ansprechpartner", data.ansprechpartner],
      ["E-Mail", data.email],
      ["Telefonnummer", optionalValue(data.telefon, "Nicht angegeben")],
      ["Anzahl Mitarbeitende", optionalValue(data.mitarbeitende, "Nicht angegeben")],
    ];

    await transporter.sendMail({
      from: `"LohnMail Website" <${fromAddress}>`,
      to: contactAddress,
      replyTo: data.email,
      subject: `Testzugang-Anfrage: ${data.firmenname}`,
      text: [
        ...rows.map(([label, value]) => `${label}: ${value}`),
        "",
        "Nachricht:",
        optionalValue(data.nachricht, "Keine zusätzliche Nachricht."),
      ].join("\n"),
      html: `
        <h2>Neue Testzugang-Anfrage</h2>
        <table cellpadding="6" cellspacing="0" style="border-collapse:collapse">
          ${rows
            .map(
              ([label, value]) =>
                `<tr><td><strong>${escapeHtml(label)}</strong></td><td>${escapeHtml(value)}</td></tr>`,
            )
            .join("")}
        </table>
        <h3>Nachricht</h3>
        <p style="white-space:pre-wrap">${escapeHtml(
          optionalValue(data.nachricht, "Keine zusätzliche Nachricht."),
        )}</p>
      `,
    });

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error(
      "Contact form delivery failed:",
      error instanceof Error ? error.message : "Unknown SMTP error",
    );
    return NextResponse.json(
      { ok: false, error: "Die Anfrage konnte nicht gesendet werden. Bitte versuchen Sie es erneut." },
      { status: 502 },
    );
  }
}
