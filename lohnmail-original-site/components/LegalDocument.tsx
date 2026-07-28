import Link from "next/link";

type LegalDocumentProps = {
  eyebrow: string;
  title: string;
  intro: string;
  children: React.ReactNode;
};

export default function LegalDocument({
  eyebrow,
  title,
  intro,
  children,
}: LegalDocumentProps) {
  return (
    <>
      <section className="page-intro legal-intro">
        <div className="container">
          <span className="eyebrow">{eyebrow}</span>
          <h1>{title}</h1>
          <p>{intro}</p>
        </div>
      </section>

      <section className="section page-section legal-page">
        <div className="container legal-layout">
          <nav className="legal-nav" aria-label="Rechtliche Informationen">
            <span>Rechtliches</span>
            <Link href="/impressum">Impressum</Link>
            <Link href="/datenschutz">Datenschutz</Link>
            <Link href="/agb">AGB</Link>
            <Link href="/widerrufsbelehrung">Widerruf</Link>
          </nav>

          <article className="legal-document">
            {children}
            <p className="legal-updated">Stand: 27. Juli 2026</p>
          </article>
        </div>
      </section>
    </>
  );
}
