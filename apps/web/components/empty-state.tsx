import Link from "next/link";

export function EmptyState({
  icon,
  title,
  description,
  href,
  action
}: Readonly<{
  icon: string;
  title: string;
  description: string;
  href?: string;
  action?: string;
}>) {
  return (
    <div className="empty-state">
      <span aria-hidden="true">{icon}</span>
      <h2>{title}</h2>
      <p>{description}</p>
      {href && action ? <Link className="button primary" href={href}>{action}</Link> : null}
    </div>
  );
}
