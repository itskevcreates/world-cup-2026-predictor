/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ||
      "https://world-cup-2026-predictor-production-65ad.up.railway.app",
  },
};
export default nextConfig;
