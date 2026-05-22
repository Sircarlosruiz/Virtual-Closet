import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
