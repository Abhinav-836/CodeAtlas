import ContourField from "@/components/ContourField";
import UploadPanel from "@/components/UploadPanel";

const LEGEND = [
  {
    symbol: <span className="block h-3 w-3 rotate-45 bg-critical" />,
    title: "Hardcoded secrets",
    body: "API keys, tokens and passwords committed to the code, shown with the value redacted and the file and line where it lives.",
  },
  {
    symbol: <span className="block h-0 w-0 border-x-[7px] border-b-[12px] border-x-transparent border-b-high" />,
    title: "Risky patterns",
    body: "Calls like eval, raw SQL string building and disabled TLS checks, ranked from critical to low.",
  },
  {
    symbol: (
      <svg viewBox="0 0 16 16" className="h-4 w-4" aria-hidden="true">
        <circle cx="8" cy="8" r="6.5" fill="none" stroke="var(--medium)" strokeWidth="1.5" />
        <circle cx="8" cy="8" r="3" fill="none" stroke="var(--medium)" strokeWidth="1.5" />
      </svg>
    ),
    title: "Complexity hot spots",
    body: "The files with the most branching logic, per-language function and class counts, and how exact each measurement is.",
  },
  {
    symbol: <span className="block h-3 w-3 rounded-full bg-accent" />,
    title: "Plain-English summary",
    body: "An AI-written overview of the architecture and the first things worth fixing, when the AI service is available.",
  },
];

const STEPS = [
  ["Point it at code", "Paste a public GitHub link or upload a ZIP of your project."],
  ["Let it survey", "The scan usually finishes in under a minute for small and medium repos."],
  ["Read and export", "Open the report here, or download it as JSON, HTML, Markdown or PDF."],
];

export default function HomePage() {
  return (
    <>
      <section className="relative overflow-hidden border-b border-rule">
        <ContourField className="pointer-events-none absolute inset-0 h-full w-full" />
        {/* Fade the map out behind the headline so the text stays crisp */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-gradient-to-r from-paper via-paper/80 to-transparent lg:via-paper/60" />
        <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 md:py-20 lg:grid-cols-[1.1fr_1fr] lg:items-center lg:gap-16">
          <div>
            <h1 className="max-w-[16ch] text-[2.5rem] font-semibold sm:text-6xl">
              Find what&rsquo;s buried in a codebase before it ships.
            </h1>
            <p className="mt-6 max-w-[52ch] text-lg text-muted">
              CodeAtlas reads every file in a repository and maps where the trouble is: leaked secrets, risky calls and the
              tangled files nobody wants to touch.
            </p>
          </div>
          <div id="start" className="scroll-mt-24">
            <UploadPanel />
          </div>
        </div>
      </section>

      <section aria-labelledby="legend-heading" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 md:py-20">
        <div className="grid gap-10 lg:grid-cols-[1fr_2fr] lg:gap-16">
          <div>
            <h2 id="legend-heading" className="text-3xl font-semibold">
              Reading the map
            </h2>
            <p className="mt-4 max-w-[40ch] text-muted">
              Every report uses the same legend, so you can compare one repository against another at a glance.
            </p>
          </div>
          <dl className="divide-y divide-rule border-y border-rule">
            {LEGEND.map((item) => (
              <div key={item.title} className="grid grid-cols-[1.5rem_1fr] gap-x-4 gap-y-1 py-5 sm:grid-cols-[1.5rem_14rem_1fr]">
                <span className="mt-1.5 flex justify-center">{item.symbol}</span>
                <dt className="font-medium">{item.title}</dt>
                <dd className="col-start-2 text-muted sm:col-start-3">{item.body}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section aria-labelledby="how-heading" className="border-t border-rule bg-surface">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 md:py-20">
          <h2 id="how-heading" className="text-3xl font-semibold">
            How it works
          </h2>
          <ol className="mt-10 grid gap-8 md:grid-cols-3">
            {STEPS.map(([title, body], i) => (
              <li key={title} className="border-t-2 border-ink pt-4">
                <span className="font-display text-sm text-muted">Step {i + 1}</span>
                <h3 className="mt-1 text-xl font-semibold">{title}</h3>
                <p className="mt-2 text-muted">{body}</p>
              </li>
            ))}
          </ol>
          <a
            href="#start"
            className="mt-12 inline-flex rounded-lg bg-ink px-5 py-3 font-medium text-paper transition-opacity hover:opacity-90"
          >
            Analyze a repository
          </a>
        </div>
      </section>
    </>
  );
}