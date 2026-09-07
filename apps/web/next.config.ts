import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/health",
        destination: "http://api:8000/health",
      },
      {
        source: "/api/:path*",
        destination: "http://api:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
