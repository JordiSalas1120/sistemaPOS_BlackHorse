/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      // Backend local en desarrollo
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/media/**",
      },
      // Backend en Docker (nombre del servicio)
      {
        protocol: "http",
        hostname: "backend",
        port: "8000",
        pathname: "/media/**",
      },
      // nginx en Docker (puerto 80)
      {
        protocol: "http",
        hostname: "localhost",
        port: "80",
        pathname: "/media/**",
      },
    ],
  },
};

module.exports = nextConfig;
