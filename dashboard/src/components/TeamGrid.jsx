import { useTeams } from "@/hooks/useTeams";
import { Link } from "react-router-dom";
import { ChevronRight, Trophy, Calendar, RotateCcw } from "lucide-react";

export default function TeamGrid() {
  const { data: teams = [], isLoading } = useTeams();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-card border border-border rounded-xl p-5 animate-pulse h-48" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {teams.map((team) => (
        <Link
          key={team.id}
          to={`/team/${team.id}`}
          className="bg-card border border-border rounded-xl p-5 hover:border-primary/40 transition-all group"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              {team.logo_url ? (
                <img src={team.logo_url} alt={team.name} className="w-10 h-10 object-contain" />
              ) : (
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Trophy className="w-5 h-5 text-primary" />
                </div>
              )}
              <div>
                <h3 className="font-semibold">{team.name}</h3>
                <p className="text-xs text-muted-foreground">{team.european_competition}</p>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">Matches</div>
              <div className="text-sm font-semibold">{team.total_matches || "—"}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">Avg Rest</div>
              <div className="text-sm font-semibold flex items-center gap-1">
                <Calendar className="w-3 h-3 text-accent" />
                {team.avg_rest_days ? `${team.avg_rest_days}d` : "—"}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-0.5">Rotation</div>
              <div className="text-sm font-semibold flex items-center gap-1">
                <RotateCcw className="w-3 h-3 text-chart-4" />
                {team.overall_rotation_index ? (team.overall_rotation_index * 100).toFixed(0) + "%" : "—"}
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
            <span className="text-xs text-muted-foreground">{team.season}</span>
            <span className="text-xs font-medium text-primary">
              {team.overall_points_per_match ? `${team.overall_points_per_match} pts/match` : ""}
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
