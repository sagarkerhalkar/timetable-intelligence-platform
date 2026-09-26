const UPSTREAM = process.env.INTERNAL_API_URL ?? "http://127.0.0.1:3550";

type RouteContext = Readonly<{
  params: Promise<{ path: string[] }>;
}>;

function cleanRequestHeaders(request: Request): Headers {
  const headers = new Headers(request.headers);
  for (const name of ["host", "connection", "content-length"]) headers.delete(name);
  return headers;
}

function cleanResponseHeaders(response: Response): Headers {
  const headers = new Headers(response.headers);
  for (const name of ["connection", "content-length", "content-encoding", "transfer-encoding"]) {
    headers.delete(name);
  }
  return headers;
}

async function proxy(request: Request, context: RouteContext): Promise<Response> {
  try {
    const { path } = await context.params;
    const incoming = new URL(request.url);
    const target = new URL(`/${path.map(encodeURIComponent).join("/")}`, UPSTREAM);
    target.search = incoming.search;

    const method = request.method.toUpperCase();
    const init: RequestInit = {
      method,
      headers: cleanRequestHeaders(request),
      cache: "no-store",
      redirect: "manual"
    };

    if (method !== "GET" && method !== "HEAD") {
      init.body = await request.arrayBuffer();
    }

    const upstream = await fetch(target, init);
    const body = await upstream.arrayBuffer();

    return new Response(body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: cleanResponseHeaders(upstream)
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown backend proxy failure";
    return Response.json(
      { detail: `Local data service proxy failed: ${message}` },
      { status: 502 }
    );
  }
}

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function GET(request: Request, context: RouteContext) { return proxy(request, context); }
export function POST(request: Request, context: RouteContext) { return proxy(request, context); }
export function PUT(request: Request, context: RouteContext) { return proxy(request, context); }
export function PATCH(request: Request, context: RouteContext) { return proxy(request, context); }
export function DELETE(request: Request, context: RouteContext) { return proxy(request, context); }
export function OPTIONS(request: Request, context: RouteContext) { return proxy(request, context); }
