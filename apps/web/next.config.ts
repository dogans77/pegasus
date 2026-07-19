import type { NextConfig } from "next";
const apiOrigin = process.env.PEGASUS_API_ORIGIN ?? "http://127.0.0.1:8042";
const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  skipTrailingSlashRedirect: true,
  async rewrites() { return [{ source: "/backend/:path*", destination: `${apiOrigin}/:path*` }]; },
};
export default nextConfig;