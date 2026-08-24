import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { About } from "./pages/About";
import { Analyzer } from "./pages/Analyzer";
import { Compare } from "./pages/Compare";
import { History } from "./pages/History";
import { Home } from "./pages/Home";
import { Network } from "./pages/Network";
import { Reports } from "./pages/Reports";
import { Results } from "./pages/Results";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/analyze" element={<Analyzer />} />
        <Route path="/results" element={<Results />} />
        <Route path="/results/:id" element={<Results />} />
        <Route path="/compare" element={<Compare />} />
        <Route path="/network" element={<Network />} />
        <Route path="/history" element={<History />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/about" element={<About />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
