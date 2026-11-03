// Deterministic topographic contours around two "peaks". Rendered on the
// server; the only motion is a one-time draw-in (see .contour-line).

function ring(cx, cy, r, seed, points = 72) {
  const pts = [];
  for (let i = 0; i < points; i++) {
    const a = (i / points) * Math.PI * 2;
    const wobble =
      1 +
      0.09 * Math.sin(a * 3 + seed) +
      0.05 * Math.sin(a * 5 + seed * 1.7) +
      0.03 * Math.cos(a * 7 + seed * 0.6);
    pts.push([cx + Math.cos(a) * r * wobble * 1.25, cy + Math.sin(a) * r * wobble * 0.82]);
  }
  // Smooth closed curve via midpoint quadratic Béziers.
  const mid = (p, q) => [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
  let d = `M${mid(pts[pts.length - 1], pts[0]).map((n) => n.toFixed(1)).join(" ")}`;
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    const m = mid(p, pts[(i + 1) % pts.length]);
    d += ` Q${p[0].toFixed(1)} ${p[1].toFixed(1)} ${m[0].toFixed(1)} ${m[1].toFixed(1)}`;
  }
  return `${d} Z`;
}

const PEAKS = [
  { cx: 860, cy: 210, rings: 11, step: 34, seed: 0.4 },
  { cx: 260, cy: 520, rings: 8, step: 38, seed: 2.1 },
];

export default function ContourField({ className = "" }) {
  return (
    <svg
      viewBox="0 0 1200 700"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      aria-hidden="true"
      fill="none"
    >
      {PEAKS.map((peak, pi) =>
        Array.from({ length: peak.rings }, (_, i) => (
          <path
            key={`${pi}-${i}`}
            className="contour-line"
            d={ring(peak.cx, peak.cy, 18 + i * peak.step, peak.seed + i * 0.35)}
            stroke="var(--contour)"
            strokeWidth={i % 4 === 3 ? 1.6 : 1}
            style={{ animationDelay: `${i * 70 + pi * 200}ms` }}
          />
        )),
      )}
    </svg>
  );
}