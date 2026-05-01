import type { NextConfig } from "next";

const apiBase = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Hide the on-screen Next.js dev indicator (the "N" badge bottom-left).
  // Build/runtime errors still surface via the regular error overlay.
  devIndicators: false,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiBase}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
