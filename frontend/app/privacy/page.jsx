import LegalPage, { CONTACT } from "@/components/LegalPage";

export const metadata = { title: "Privacy policy" };

export default function Privacy() {
  return (
    <LegalPage title="Privacy policy">
      <p>
        CodeAtlas is a free tool built by Abhinav Ashutosh (StrattonTrade) that scans a codebase for leaked secrets,
        risky patterns and complex files. There are no accounts. This page explains what happens to the code you
        give it. We don&rsquo;t sell data or use it for advertising.
      </p>

      <h2>What we handle</h2>
      <ul>
        <li>
          <strong>Your code:</strong> the public GitHub repository you name, or the ZIP file you upload, is copied to
          our server so it can be scanned. The copy sits on the server&rsquo;s temporary disk, which is wiped whenever
          the server restarts or is updated. We don&rsquo;t read it ourselves.
        </li>
        <li>
          <strong>Reports:</strong> each report (file names, findings, scores and the AI summary) is saved in our
          database so you can come back to it. Secrets found in your code are masked in the report: only their first
          and last few characters are kept.
        </li>
        <li>
          <strong>A browser key:</strong> your browser gets a random key, kept in its local storage, that marks which
          reports are yours. It isn&rsquo;t linked to your name or email. Anyone with your key can see your reports, so
          don&rsquo;t share it.
        </li>
        <li>
          <strong>Share links:</strong> if you create one, anyone with the link can view that report (read-only)
          until you revoke it.
        </li>
        <li>
          <strong>Server logs and limits:</strong> your IP address and request times, used to stop abuse and apply
          the daily analysis limit.
        </li>
        <li>
          <strong>Visit statistics:</strong> Vercel Web Analytics counts page views and visitors without cookies and
          without storing personal information.
        </li>
      </ul>

      <h2>The AI summary</h2>
      <p>
        The summary is written by an AI model hosted by Ollama. It receives only the scan&rsquo;s numbers (counts,
        risk level, languages) and up to three file names, never your source code or the secrets themselves.
      </p>

      <h2>Who else handles it</h2>
      <ul>
        <li>Render runs the server, Vercel hosts the website, and Neon hosts the database.</li>
        <li>Ollama writes the AI summary from the numbers above.</li>
        <li>GitHub serves the repositories you ask us to clone.</li>
      </ul>

      <h2>Deleting your data</h2>
      <p>
        You can delete any of your reports from <strong>My reports</strong>, which removes it from the database. To
        have everything linked to your browser key deleted, email <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
      </p>

      <h2>Security</h2>
      <p>
        Everything travels over HTTPS, and only your browser key can see your reports. No system is perfectly secure,
        so don&rsquo;t upload code you aren&rsquo;t allowed to share.
      </p>

      <h2>Contact</h2>
      <p>
        Questions: <a href={`mailto:${CONTACT}`}>{CONTACT}</a>. If this policy changes, the date at the top changes too.
      </p>
    </LegalPage>
  );
}
