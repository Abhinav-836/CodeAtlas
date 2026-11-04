import Link from "next/link";
import Logo from "./Logo";

/*
 * Footer as a survey map's title block: the ruled box of cells printed in the
 * corner of every map sheet (title, surveyor, legend, scale).
 */
function ScaleBar() {
  return (
    <div aria-hidden="true">
      <div className="grid h-2 w-40 grid-cols-4 overflow-hidden rounded-sm border border-ink">
        <span className="bg-ink" />
        <span />
        <span className="bg-ink" />
        <span />
      </div>
      <div className="mt-1 flex w-40 justify-between text-[11px] tabular-nums text-muted">
        <span>0</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  );
}

const Cell = ({ label, children, className = "" }) => (
  <div className={`border-rule p-4 ${className}`}>
    <p className="text-xs text-muted">{label}</p>
    <div className="mt-1.5">{children}</div>
  </div>
);

export default function SiteFooter() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-auto">
      <div className="mx-auto max-w-6xl px-4 pb-10 pt-16 sm:px-6">
        <div className="grid border border-ink bg-surface text-sm sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <Cell label="Sheet" className="border-b sm:border-r lg:border-b-0">
            <p className="flex items-center gap-2 font-display text-lg font-semibold">
              <Logo className="h-6 w-6" /> CodeAtlas
            </p>
            <p className="mt-2 max-w-[32ch] text-muted">Maps the secrets, risky patterns and tangled files in any codebase.</p>
          </Cell>
          <Cell label="Routes" className="border-b lg:border-b-0 lg:border-r">
            <ul className="space-y-1">
              <li>
                <Link href="/#start" className="hover:text-accent">
                  Analyze a repository
                </Link>
              </li>
              <li>
                <Link href="/reports" className="hover:text-accent">
                  My reports
                </Link>
              </li>
              <li>
                <a href="https://github.com/Abhinav-836/CodeAtlas" className="hover:text-accent">
                  Source on GitHub
                </a>
              </li>
            </ul>
          </Cell>
          <Cell label="Surveyed by" className="border-b sm:border-b-0 sm:border-r">
            <a href="https://github.com/Abhinav-836" className="font-display text-base font-semibold hover:text-accent">
              Abhinav Ashutosh
            </a>
            <p className="mt-1 text-muted">Edition {year}</p>
          </Cell>
          <Cell label="Risk scale">
            <ScaleBar />
            <p className="mt-2 text-muted">Reports stay private to this browser.</p>
          </Cell>
        </div>
      </div>
    </footer>
  );
}