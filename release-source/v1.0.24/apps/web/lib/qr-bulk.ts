export type BulkQrRow = { name: string; url: string };

function stripCsvQuotes(value: string): string {
  return value.trim().replace(/^"|"$/g, "");
}

export function parseBulkQrRows(raw: string): BulkQrRow[] {
  return raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const tab = line.split("\t");
      if (tab.length >= 2) {
        const name = (tab[0] ?? "").trim();
        const url = tab.slice(1).join("\t").trim();
        return { name, url };
      }

      const comma = line.split(",");
      if (comma.length >= 2) {
        const name = stripCsvQuotes(comma[0] ?? "");
        const url = stripCsvQuotes(comma.slice(1).join(","));
        return { name, url };
      }

      const match = line.match(/^(.*?)\s+(https?:\/\/\S+)$/i);
      if (match) {
        const name = (match[1] ?? "").trim();
        const url = (match[2] ?? "").trim();
        return { name, url };
      }

      return { name: line, url: "" };
    });
}
