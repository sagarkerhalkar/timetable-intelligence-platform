import { redirect } from "next/navigation";

export default function LegacyQrAnalyticsPage() {
  redirect("/qr/stats");
}
