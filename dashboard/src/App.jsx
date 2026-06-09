import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import Layout from './components/Layout';
import Home from './pages/Home';
import Team from './pages/Team';
import TeamDetail from './pages/TeamDetail';
import Hypothesis from './pages/Hypothesis';
import DataSources from './pages/DataSources';
import PlayerMonitor from './pages/PlayerMonitor';
import PlayerDetail from './pages/PlayerDetail';
import ModelExplanation from './pages/ModelExplanation';

function App() {
  return (
    <QueryClientProvider client={queryClientInstance}>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <TooltipProvider delayDuration={200}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/teams" element={<Team />} />
            <Route path="/team/:teamId" element={<TeamDetail />} />
            <Route path="/hypotheses" element={<Hypothesis />} />
            <Route path="/data-sources" element={<DataSources />} />
            <Route path="/player-monitor" element={<PlayerMonitor />} />
            <Route path="/player/:playerId" element={<PlayerDetail />} />
            <Route path="/model-explanation" element={<ModelExplanation />} />
            <Route path="/model/:playerId" element={<ModelExplanation />} />
          </Route>
          <Route path="*" element={<PageNotFound />} />
        </Routes>
        </TooltipProvider>
        <Toaster />
      </Router>
    </QueryClientProvider>
  )
}

export default App
