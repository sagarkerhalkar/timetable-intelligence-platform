import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NextToppers QR",
  description: "NextToppers dynamic QR and verified scan intelligence",
  applicationName: "NextToppers",
};

export default function QrLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
