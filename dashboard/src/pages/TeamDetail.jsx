import { useParams, Link } from "react-router-dom";
import { useTeam } from "@/hooks/useTeams";
import { useCongestionMetrics } from "@/hooks/useCongestionMetrics";
import { ArrowLeft, Calendar, Trophy, RotateCcw, TrendingUp } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend,
} from "recharts";

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-popover border border-border rounded-lg p-3 shadow-xl text-sm">
      <p className="font-semibold text-foreground mb-1.5">{label}</p>
      {payload.map((e) => (
        <p key={e.name} className="text-muted-foreground flex justify-between gap-4">
          <span>{e.name}:</span>
          <span className="font-medium text-foreground">{e.value}</span>
        </p>
      ))}
    </div>
  );
};

export default function TeamDetail() {
  const { teamId } = useParams();
  const { data: team, isLoading: teamLoading } = useTeam(teamId);
  const { data: metrics = [], isLoading: metricsLoading } = useCongestionMetrics();

  if (teamLoading || metricsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-muted border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  if (!team) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground">Team not found</p>
        <Link to="/teams" className="text-primary hover:underline text-sm mt-2 inline-block">Back to teams</Link>
      </div>
    );
  }

  const teamMetrics = metrics.filter((m) => m.team_name === team.name);
  const order = ["Low", "Medium", "High"];
  const sorted = [...teamMetrics].sort((a, b) => order.indexOf(a.congestion_level) - order.indexOf(b.congestion_level));

  const barData = sorted.map((m) => ({
    name: `${m.congestion_level}`,
    "Points/Match": m.points_per_match,
    "xG For": m.xg_for,
    "Win Rate %": m.win_rate,
  }));

  // Min-max normalize each metric across available congestion levels (0–100)
  const radarRaw = sorted.map((m) => ({
    level: m.congestion_level,
    pts: m.points_per_match || 0,
    xg: m.xg_for || 0,
    win: m.win_rate || 0,
    rot: m.rotation_index || 0,
  }));
  const normalize = (arr) => {
    const min = Math.min(...arr), max = Math.max(...arr);
    if (max === min) return arr.map(() => 50);
    return arr.map((v) => ((v - min) / (max - min)) * 100);
  };
  const ptsN = normalize(radarRaw.map((d) => d.pts));
  const xgN = normalize(radarRaw.map((d) => d.xg));
  const winN = normalize(radarRaw.map((d) => d.win));
  const rotN = normalize(radarRaw.map((d) => d.rot));
  const valAt = (norm, level) => {
    const i = radarRaw.findIndex((d) => d.level === level);
    return i >= 0 ? +norm[i].toFixed(1) : 0;
  };

  return (
    <div>
      <Link to="/teams" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Teams
      </Link>

      <div className="bg-card border border-border rounded-xl p-6 mb-6">
        <div className="flex items-center gap-4 mb-4">
          {team.logo_url ? (
            <img src={team.logo_url} alt={team.name} className="w-14 h-14 object-contain" />
          ) : (
            <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center">
              <Trophy className="w-7 h-7 text-primary" />
            </div>
          )}
          <div>
            <h1 className="text-2xl font-bold">{team.name}</h1>
            <p className="text-muted-foreground text-sm">{team.european_competition} · {team.season}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-muted/50 rounded-lg p-3">
            <Calendar className="w-4 h-4 text-accent mb-1" />
            <div className="text-xl font-bold">{team.total_matches || "—"}</div>
            <div className="text-xs text-muted-foreground">Total Matches</div>
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <TrendingUp className="w-4 h-4 text-primary mb-1" />
            <div className="text-xl font-bold">{team.overall_points_per_match || "—"}</div>
            <div className="text-xs text-muted-foreground">Pts/Match</div>
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <Calendar className="w-4 h-4 text-chart-3 mb-1" />
            <div className="text-xl font-bold">{team.avg_rest_days ? `${team.avg_rest_days}d` : "—"}</div>
            <div className="text-xs text-muted-foreground">Avg Rest Days</div>
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <RotateCcw className="w-4 h-4 text-chart-4 mb-1" />
            <div className="text-xl font-bold">{team.overall_rotation_index != null ? `${(team.overall_rotation_index * 100).toFixed(0)}%` : "—"}</div>
            <div className="text-xs text-muted-foreground">Avg Rotation</div>
          </div>
        </div>
      </div>

      {teamMetrics.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-card border border-border rounded-xl p-5">
            <h3 className="font-semibold mb-1">Performance by Congestion</h3>
            <p className="text-xs text-muted-foreground mb-4">How {team.short_name || team.name} performs under different fixture density</p>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} barGap={4}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(215 28% 20%)" />
                  <XAxis dataKey="name" tick={{ fill: "hsl(215 20% 55%)", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis yAxisId="left" tick={{ fill: "hsl(215 20% 55%)", fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, "auto"]} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fill: "hsl(215 20% 55%)", fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, 100]} label={{ value: "Win Rate %", angle: 90, position: "insideRight", offset: -5, style: { fill: "hsl(215 20% 55%)", fontSize: 11 } }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar yAxisId="left" dataKey="Points/Match" fill="hsl(217 91% 60%)" radius={[4, 4, 0, 0]} />
                  <Bar yAxisId="left" dataKey="xG For" fill="hsl(187 72% 50%)" radius={[4, 4, 0, 0]} />
                  <Bar yAxisId="right" dataKey="Win Rate %" fill="hsl(142 71% 45%)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-5">
            <h3 className="font-semibold mb-1">Congestion Impact Radar</h3>
            <p className="text-xs text-muted-foreground mb-4">Shows how performance (points, xG, win rate) changes across Low/Medium/High fixture congestion, alongside squad rotation rate — values are min-max normalized (0–100) per metric for comparison across levels</p>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={[
                  { metric: "Pts/Match", Low: valAt(ptsN, "Low"), Medium: valAt(ptsN, "Medium"), High: valAt(ptsN, "High") },
                  { metric: "xG", Low: valAt(xgN, "Low"), Medium: valAt(xgN, "Medium"), High: valAt(xgN, "High") },
                  { metric: "Win %", Low: valAt(winN, "Low"), Medium: valAt(winN, "Medium"), High: valAt(winN, "High") },
                  { metric: "Rotation", Low: valAt(rotN, "Low"), Medium: valAt(rotN, "Medium"), High: valAt(rotN, "High") },
                ]}>
                  <PolarGrid stroke="hsl(215 28% 20%)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: "hsl(215 20% 55%)", fontSize: 11 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Low" dataKey="Low" stroke="hsl(142 71% 45%)" fill="hsl(142 71% 45%)" fillOpacity={0.15} />
                  <Radar name="Medium" dataKey="Medium" stroke="hsl(38 92% 50%)" fill="hsl(38 92% 50%)" fillOpacity={0.15} />
                  <Radar name="High" dataKey="High" stroke="hsl(0 84% 60%)" fill="hsl(0 84% 60%)" fillOpacity={0.15} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-xl p-10 text-center">
          <p className="text-muted-foreground">No congestion data available for this team yet.</p>
        </div>
      )}

      {/* Metrics Table */}
      {teamMetrics.length > 0 && (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="p-5 border-b border-border">
            <h3 className="font-semibold">Detailed Metrics</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Level</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Matches</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Rest Days</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Pts/Match</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">xG For</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">xG Against</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Win %</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Rotation</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((m) => (
                  <tr key={m.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                    <td className="px-5 py-3 font-medium">
                      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold ${
                        m.congestion_level === "Low" ? "bg-chart-3/10 text-chart-3" :
                        m.congestion_level === "Medium" ? "bg-chart-4/10 text-chart-4" :
                        "bg-destructive/10 text-destructive"
                      }`}>
                        {m.congestion_level}
                      </span>
                    </td>
                    <td className="text-right px-5 py-3">{m.matches}</td>
                    <td className="text-right px-5 py-3">{m.avg_rest_days}d</td>
                    <td className="text-right px-5 py-3 font-semibold">{m.points_per_match}</td>
                    <td className="text-right px-5 py-3">{m.xg_for}</td>
                    <td className="text-right px-5 py-3">{m.xg_against}</td>
                    <td className="text-right px-5 py-3">{m.win_rate}%</td>
                    <td className="text-right px-5 py-3">{(m.rotation_index * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
