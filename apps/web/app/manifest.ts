import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "NextToppers",
    short_name: "NextToppers",
    description: "NextToppers QR and timetable intelligence",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#111827",
  };
}
