import Link from "next/link";
import LegalPage, { CONTACT } from "@/components/LegalPage";

export const metadata = { title: "Terms of service" };

export default function Terms() {
  return (
    <LegalPage title="Terms of service">
      <p>
        These terms cover your use of CodeAtlas, a free tool built by Abhinav Ashutosh (Kavorin Tech). By analyzing a
        repository or uploading a file, you agree to them.
      </p>

      <h2>Your code</h2>
      <ul>
        <li>Only analyze code you own or have permission to share. You keep all rights to your code.</li>
        <li>You let us copy and process it only to produce your report, as described in the <Link href="/privacy">privacy policy</Link>.</li>
      </ul>

      <h2>Acceptable use</h2>
      <p>
        Don&rsquo;t use CodeAtlas to break the law, to attack or overload the service, to get around its daily limits,
        or to upload malware. We may block access that does.
      </p>

      <h2>Reports are a starting point</h2>
      <p>
        Findings come from automated scans and an AI model. They can miss real problems and flag harmless code. A
        clean report doesn&rsquo;t mean your code is secure; it isn&rsquo;t a security audit or professional advice.
        If CodeAtlas finds a real secret, rotate it, since removing it from the code alone isn&rsquo;t enough.
      </p>

      <h2>The service</h2>
      <p>
        CodeAtlas is free and provided &ldquo;as is&rdquo;, without any guarantee that it will always be available or
        error-free, and reports may be removed if the service changes. To the extent the law allows, we are not
        liable for losses that come from using it. These terms are governed by the laws of India.
      </p>

      <h2>Contact</h2>
      <p>
        <a href={`mailto:${CONTACT}`}>{CONTACT}</a>. If these terms change, the date at the top changes too.
      </p>
    </LegalPage>
  );
}