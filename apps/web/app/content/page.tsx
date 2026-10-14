import { ContentSearchExperience } from "@/components/content-search-experience";
import { PageAutoRefresh } from "@/components/page-auto-refresh";
import { getContent, getDashboard, getSourceAnalysis } from "@/lib/api";

type SearchParams = Promise<{
  q?: string;
  type?: string;
  stream?: string;
  source?: string;
  tab?: string;
  page?: string;
}>;

export const metadata = { title: "Learning Files" };

export default async function ContentPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const [initialData, dashboard, sourceAnalysis] = await Promise.all([
    getContent({
      page,
      pageSize: 18,
      query: params.q,
      contentType: params.type,
      stream: params.stream,
      sourceId: params.source,
      sheetName: params.tab
    }),
    getDashboard(),
    getSourceAnalysis()
  ]);
  return (
    <>
      <PageAutoRefresh minutes={5} />
      <ContentSearchExperience
        initialData={initialData}
        dashboard={dashboard}
        sourceAnalysis={sourceAnalysis}
        initialQuery={params.q ?? ""}
        initialType={params.type ?? ""}
        initialStream={params.stream ?? ""}
        initialSource={params.source ?? ""}
        initialTab={params.tab ?? ""}
      />
    </>
  );
}
