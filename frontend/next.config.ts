import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // Output File Tracing — menghasilkan .next/standalone/server.js yang dipakai
  // image Docker produksi. Wajib aktif untuk build Docker.
  output: 'standalone',
};

export default nextConfig;
