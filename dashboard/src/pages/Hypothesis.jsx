import HypothesisCards from "../components/HypothesisCards";

export default function Hypotheses() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">Research Hypotheses</h1>
        <p className="text-muted-foreground">
          The four key hypotheses tested in the Fixture IQ analysis, with evidence and current status
        </p>
      </div>
      <HypothesisCards />
    </div>
  );
}