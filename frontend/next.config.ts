import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  turbopack: {
    root: frontendRoot,
  },
  output: "standalone",
  async redirects() {
    return [
      {
        source: "/register",
        destination: "/registro",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
