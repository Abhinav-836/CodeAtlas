// Nested contour rings — a summit on a survey map.
export default function Logo({ className = "h-7 w-7" }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true" fill="none">
      <path d="M16 3C24 3 29 9 29 16S23 29 15 29 3 23 3 16 8 3 16 3Z" stroke="currentColor" strokeWidth="1.6" />
      <path d="M16.5 8.5C21 8.5 24 12 24 16s-3.5 7.5-8 7.5S8.5 20 8.5 16s3.5-7.5 8-7.5Z" stroke="currentColor" strokeWidth="1.6" opacity=".7" />
      <path d="M17 13c2 0 3 1.4 3 3s-1.4 3-3.2 3S14 17.7 14 16s1-3 3-3Z" fill="currentColor" />
    </svg>
  );
}