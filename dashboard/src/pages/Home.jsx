import HeroSection from "../components/HeroSection";
import StatsOverview from "../components/StatsOverview";
import CongestionChart from "../components/CongestionChart";
import RotationChart from "../components/RotationChart";

export default function Home() {
  return (
    <div>
      <HeroSection />
      <StatsOverview />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <CongestionChart />
        <RotationChart />
      </div>
     
    </div>
  );
}