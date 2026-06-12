import { memo } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const formatDate = (d) => {
  if (!d) return "";
  const date = new Date(d.split(" ")[0]);
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
};

const PANEL_HEIGHT = 96;
const SYNC_ID = "workload-timeline";

const _fmtLabel = (d) => {
  if (!d) return "";
  return String(d).split(" ")[0];
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-lg p-3 text-xs shadow-lg">
      <p className="font-semibold mb-1 text-foreground">{_fmtLabel(label)}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color }} className="text-foreground/90">{p.name}: {p.value}</p>
      ))}
    </div>
  );
};

const Panel = memo(function Panel({ data, dataKey, name, color, domain, showXAxis }) {
  return (
    <ResponsiveContainer width="100%" height={PANEL_HEIGHT}>
      <AreaChart data={data} syncId={SYNC_ID} margin={{ top: 2, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }} hide={!showXAxis} />
        <YAxis domain={domain} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }} />
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: "hsl(var(--muted-foreground))", strokeDasharray: "3 3" }} />
        <Area type="monotone" dataKey={dataKey} name={name} stroke={color} fill={`${color}/.12`} strokeWidth={1.5} dot={false} activeDot={{ r: 3, fill: color }} />
      </AreaChart>
    </ResponsiveContainer>
  );
});

const WorkloadTimeline = memo(function WorkloadTimeline({ data = [] }) {
  if (!data.length) return (
    <div className="bg-card border border-border rounded-xl p-6 text-center text-muted-foreground text-sm">
      No timeline data available.
    </div>
  );

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <h3 className="font-semibold mb-4">Workload Timeline (Last 8 Weeks)</h3>
      <div className="space-y-0">
        <div className="flex items-center gap-3 text-xs text-muted-foreground mb-1">
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm" style={{ background: "hsl(var(--primary))" }} />Rolling 14d (min)</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-1.5 rounded-sm" style={{ background: "hsl(var(--chart-4))" }} />Match (min)</span>
        </div>
        <div className="h-24">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} syncId={SYNC_ID} margin={{ top: 2, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }} hide={true} />
              <YAxis domain={["auto", "auto"]} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }} label={{ value: "min", position: "insideTopLeft", offset: -5, style: { fill: "hsl(var(--muted-foreground))", fontSize: 10 } }} />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: "hsl(var(--muted-foreground))", strokeDasharray: "3 3" }} />
              <Area type="monotone" dataKey="minutes" name="Rolling 14d" stroke="hsl(var(--primary))" fill="hsl(var(--primary)/.12)" strokeWidth={1.5} dot={false} activeDot={{ r: 3, fill: "hsl(var(--primary))" }} />
              <Area type="monotone" dataKey="minutes_played" name="Match" stroke="hsl(var(--chart-4))" fill="hsl(var(--chart-4)/.08)" strokeWidth={1.5} dot={false} activeDot={{ r: 3, fill: "hsl(var(--chart-4))" }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1 mt-2">
          <span className="w-2.5 h-2.5 rounded-sm" style={{ background: "hsl(var(--accent))" }} />
          <span>Rest Days</span>
        </div>
        <div className="h-24">
          <Panel data={data} dataKey="rest_days" name="Rest Days" color="hsl(var(--accent))" domain={["auto", "auto"]} showXAxis={false} />
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1 mt-2">
          <span className="w-2.5 h-2.5 rounded-sm" style={{ background: "hsl(var(--chart-5))" }} />
          <span>Fatigue Score</span>
        </div>
        <div className="h-24">
          <Panel data={data} dataKey="fatigue_score" name="Fatigue Score" color="hsl(var(--chart-5))" domain={["auto", "auto"]} showXAxis={true} />
        </div>
      </div>
    </div>
  );
});

export default WorkloadTimeline;
