import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function MetricCard({
  title,
  value,
  detail,
  confidence
}: {
  title: string;
  value: string;
  detail?: string;
  confidence?: string;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{title}</CardTitle>
          {confidence ? <Badge tone={confidence === "verified" || confidence === "high" ? "success" : confidence === "medium" ? "neutral" : "warning"}>{confidence}</Badge> : null}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tracking-normal">{value}</div>
        {detail ? <div className="mt-1 text-sm text-muted-foreground">{detail}</div> : null}
      </CardContent>
    </Card>
  );
}
