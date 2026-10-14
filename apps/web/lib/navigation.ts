export const navigation = [
  ["Today", "/", "⌂"],
  ["Weekly Timetable", "/timetable", "▦"],
  ["Learning Files", "/content", "▶"],
  ["Google Sheets", "/sources", "⌗"],
  ["Sheet Updates", "/changes", "↻"],
  ["Test Monitor", "/tests", "✓"],
  ["QR Generator", "/qr", "＋"],
  ["QR Templates", "/qr/templates", "◫"],
  ["Bulk QR", "/qr/bulk", "▦"],
  ["My QR Codes", "/qr/codes", "⌗"],
  ["QR Analytics", "/qr/stats", "▥"],
  ["Geo & Device Analytics", "/qr/reports", "◎"],
  ["Notifications", "/notifications", "◌"],
  ["App Status", "/overview", "◫"]
] as const;

export type NavigationItem = (typeof navigation)[number];


export function resolveActiveNavigationHref(pathname: string, hrefs: readonly string[] = navigation.map(([, href]) => href)): string | null {
  const matches = hrefs
    .filter((href) => href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`))
    .sort((a, b) => b.length - a.length);
  return matches[0] ?? null;
}
