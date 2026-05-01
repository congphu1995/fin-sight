import { cn } from "@/lib/utils";

export function Section({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </div>
  );
}

export function BulletList({ items }: { items: string[] }) {
  if (!items?.length) return <div className="text-sm text-muted-foreground">—</div>;
  return (
    <ul className="list-disc space-y-1 pl-4 text-sm">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

export function KeyValueGrid({ entries }: { entries: Array<{ label: string; value: React.ReactNode }> }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
      {entries.map(({ label, value }) => (
        <div key={label} className="contents">
          <dt className="text-muted-foreground">{label}</dt>
          <dd className="font-medium tabular-nums">{value ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Empty({ message }: { message: string }) {
  return <div className="text-sm text-muted-foreground">{message}</div>;
}
