import HeroSection from "../components/HeroSection";
import StatsOverview from "../components/StatsOverview";
import CongestionChart from "../components/CongestionChart";
import RotationChart from "../components/RotationChart";
import TeamGrid from "../components/TeamGrid";
import HypothesisCards from "../components/HypothesisCards";
import TeamRiskSummary from "../components/risk/TeamRiskSummary";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

export default function Home() {
  return (
    <div>
      <HeroSection />
      <StatsOverview />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <CongestionChart />
        <RotationChart />
      </div>

      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold">Player Risk Overview</h2>
            <p className="text-sm text-muted-foreground">XGBoost V4B — Squad risk distribution across all monitored teams</p>
          </div>
          <Link to="/player-monitor" className="text-sm text-primary hover:underline flex items-center gap-1">
            Full monitor <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <TeamRiskSummary />
      </div>

      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold">Research Hypotheses</h2>
            <p className="text-sm text-muted-foreground">Key findings from the analysis</p>
          </div>
          <Link to="/hypotheses" className="text-sm text-primary hover:underline flex items-center gap-1">
            View details <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <HypothesisCards compact />
      </div>

      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold">Teams Analysed</h2>
            <p className="text-sm text-muted-foreground">Premier League clubs competing in Europe</p>
          </div>
          <Link to="/teams" className="text-sm text-primary hover:underline flex items-center gap-1">
            All teams <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <TeamGrid />
      </div>
    </div>
  );
}