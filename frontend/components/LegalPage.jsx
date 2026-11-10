import Link from "next/link";

export const CONTACT = "ashutoshabhinavbachra0009@gmail.com";
export const UPDATED = "10 November 2026";

/** Shared layout for the privacy policy and terms of service. */
export default function LegalPage({ title, children }) {
  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6 md:py-16">
      <h1 className="text-4xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-muted">Last updated {UPDATED}</p>
      <article className="mt-8 leading-relaxed [&_a]:text-accent [&_a]:underline [&_a]:underline-offset-4 [&_h2]:mt-10 [&_h2]:mb-3 [&_h2]:text-xl [&_h2]:font-semibold [&_li]:ml-5 [&_li]:list-disc [&_p]:mt-3 [&_ul]:mt-3 [&_ul]:space-y-1.5">
        {children}
      </article>
      <p className="mt-12 flex gap-5 text-sm">
        <Link href="/" className="text-accent hover:underline">Home</Link>
        <Link href="/privacy" className="text-accent hover:underline">Privacy</Link>
        <Link href="/terms" className="text-accent hover:underline">Terms</Link>
      </p>
    </div>
  );
}
