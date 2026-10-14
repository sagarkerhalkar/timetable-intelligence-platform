export default function Loading() {
  return (
    <section className="instant-loading-shell" aria-live="polite" aria-busy="true">
      <div className="instant-loading-head">
        <span className="instant-loading-pulse" />
        <div><strong>Opening…</strong><small>The page changed. Loading the latest local data.</small></div>
      </div>
      <div className="instant-loading-kpis">
        <i /><i /><i /><i />
      </div>
      <div className="instant-loading-lines"><i /><i /><i /><i /><i /></div>
    </section>
  );
}
