import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output for docker-compose -- ships only the traced
  // dependency subset + a minimal server, not the full node_modules tree.
  output: "standalone",
};

export default nextConfig;
