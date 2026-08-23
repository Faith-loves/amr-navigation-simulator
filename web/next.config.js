const path = require("path");

const localApiOrigin = process.env.AMR_API_ORIGIN || ["http://", "127.0.0.1", ":8787"].join("");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  turbopack: {
    root: path.resolve(__dirname)
  },
  async rewrites() {
    if (process.env.NODE_ENV !== "development") {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: `${localApiOrigin}/api/:path*`
      }
    ];
  }
};

module.exports = nextConfig;