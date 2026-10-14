import type { NextConfig } from "next";

const internalApiUrl = process.env.INTERNAL_API_URL ?? "http://127.0.0.1:3458";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  rewrites: async () => [
    { source: "/backend/:path*", destination: `${internalApiUrl}/:path*` }
  ],
  headers: async () => [
    {
      source: "/(.*)",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" }
      ]
    }
  ]
};

export default nextConfig;
