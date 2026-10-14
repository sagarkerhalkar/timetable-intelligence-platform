import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NextToppers",
  description: "Opening your NextToppers content",
  applicationName: "NextToppers",
};

export default function PublicQrLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
