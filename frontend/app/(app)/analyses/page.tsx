import { CalendarClock, Clock, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function AnalysesPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Analyses</h1>
          <p className="text-sm text-muted-foreground">
            Schedule recurring agent runs and review their outputs.
          </p>
        </div>
        <Badge variant="outline">Coming soon</Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">What this will do</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-muted-foreground">
            Define a prompt and a schedule. The agent runs on cadence, persists the result, and shows
            the history here. Useful for weekly portfolio summaries, daily macro briefs, or
            ticker-specific watchlists.
          </p>
          <div className="grid gap-3 sm:grid-cols-3 pt-2">
            <FeatureRow
              icon={<Sparkles className="h-4 w-4" />}
              title="Pick an agent"
              body="Reuse the QA agent or any agent registered in the runtime."
            />
            <FeatureRow
              icon={<CalendarClock className="h-4 w-4" />}
              title="Set a cadence"
              body="Hourly, daily, weekly, or a raw cron expression."
            />
            <FeatureRow
              icon={<Clock className="h-4 w-4" />}
              title="Browse history"
              body="Every run is saved as a conversation you can open and inspect."
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Backend status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="text-muted-foreground">
            Phase 2 work — needs a scheduler + two new tables (<code>scheduled_analyses</code>,{" "}
            <code>analysis_runs</code>) and a small CRUD API. Once those land, this page wires up to
            them.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function FeatureRow({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-md border p-3">
      <div className="flex items-center gap-2 text-foreground">
        {icon}
        <span className="font-medium">{title}</span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{body}</p>
    </div>
  );
}
