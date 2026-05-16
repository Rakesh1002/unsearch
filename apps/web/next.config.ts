import type { NextConfig } from "next"

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    typedRoutes: true,
  },
  // Proxy API calls to the Worker in dev so we don't hit CORS.
  async rewrites() {
    if (process.env.NODE_ENV === "production") return []
    const apiTarget = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8787"
    return [{ source: "/api/v1/:path*", destination: `${apiTarget}/api/v1/:path*` }]
  },
}

export default config
