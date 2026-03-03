import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import Button from "../components/UI/Button";
import Card from "../components/UI/Card";
import Loader from "../components/UI/Loader";
import Modal from "../components/UI/Modal";
import { reportsAPI } from "../utils/apiClient";

export default function ReportsPage() {
  const [searchParams] = useSearchParams();

  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const [selectedReport, setSelectedReport] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportFormat, setExportFormat] = useState("json");

  /* ======================
     FETCH REPORTS
  ====================== */
  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      const { data } = await reportsAPI.listReports();
      setReports(data.reports ?? []);
    } catch (err) {
      console.error(err);
      alert("Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchReportDetails = async (reportId) => {
    try {
      const { data } = await reportsAPI.getReport(reportId);
      setSelectedReport(data);
    } catch {
      alert("Report not found");
    }
  };

  useEffect(() => {
    fetchReports();

    const reportId = searchParams.get("report");
    if (reportId) fetchReportDetails(reportId);
  }, [fetchReports, searchParams]);

  /* ======================
     ACTIONS
  ====================== */
  const handleSearch = async (e) => {
    e.preventDefault();

    if (!searchQuery.trim()) {
      fetchReports();
      return;
    }

    try {
      const { data } = await reportsAPI.searchReports(searchQuery);
      setReports(data.reports ?? []);
    } catch {
      alert("Search failed");
    }
  };

  const handleDeleteReport = async () => {
    if (!selectedReport) return;

    try {
      await reportsAPI.deleteReport(selectedReport.report_id);
      setSelectedReport(null);
      setShowDeleteModal(false);
      fetchReports();
    } catch {
      alert("Failed to delete report");
    }
  };

  const handleExportReport = async () => {
    if (!selectedReport) return;

    try {
      const res = await reportsAPI.exportReport(
        selectedReport.report_id,
        exportFormat
      );

      if (res.data?.download_url) {
        const link = document.createElement("a");
        link.href = `http://localhost:8000${res.data.download_url}`;
        link.download = `${selectedReport.report_id}.${exportFormat}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }

      setShowExportModal(false);
    } catch {
      alert("Export failed");
    }
  };

  /* ======================
     HELPERS
  ====================== */
  const formatDate = (date) =>
    new Date(date).toLocaleString("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
    });

  const getSeverityBadge = (severity = "low") => {
    const styles = {
      critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
      high: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
      medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
      low: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
    };

    return (
      <span className={`px-2 py-1 rounded text-xs font-bold ${styles[severity]}`}>
        {severity.toUpperCase()}
      </span>
    );
  };

  /* ======================
     RENDER
  ====================== */
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <h1 className="text-3xl font-bold mb-2">Analysis Reports</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-8">
        View and manage your code analysis reports
      </p>

      <Card className="mb-6">
        <form onSubmit={handleSearch} className="flex gap-4">
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search reports..."
            className="flex-1 px-4 py-3 border rounded-lg dark:bg-gray-800"
          />
          <Button type="submit">🔍 Search</Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setSearchQuery("");
              fetchReports();
            }}
          >
            Reset
          </Button>
        </form>
      </Card>

      {loading ? (
        <div className="text-center py-16">
          <Loader size="lg" />
        </div>
      ) : reports.length === 0 ? (
        <Card className="text-center py-12">
          <div className="text-5xl mb-4">📄</div>
          <p>No reports found</p>
        </Card>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {reports.map((r) => (
            <Card
              key={r.report_id}
              onClick={() => setSelectedReport(r)}
              className="cursor-pointer hover:shadow-lg"
            >
              <div className="flex justify-between mb-2">
                <h3 className="font-bold truncate">
                  {r.filename ?? r.report_id}
                </h3>
                {getSeverityBadge(r.severity)}
              </div>

              <p className="text-sm text-gray-500">
                {formatDate(r.created_at)}
              </p>

              <div className="grid grid-cols-2 gap-2 mt-4 text-center text-sm">
                <div className="bg-gray-100 dark:bg-gray-800 p-2 rounded">
                  {r.stats?.files_analyzed ?? 0} files
                </div>
                <div className="bg-gray-100 dark:bg-gray-800 p-2 rounded">
                  {r.stats?.issues_found ?? 0} issues
                </div>
              </div>

              <div className="text-xs text-gray-500 mt-3">
                {(r.size ? r.size / 1024 : 0).toFixed(1)} KB
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Modals remain unchanged logic-wise */}
      {/* Your existing Modal JSX is compatible */}
    </div>
  );
}
