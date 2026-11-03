import Link from "next/link";

export const metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 sm:px-6">
      <h1 className="text-4xl font-semibold">Off the map</h1>
      <p className="mt-4 text-muted">There&rsquo;s no page at this address. It may have moved, or the link was mistyped.</p>
      <Link href="/" className="mt-8 inline-block rounded-lg bg-ink px-4 py-2.5 font-medium text-paper hover:opacity-90">
        Go to the home page
      </Link>
    </div>
  );
}