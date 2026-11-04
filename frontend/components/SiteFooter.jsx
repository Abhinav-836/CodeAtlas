export default function SiteFooter() {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p>CodeAtlas keeps your reports private to this browser. No account needed.</p>
        <p>
          Built by{" "}
          <a
            href="https://github.com/Abhinav-836"
            className="text-ink underline decoration-rule underline-offset-4 hover:decoration-ink"
          >
            Abhinav Ashutosh
          </a>
        </p>
      </div>
    </footer>
  );
}