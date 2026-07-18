import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // FastAPI endpoints intentionally use trailing slashes. Keeping the URL
  // unchanged prevents Next from redirecting the proxy request outside /backend.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: "http://127.0.0.1:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
