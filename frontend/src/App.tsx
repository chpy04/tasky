// src/App.tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import Tasks from "./pages/Tasks";
import Proposals from "./pages/Proposals";
import Ingestion from "./pages/Ingestion";
import Experiences from "./pages/Experiences";
import Prompts from "./pages/Prompts";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Tasks />} />
          <Route path="/proposals" element={<Proposals />} />
          <Route path="/ingestion" element={<Ingestion />} />
          <Route path="/experiences" element={<Experiences />} />
          <Route path="/prompts" element={<Prompts />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
