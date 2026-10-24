import { useEffect } from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import HomePage from "./pages/HomePage";
import UploadPage from "./pages/UploadPage";
import AnalyzePage from "./pages/AnalyzePage";
import ResultsPage from "./pages/ResultsPage";
import ReportsPage from "./pages/ReportsPage";

// React Router keeps the previous page's scroll position on navigation,
// so /upload -> /analyze -> /results opened scrolled to the bottom.
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

function NotFound() {
  return (
    <div className="container mx-auto px-4 py-24 text-center">
      <div className="text-6xl mb-4">🧭</div>
      <h1 className="text-3xl font-bold mb-2">Page not found</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        The page you&apos;re looking for doesn&apos;t exist.
      </p>
      <Link to="/" className="text-blue-600 hover:underline">
        Back to home
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <Layout>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/results/:taskId" element={<ResultsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Layout>
  );
}