/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Old Vite routes kept working for anyone with a bookmark.
  async redirects() {
    return [
      { source: "/upload", destination: "/#start", permanent: true },
      { source: "/analyze", destination: "/#start", permanent: true },
    ];
  },
};

export default nextConfig;