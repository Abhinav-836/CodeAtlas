import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import Button from "../components/UI/Button";
import Card from "../components/UI/Card";
import Loader from "../components/UI/Loader";
import Modal from "../components/UI/Modal";
import { reportsAPI } from "../utils/apiClient";
import { API_URL } from "../utils/constants";

export default function ReportsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const [selectedReport, setSelectedReport] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportFormat, setExportFormat] = useState("json");
  const [busy, setBusy] = useState(false);

  /* ======================
     FETCH REPORTS
  ====================== */
  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      setErrorMsg("");
      const { data } = await reportsAPI.listReports();
      setReports(data.reports ?? []);
    } catch (err) {
      console.error(err);
      setErrorMsg("Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchReportDetails = useCallback(async (reportId) => {
    try {
      const { data } = await reportsAPI.getReportSummary(reportId);
      setSelectedReport(data);
      setShowDetailModal(true);
    } catch (err) {
      console.error(err);
      setErrorMsg("Report not found");
    }
  }, []);

  useEffect(() => {
    fetchReports();
    const reportId = searchParams.get("report");
    if (reportId) fetchReportDetails(reportId);
  }, [fetchReports, fetchReportDetails, searchParams]);

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
    } catch (err) {
      console.error(err);
      setErrorMsg("Search failed");
    }
  };

  const handleDeleteReport = async () => {
    if (!selectedReport) return;
    setBusy(true);
    try {
      await reportsAPI.deleteReport(selectedReport.id);
      setShowDeleteModal(false);
      setShowDetailModal(false);
      setSelectedReport(null);
      await fetchReports();
    } catch (err) {
      console.error(err);
      setErrorMsg("Failed to delete report");
    } finally {
      setBusy(false);
    }
  };

  const handleExportReport = async () => {
    if (!selectedReport) return;
    setBusy(true);
    try {
      // Simplest path: hit the download URL directly. No temp files on
      // the server, no /api-prefix guesswork.
      const url = reportsAPI.downloadReportUrl(selectedReport.id, exportFormat);
      const link = document.createElement("a");
      link.href = url;
      link.rel = "noopener";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setShowExportModal(false);
    } catch (err) {
      console.error(err);
      setErrorMsg("Export failed");
    } finally {
      setBusy(false);
    }
  };

  /* ======================
     HELPERS
  ====================== */
  const formatDate = (date) => {
    if (!date) return "-";
    try {
      return new Date(date).toLocaleString("en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return date;
    }
  };

  const getSeverityBadge = (severity = "low") => {
    const styles = {
      critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
      high: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
      medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
      low: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
      none: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300",
    };
    const key = (severity || "none").toLowerCase();
    return (
      <span className={`px-2 py-1 rounded text-xs font-bold ${styles[key] || styles.none}`}>
        {key.toUpperCase()}
      </span>
    );
  };

  const humanSize = (bytes) => {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
      bytes /= 1024;
      i++;
    }
    return `${bytes.toFixed(1)} ${units[i]}`;
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
            className="flex-1 px-4 py-3 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
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

      {errorMsg && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400">
          ⚠️ {errorMsg}
        </div>
      )}

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
              key={r.id}
              className="cursor-pointer hover:shadow-lg transition-shadow"
            >
              <div
                onClick={() => {
                  setSelectedReport(r);
                  setShowDetailModal(true);
                }}
              >
                <div className="flex justify-between mb-2">
                  <h3 className="font-bold truncate">
                    {r.filename ?? r.id}
                  </h3>
                  {getSeverityBadge(r.risk_level)}
                </div>

                <p className="text-sm text-gray-500 truncate" title={r.path}>
                  {r.path ?? "-"}
                </p>

                <p className="text-sm text-gray-500 mt-1">
                  {formatDate(r.created)}
                </p>

                <div className="grid grid-cols-2 gap-2 mt-4 text-center text-sm">
                  <div className="bg-gray-100 dark:bg-gray-800 p-2 rounded">
                    {r.files_analyzed ?? 0} files
                  </div>
                  <div className="bg-gray-100 dark:bg-gray-800 p-2 rounded">
                    {r.risk_score ?? 0}/100 risk
                  </div>
                </div>

                <div className="text-xs text-gray-500 mt-3">
                  {humanSize(r.size_bytes)}
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setSelectedReport(r);
                    setShowExportModal(true);
                  }}
                >
                  Export
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => {
                    setSelectedReport(r);
                    setShowDeleteModal(true);
                  }}
                >
                  Delete
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    navigate(`/reports?report=${encodeURIComponent(r.id)}`)
                  }
                >
                  View
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      <Modal
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
        title={selectedReport?.filename ?? "Report"}
        size="xl"
      >
        {selectedReport && (
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">ID</span>
              <span className="font-mono">{selectedReport.id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Path</span>
              <span className="truncate max-w-md">{selectedReport.path}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Analysis ID</span>
              <span className="font-mono">{selectedReport.analysis_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Created</span>
              <span>{formatDate(selectedReport.created)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Size</span>
              <span>{humanSize(selectedReport.size_bytes)}</span>
            </div>
          </div>
        )}
      </Modal>

      {/* Delete Confirmation */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Report"
        size="sm"
      >
        <p className="mb-6">
          Are you sure you want to delete{" "}
          <span className="font-mono">{selectedReport?.filename}</span>? This
          cannot be undone.
        </p>
        <div className="flex justify-end gap-3">
          <Button
            variant="outline"
            onClick={() => setShowDeleteModal(false)}
            disabled={busy}
          >
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDeleteReport} loading={busy}>
            Delete
          </Button>
        </div>
      </Modal>

      {/* Export Modal */}
      <Modal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        title="Export Report"
        size="sm"
      >
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">Format</label>
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
          >
            <option value="json">JSON</option>
            <option value="html">HTML</option>
            <option value="markdown">Markdown</option>
            <option value="pdf">PDF</option>
          </select>
        </div>
        <div className="flex justify-end gap-3">
          <Button
            variant="outline"
            onClick={() => setShowExportModal(false)}
            disabled={busy}
          >
            Cancel
          </Button>
          <Button onClick={handleExportReport} loading={busy}>
            Download
          </Button>
        </div>
      </Modal>
    </div>
  );
}