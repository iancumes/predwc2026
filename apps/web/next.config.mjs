/** @type {import('next').NextConfig} */
// Default to a fully static export (`out/`) — the whole site is static JSON +
// pre-rendered pages, so it hosts for free anywhere (Vercel, Pages, any CDN)
// with no backend or serverless functions.  Set NEXT_OUTPUT=standalone for the
// Docker image. Data is read client-side from /data/*.json.
const output = process.env.NEXT_OUTPUT || "export";
const nextConfig = {
  reactStrictMode: true,
  output,
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },
};
export default nextConfig;
