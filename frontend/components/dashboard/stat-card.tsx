import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: React.ReactNode;
  hint?: string;
  className?: string;
}

export function StatCard({ label, value, hint, className }: Props) {
  return (
    <Card className={cn("gap-2", className)}>
      <CardHeader className="pb-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="text-2xl font-semibold tabular-nums">{value}</div>
        {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
      </CardContent>
    </Card>
  );
}
