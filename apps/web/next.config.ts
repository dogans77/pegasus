import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Local dashboard and API tools use both localhost and 127.0.0.1.
  // Explicit origins keep development HMR available without weakening public routes.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
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