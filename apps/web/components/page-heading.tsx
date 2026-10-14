export function PageHeading({
  eyebrow,
  title,
  description,
  actions
}: Readonly<{
  eyebrow: string;
  title: string;
  description: string;
  actions?: React.ReactNode;
}>) {
  return (
    <section className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions ? <div className="heading-actions">{actions}</div> : null}
    </section>
  );
}
