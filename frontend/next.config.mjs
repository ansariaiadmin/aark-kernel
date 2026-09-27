/** @type {import('next').NextConfig} */

// The browser talks to *this* origin only; Next proxies /api/v1/* to FastAPI.
// That removes the two wiring bugs the dashboard had:
//   1. relative fetch('/api/v1/...') calls hit the Next server and 404'd,
//   2. cross-origin calls to :8000 were blocked (no CORS was registered).
// AARK_BACKEND_ORIGIN is the server-side address of the API: inside docker
// compose it is http://backend:8000, on bare metal http://127.0.0.1:8000.
const BACKEND_ORIGIN = (
  process.env.AARK_BACKEND_ORIGIN ||
  process.env.BACKEND_ORIGIN ||
  'http://127.0.0.1:8000'
).replace(/\/+$/, '');

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  poweredByHeader: false,
  compress: true,
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${BACKEND_ORIGIN}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
