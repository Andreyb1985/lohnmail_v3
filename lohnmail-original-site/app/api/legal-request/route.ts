import nodemailer from "nodemailer";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type LegalRequest = {
  art?: unknown;
  name?: unknown;
  email?: unknown;
  vertragsreferenz?: unknown;
  kuendigungsart?: unknown;
  wunschdatum?: unknown;
  grund?: unknown;
  mitteilung?: unknown;
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
    const payload = (await request.json()) as LegalRequest;

    if (readText(payload.website, 200)) {
      return NextResponse.json({ ok: true });
    }

    const kind = readSingleLine(payload.art, 30);
    const isWithdrawal = kind === "withdrawal";
    const isCancellation = kind === "cancellation";
    if (!isWithdrawal && !isCancellation) {
      return NextResponse.json(
        { ok: false, error: "Ungültige Art der Erklärung." },
        { status: 400 },
      );
    }

    const data = {
      name: readSingleLine(payload.name, 180),
      email: readSingleLine(payload.email, 254).toLowerCase(),
      reference: readSingleLine(payload.vertragsreferenz, 300),
      cancellationType: readSingleLine(payload.kuendigungsart, 40),
      desiredDate: readSingleLine(payload.wunschdatum, 20),
      reason: readText(payload.grund, 3000),
      message: readText(payload.mitteilung, 3000),
    };

    if (!data.name || !EMAIL_PATTERN.test(data.email) || !data.reference) {
      return NextResponse.json(
        { ok: false, error: "Bitte prüfen Sie die Pflichtfelder." },
        { status: 400 },
      );
    }

    if (
      isCancellation &&
      !["ordentlich", "ausserordentlich"].includes(data.cancellationType)
    ) {
      return NextResponse.json(
        { ok: false, error: "Bitte wählen Sie die Art der Kündigung." },
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
    const received = new Date();
    const receivedAt = new Intl.DateTimeFormat("de-DE", {
      dateStyle: "medium",
      timeStyle: "long",
      timeZone: "Europe/Berlin",
    }).format(received);

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

    const requestLabel = isWithdrawal ? "Widerruf" : "Kündigung";
    const details = isWithdrawal
      ? [
          ["Erklärung", "Widerruf des LohnMail-Vertrags"],
          ["Ergänzende Mitteilung", data.message || "Keine"],
        ]
      : [
          [
            "Art der Kündigung",
            data.cancellationType === "ausserordentlich"
              ? "Außerordentliche Kündigung"
              : "Ordentliche Kündigung",
          ],
          [
            "Gewünschtes Vertragsende",
            data.desiredDate || "Zum nächstmöglichen Zeitpunkt",
          ],
          ["Kündigungsgrund", data.reason || "Nicht angegeben"],
        ];
    const rows = [
      ["Eingang", receivedAt],
      ["Name", data.name],
      ["E-Mail", data.email],
      ["Vertrags- oder Lizenzreferenz", data.reference],
      ...details,
    ];

    await transporter.sendMail({
      from: `"LohnMail" <${fromAddress}>`,
      to: data.email,
      bcc: contactAddress,
      replyTo: contactAddress,
      subject: `Eingangsbestätigung: ${requestLabel} Ihres LohnMail-Vertrags`,
      text: [
        `Wir bestätigen den Eingang Ihrer Erklärung am ${receivedAt}.`,
        "",
        ...rows.map(([label, value]) => `${label}: ${value}`),
        "",
        "Diese E-Mail bestätigt den Eingang. Die rechtliche Prüfung und Bearbeitung erfolgt gesondert.",
        "",
        "LohnMail",
        "Andrii Bakanov",
        "Große Leining 22",
        "45141 Essen",
        "support@lohn-mail.de",
      ].join("\n"),
      html: `
        <h2>Eingangsbestätigung: ${escapeHtml(requestLabel)}</h2>
        <p>Wir bestätigen den Eingang Ihrer Erklärung am <strong>${escapeHtml(receivedAt)}</strong>.</p>
        <table cellpadding="6" cellspacing="0" style="border-collapse:collapse">
          ${rows
            .map(
              ([label, value]) =>
                `<tr><td><strong>${escapeHtml(label)}</strong></td><td>${escapeHtml(value)}</td></tr>`,
            )
            .join("")}
        </table>
        <p>Diese E-Mail bestätigt den Eingang. Die rechtliche Prüfung und Bearbeitung erfolgt gesondert.</p>
        <p>LohnMail<br>Andrii Bakanov<br>Große Leining 22<br>45141 Essen<br>support@lohn-mail.de</p>
      `,
    });

    return NextResponse.json({ ok: true, receivedAt });
  } catch (error) {
    console.error(
      "Legal request delivery failed:",
      error instanceof Error ? error.message : "Unknown SMTP error",
    );
    return NextResponse.json(
      {
        ok: false,
        error:
          "Die Erklärung konnte nicht übermittelt werden. Bitte senden Sie sie per E-Mail an support@lohn-mail.de.",
      },
      { status: 502 },
    );
  }
}
