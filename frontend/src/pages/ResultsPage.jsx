import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import Button from '../components/UI/Button';
import Card from '../components/UI/Card';
import ProgressBar from '../components/UI/ProgressBar';
import AnalysisChart from '../components/Charts/AnalysisChart';
import { useAnalysis } from '../hooks/useAnalysis';
import ReactMarkdown from 'react-markdown';
import { SEVERITY_COLORS } from '../utils/constants';

const ResultsPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiExpanded, setAiExpanded] = useState(false);
  
  // Use the analysis hook to get real-time status
  const { status, progress, results, error: analysisError } = useAnalysis(taskId);

  useEffect(() => {
    if (results) {
      setResult(results);
      setLoading(false);
      
      // If AI insights are not present, fetch them
      if (!results.ai_insights && !aiLoading) {
        fetchAIInsights();
      }
    }
  }, [results]);

  useEffect(() => {
    if (analysisError) {
      setError(analysisError);
      setLoading(false);
    }
  }, [analysisError]);

  const fetchAIInsights = async () => {
    setAiLoading(true);
    try {
      const response = await axios.get(`http://localhost:8000/api/analyze/results/${taskId}?include_ai=true`);
      if (response.data.ai_insights) {
        setResult(prev => ({ ...prev, ai_insights: response.data.ai_insights }));
      }
    } catch (err) {
      console.error("Failed to fetch AI insights:", err);
    } finally {
      setAiLoading(false);
    }
  };

  const getRiskColor = (level) => {
    const colors = {
      critical: 'bg-red-600',
      high: 'bg-orange-500',
      medium: 'bg-yellow-500',
      low: 'bg-green-500',
      none: 'bg-gray-500'
    };
    return colors[level] || colors.none;
  };

  const getRiskBadge = (level) => {
    const colors = {
      critical: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
      high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
      medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
      low: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
      none: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300'
    };
    return colors[level] || colors.none;
  };

  const getSeverityBadge = (severity) => {
    return SEVERITY_COLORS[severity] || SEVERITY_COLORS.info;
  };

  // Show progress while analysis is running
  if (status !== 'completed' || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 py-12">
        <div className="container mx-auto px-4 max-w-2xl">
          <Card className="p-8 text-center bg-white/95 backdrop-blur">
            <div className="mb-6">
              <div className="w-24 h-24 mx-auto mb-4 relative">
                <div className="absolute inset-0 rounded-full bg-blue-500 animate-ping opacity-20"></div>
                <div className="absolute inset-2 rounded-full bg-gradient-to-r from-blue-600 to-purple-600 flex items-center justify-center">
                  <span className="text-4xl animate-pulse">🤖</span>
                </div>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                AI Analysis in Progress
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Please wait while our AI analyzes your code
              </p>
            </div>
            
            <div className="mb-8">
              <div className="flex justify-between items-center mb-4">
                <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">Status:</span>
                <span className="px-4 py-2 bg-blue-100 dark:bg-blue-900 rounded-full text-blue-800 dark:text-blue-200 font-medium capitalize">
                  {status || "Starting..."}
                </span>
              </div>
              
              <div className="mt-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600 dark:text-gray-400">Progress</span>
                  <span className="font-bold text-blue-600 dark:text-blue-400">{progress}%</span>
                </div>
                <ProgressBar value={progress} max={100} className="h-4" />
              </div>

              <div className="mt-4 text-sm text-gray-500">
                Task ID: <span className="font-mono">{taskId}</span>
              </div>
            </div>

            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg mb-4">
                <p className="text-red-600 dark:text-red-400">⚠️ {error}</p>
              </div>
            )}

            <Button variant="outline" onClick={() => navigate('/upload')} className="mt-4">
              Upload Another Repository
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 py-12">
        <div className="container mx-auto px-4 max-w-lg">
          <Card className="p-8 text-center bg-white/95 backdrop-blur">
            <div className="text-6xl mb-4">❌</div>
            <h2 className="text-2xl font-bold mb-2">Error Loading Results</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
            <Button onClick={() => navigate('/upload')} variant="primary">
              Try Again
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 py-8">
      <div className="container mx-auto px-4 max-w-7xl">
        {/* Header with AI Badge */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 mb-6">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center gap-4 mb-4 md:mb-0">
              <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center">
                <span className="text-3xl">🤖</span>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">AI Analysis Results</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  Repository: {result?.repo_name || result?.path?.split('/').pop() || 'Unknown'}
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className={`px-4 py-2 rounded-lg text-white text-center ${getRiskColor(result?.overall_risk_level)}`}>
                <div className="text-xs opacity-90">Risk Level</div>
                <div className="font-bold text-lg">{result?.overall_risk_level?.toUpperCase() || 'UNKNOWN'}</div>
              </div>
              <div className="bg-gray-800 dark:bg-gray-700 px-4 py-2 rounded-lg text-white text-center">
                <div className="text-xs opacity-90">Risk Score</div>
                <div className="font-bold text-lg">{result?.overall_risk_score || 0}/100</div>
              </div>
            </div>
          </div>

          {/* Analysis Info - AI Model Removed */}
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-gray-600 dark:text-gray-400">Analysis Time:</span>
              <span className="font-bold">{result?.performance?.analysis_duration_seconds?.toFixed(2)}s</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-600 dark:text-gray-400">Files Analyzed:</span>
              <span className="font-bold">{result?.summary?.total_files}</span>
            </div>
          </div>
        </div>

        {/* Stats Cards with AI Insights */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card className="p-4 hover:shadow-lg transition-shadow">
            <div className="flex items-center gap-3">
              <div className="text-3xl bg-blue-100 dark:bg-blue-900 w-12 h-12 rounded-lg flex items-center justify-center">
                📁
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-600">{result?.summary?.total_files || 0}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Total Files</div>
              </div>
            </div>
          </Card>
          
          <Card className="p-4 hover:shadow-lg transition-shadow">
            <div className="flex items-center gap-3">
              <div className="text-3xl bg-green-100 dark:bg-green-900 w-12 h-12 rounded-lg flex items-center justify-center">
                📊
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">{result?.metrics?.total_lines?.toLocaleString() || 0}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Lines of Code</div>
              </div>
            </div>
          </Card>
          
          <Card className="p-4 hover:shadow-lg transition-shadow">
            <div className="flex items-center gap-3">
              <div className="text-3xl bg-purple-100 dark:bg-purple-900 w-12 h-12 rounded-lg flex items-center justify-center">
                🌐
              </div>
              <div>
                <div className="text-2xl font-bold text-purple-600">{result?.languages?.language_count || 0}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Languages</div>
              </div>
            </div>
          </Card>
          
          <Card className="p-4 hover:shadow-lg transition-shadow">
            <div className="flex items-center gap-3">
              <div className="text-3xl bg-orange-100 dark:bg-orange-900 w-12 h-12 rounded-lg flex items-center justify-center">
                🔒
              </div>
              <div>
                <div className="text-2xl font-bold text-orange-600">{result?.security?.vulnerabilities_found || 0}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Issues Found</div>
              </div>
            </div>
          </Card>
        </div>

        {/* AI Summary Card - Prominently Displayed */}
        {(result?.ai_insights || aiLoading) && (
          <Card className="p-6 mb-6 border-2 border-blue-400 dark:border-blue-600">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center">
                <span className="text-xl">🤖</span>
              </div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">AI Executive Summary</h2>
              {aiLoading && (
                <div className="ml-auto flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-pink-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                  <span className="text-sm text-gray-500">AI generating insights...</span>
                </div>
              )}
            </div>
            
            {result?.ai_insights && !aiLoading && (
              <div className={`prose dark:prose-invert max-w-none transition-all ${!aiExpanded && 'max-h-96 overflow-hidden relative'}`}>
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-6 rounded-lg">
                  <ReactMarkdown
                    components={{
                      h1: ({node, ...props}) => <h1 className="text-2xl font-bold mt-4 mb-2" {...props} />,
                      h2: ({node, ...props}) => <h2 className="text-xl font-semibold mt-3 mb-2" {...props} />,
                      h3: ({node, ...props}) => <h3 className="text-lg font-medium mt-2 mb-1" {...props} />,
                      p: ({node, ...props}) => <p className="text-gray-700 dark:text-gray-300 mb-2" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-2" {...props} />,
                      li: ({node, ...props}) => <li className="text-gray-700 dark:text-gray-300" {...props} />,
                      code: ({node, inline, ...props}) => 
                        inline 
                          ? <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded" {...props} />
                          : <code className="block bg-gray-800 text-white p-3 rounded-lg overflow-x-auto" {...props} />
                    }}
                  >
                    {typeof result.ai_insights === 'string' 
                      ? result.ai_insights 
                      : result.ai_insights.summary || JSON.stringify(result.ai_insights, null, 2)}
                  </ReactMarkdown>
                </div>
                
                {!aiExpanded && (
                  <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white dark:from-gray-800 to-transparent"></div>
                )}
              </div>
            )}
            
            {result?.ai_insights && !aiLoading && (
              <button
                onClick={() => setAiExpanded(!aiExpanded)}
                className="mt-4 text-blue-600 dark:text-blue-400 hover:underline font-medium flex items-center gap-1"
              >
                {aiExpanded ? 'Show less' : 'Read more'}
                <span>{aiExpanded ? '↑' : '↓'}</span>
              </button>
            )}
          </Card>
        )}

        {/* Tabs Navigation */}
        <div className="flex flex-wrap gap-2 mb-6 bg-white dark:bg-gray-800 p-2 rounded-xl shadow">
          {['overview', 'security', 'complexity', 'languages', 'ai'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg capitalize font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              {tab === 'overview' && '📋 '}
              {tab === 'security' && '🔒 '}
              {tab === 'complexity' && '📊 '}
              {tab === 'languages' && '🌐 '}
              {tab === 'ai' && '🤖 '}
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <Card className="p-6 mb-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <span>📊</span> Key Metrics
                </h3>
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Total Files:</span>
                    <span className="font-bold">{result?.summary?.total_files}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Total Lines:</span>
                    <span className="font-bold">{result?.metrics?.total_lines?.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Languages:</span>
                    <span className="font-bold">{result?.languages?.language_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Primary Language:</span>
                    <span className="font-bold">{result?.languages?.primary_language}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Risk Score:</span>
                    <span className="font-bold">{result?.overall_risk_score}/100</span>
                  </div>
                </div>
              </div>

              {/* AI Quick Insights */}
              {result?.ai_insights && (
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <span>🤖</span> AI Quick Insights
                  </h3>
                  <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-4 rounded-lg">
                    <p className="text-gray-700 dark:text-gray-300">
                      {typeof result.ai_insights === 'string' 
                        ? result.ai_insights.split('\n')[0] 
                        : 'AI analysis complete. Check the AI tab for detailed insights.'}
                    </p>
                  </div>
                </div>
              )}

              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <span>💡</span> Recommendations
                </h3>
                <div className="space-y-3">
                  {result?.recommendations?.map((rec, index) => (
                    <div key={index} className={`p-4 rounded-lg border-l-4 ${
                      rec.priority === 'critical' ? 'border-l-red-600 bg-red-50 dark:bg-red-900/20' :
                      rec.priority === 'high' ? 'border-l-orange-500 bg-orange-50 dark:bg-orange-900/20' :
                      rec.priority === 'medium' ? 'border-l-yellow-500 bg-yellow-50 dark:bg-yellow-900/20' :
                      'border-l-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    }`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          rec.priority === 'critical' ? 'bg-red-200 text-red-800 dark:bg-red-800 dark:text-red-200' :
                          rec.priority === 'high' ? 'bg-orange-200 text-orange-800 dark:bg-orange-800 dark:text-orange-200' :
                          rec.priority === 'medium' ? 'bg-yellow-200 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-200' :
                          'bg-blue-200 text-blue-800 dark:bg-blue-800 dark:text-blue-200'
                        }`}>
                          {rec.priority.toUpperCase()}
                        </span>
                        <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">{rec.category}</span>
                      </div>
                      <h4 className="font-bold mb-1">{rec.title}</h4>
                      <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">{rec.description}</p>
                      <p className="text-sm text-blue-600 dark:text-blue-400">
                        <strong>Action:</strong> {rec.action}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Security Tab */}
          {activeTab === 'security' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 border-l-4 border-l-red-600 bg-red-50 dark:bg-red-900/20 rounded">
                  <div className="text-2xl font-bold text-red-600">{result?.security?.by_severity?.critical || 0}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Critical</div>
                </div>
                <div className="text-center p-4 border-l-4 border-l-orange-500 bg-orange-50 dark:bg-orange-900/20 rounded">
                  <div className="text-2xl font-bold text-orange-500">{result?.security?.by_severity?.high || 0}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">High</div>
                </div>
                <div className="text-center p-4 border-l-4 border-l-yellow-500 bg-yellow-50 dark:bg-yellow-900/20 rounded">
                  <div className="text-2xl font-bold text-yellow-500">{result?.security?.by_severity?.medium || 0}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Medium</div>
                </div>
                <div className="text-center p-4 border-l-4 border-l-blue-500 bg-blue-50 dark:bg-blue-900/20 rounded">
                  <div className="text-2xl font-bold text-blue-500">{result?.security?.by_severity?.low || 0}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Low</div>
                </div>
              </div>

              <AnalysisChart stats={{
                critical_issues: result?.security?.by_severity?.critical || 0,
                high_issues: result?.security?.by_severity?.high || 0,
                medium_issues: result?.security?.by_severity?.medium || 0,
                low_issues: result?.security?.by_severity?.low || 0,
              }} />

              {result?.security?.vulnerabilities?.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <span>🔍</span> Vulnerabilities Found
                  </h3>
                  <div className="space-y-4">
                    {result.security.vulnerabilities.map((vuln, idx) => (
                      <div key={idx} className="border-l-4 border-l-red-500 pl-4 py-2">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-sm bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                              {vuln.file.split('/').pop()}
                            </span>
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              Line {vuln.line}
                            </span>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs font-bold ${getSeverityBadge(vuln.severity)}`}>
                            {vuln.severity?.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-sm font-medium mb-2">{vuln.pattern}</p>
                        <pre className="mt-2 p-3 bg-gray-900 text-green-300 text-xs rounded-lg overflow-x-auto">
                          {vuln.context}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Complexity Tab */}
          {activeTab === 'complexity' && result?.python_analysis && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded">
                  <div className="text-2xl font-bold text-purple-600">{result.python_analysis.total_functions}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Functions</div>
                </div>
                <div className="text-center p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded">
                  <div className="text-2xl font-bold text-indigo-600">{result.python_analysis.total_classes}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Classes</div>
                </div>
                <div className="text-center p-4 bg-pink-50 dark:bg-pink-900/20 rounded">
                  <div className="text-2xl font-bold text-pink-600">{result.python_analysis.avg_complexity_score?.toFixed(2)}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Avg Complexity</div>
                </div>
                <div className="text-center p-4 bg-teal-50 dark:bg-teal-900/20 rounded">
                  <div className="text-2xl font-bold text-teal-600">{result.python_analysis.total_imports}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Imports</div>
                </div>
              </div>

              {result.python_analysis.most_complex_files?.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <span>📈</span> Most Complex Files
                  </h3>
                  <div className="space-y-3">
                    {result.python_analysis.most_complex_files.slice(0, 5).map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                        <div className="flex-1">
                          <div className="font-medium truncate max-w-md">{file.file.split('/').pop()}</div>
                          <div className="flex gap-4 text-xs text-gray-600 dark:text-gray-400 mt-1">
                            <span>Functions: {file.functions}</span>
                            <span>Classes: {file.classes}</span>
                            <span>Imports: {file.imports}</span>
                            <span>Lines: {file.lines}</span>
                          </div>
                        </div>
                        <div className="ml-4 px-3 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-300 rounded-full text-sm font-bold">
                          {file.complexity_score}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Languages Tab */}
          {activeTab === 'languages' && result?.languages?.detected_languages && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>🌐</span> Language Distribution
              </h3>
              {Object.entries(result.languages.detected_languages).map(([lang, data]) => (
                <div key={lang} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-bold">{lang}</span>
                    <span className="text-sm text-gray-600 dark:text-gray-400">{data.count} files</span>
                  </div>
                  <ProgressBar value={data.percentage} max={100} />
                  <p className="text-right text-sm text-gray-600 dark:text-gray-400 mt-1">{data.percentage}% of codebase</p>
                </div>
              ))}
            </div>
          )}

          {/* AI Insights Tab */}
          {activeTab === 'ai' && (
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>🤖</span> Detailed AI Analysis
              </h3>
              
              {aiLoading ? (
                <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="w-16 h-16 mx-auto mb-4 relative">
                    <div className="absolute inset-0 rounded-full bg-blue-500 animate-ping opacity-20"></div>
                    <div className="absolute inset-2 rounded-full bg-gradient-to-r from-blue-600 to-purple-600 flex items-center justify-center">
                      <span className="text-2xl animate-pulse">🤖</span>
                    </div>
                  </div>
                  <p className="text-gray-600 dark:text-gray-400">AI is generating insights...</p>
                </div>
              ) : result?.ai_insights ? (
                <div className="prose dark:prose-invert max-w-none">
                  <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-6 rounded-lg">
                    <ReactMarkdown
                      components={{
                        h1: ({node, ...props}) => <h1 className="text-2xl font-bold mt-4 mb-2" {...props} />,
                        h2: ({node, ...props}) => <h2 className="text-xl font-semibold mt-3 mb-2" {...props} />,
                        h3: ({node, ...props}) => <h3 className="text-lg font-medium mt-2 mb-1" {...props} />,
                        p: ({node, ...props}) => <p className="text-gray-700 dark:text-gray-300 mb-2" {...props} />,
                        ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-2" {...props} />,
                        li: ({node, ...props}) => <li className="text-gray-700 dark:text-gray-300" {...props} />,
                        code: ({node, inline, ...props}) => 
                          inline 
                            ? <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded" {...props} />
                            : <code className="block bg-gray-800 text-white p-3 rounded-lg overflow-x-auto" {...props} />
                      }}
                    >
                      {typeof result.ai_insights === 'string' 
                        ? result.ai_insights 
                        : result.ai_insights.summary || JSON.stringify(result.ai_insights, null, 2)}
                    </ReactMarkdown>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <p className="text-gray-600 dark:text-gray-400 mb-4">AI insights not available</p>
                  <Button onClick={fetchAIInsights} variant="secondary">
                    Generate AI Insights
                  </Button>
                </div>
              )}
            </div>
          )}
        </Card>

        {/* Action Buttons */}
        <div className="flex flex-wrap justify-center gap-4 mt-8">
          <Button
            onClick={() => window.open(`http://localhost:8000/api/reports/${result?.report_id}?format=html`, '_blank')}
            variant="primary"
            className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
          >
            <span className="flex items-center gap-2">
              <span>⬇️</span>
              <span>Download JSON</span>
            </span>
          </Button>
          <Button
            onClick={() => navigate('/upload')}
            variant="outline"
          >
            <span className="flex items-center gap-2">
              <span>📤</span>
              <span>New Analysis</span>
            </span>
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ResultsPage;