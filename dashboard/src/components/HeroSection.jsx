import { TrendingUp, Calendar, BarChart3 } from "lucide-react";
import { useTeams } from "@/hooks/useTeams";

const HERO_IMAGE = '/home_base_image.png';

export default function HeroSection() {
  const { data: teams = [] } = useTeams();
  const season = teams.length > 0 && teams[0].season ? teams[0].season : "Current";

  return (
    <div className="relative overflow-hidden rounded-2xl mb-8 bg-gradient-to-br from-card to-muted border border-border">
      <div className="absolute inset-0">
        <img src={HERO_IMAGE} alt="" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-r from-background via-background/90 to-background/40" />
      </div>
      <div className="relative z-10 px-6 py-12 md:px-10 md:py-16">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/20 text-primary text-xs font-semibold mb-4 backdrop-blur">
          <BarChart3 className="w-3 h-3" />
          Sports Analytics Research
        </div>
        <h1 className="text-3xl md:text-5xl font-bold tracking-tight mb-3 max-w-2xl leading-tight">
          {"Fixture Congestion &"}
          <br />
          <span className="text-primary">Premier League Performance</span>
        </h1>
        <p className="text-muted-foreground text-sm md:text-base max-w-xl leading-relaxed mb-6">
          A data-driven framework quantifying how match density affects competitive 
          performance and squad rotation in clubs competing across domestic and European competitions.
        </p>
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="w-4 h-4 text-accent" />
            <span className="text-muted-foreground">Season {season}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <TrendingUp className="w-4 h-4 text-accent" />
            <span className="text-muted-foreground">{"Premier League + UEFA"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
