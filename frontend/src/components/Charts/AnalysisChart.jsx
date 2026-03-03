import { useEffect, useRef } from 'react';
import Card from '../UI/Card';

export default function AnalysisChart({ stats }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!stats || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Prepare data
    const issuesData = [
      { label: 'Critical', value: stats.critical_issues || 0, color: '#ef4444' },
      { label: 'High', value: stats.high_issues || 0, color: '#f97316' },
      { label: 'Medium', value: stats.medium_issues || 0, color: '#eab308' },
      { label: 'Low', value: stats.low_issues || 0, color: '#3b82f6' },
    ].filter(item => item.value > 0);

    if (issuesData.length === 0) {
      // Show "No data" message
      ctx.font = '14px Arial';
      ctx.fillStyle = '#6b7280';
      ctx.textAlign = 'center';
      ctx.fillText('No issues found', canvas.width / 2, canvas.height / 2);
      return;
    }

    // Calculate total for percentages
    const total = issuesData.reduce((sum, item) => sum + item.value, 0);

    // Set up chart dimensions
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 40;

    // Draw pie chart
    let startAngle = 0;
    
    issuesData.forEach((item) => {
      const sliceAngle = (item.value / total) * 2 * Math.PI;
      
      // Draw slice
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
      ctx.closePath();
      ctx.fillStyle = item.color;
      ctx.fill();

      // Draw border
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw percentage label
      const labelAngle = startAngle + sliceAngle / 2;
      const labelRadius = radius * 0.7;
      const labelX = centerX + Math.cos(labelAngle) * labelRadius;
      const labelY = centerY + Math.sin(labelAngle) * labelRadius;

      const percentage = Math.round((item.value / total) * 100);
      
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 14px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${percentage}%`, labelX, labelY);

      startAngle += sliceAngle;
    });

    // Draw center circle for donut effect (optional)
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.4, 0, 2 * Math.PI);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw total in center
    ctx.fillStyle = '#111827';
    ctx.font = 'bold 20px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(total.toString(), centerX, centerY);

  }, [stats]);

  // Prepare legend data
  const legendItems = stats ? [
    { label: 'Critical', value: stats.critical_issues || 0, color: '#ef4444' },
    { label: 'High', value: stats.high_issues || 0, color: '#f97316' },
    { label: 'Medium', value: stats.medium_issues || 0, color: '#eab308' },
    { label: 'Low', value: stats.low_issues || 0, color: '#3b82f6' },
  ].filter(item => item.value > 0) : [];

  const total = legendItems.reduce((sum, item) => sum + item.value, 0);

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4 text-gray-700 dark:text-gray-300">
        Issues Distribution
      </h3>
      
      <div className="flex flex-col md:flex-row items-center gap-8">
        {/* Canvas Chart */}
        <div className="relative">
          <canvas
            ref={canvasRef}
            width={300}
            height={300}
            className="w-full max-w-[300px] h-auto"
          />
        </div>

        {/* Legend */}
        <div className="flex-1 space-y-3">
          {legendItems.map((item) => {
            const percentage = total > 0 ? Math.round((item.value / total) * 100) : 0;
            return (
              <div key={item.label} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div 
                    className="w-4 h-4 rounded" 
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {item.label}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {item.value} issues
                  </span>
                  <span className="text-sm font-bold w-12 text-right">
                    {percentage}%
                  </span>
                </div>
              </div>
            );
          })}

          {legendItems.length === 0 && (
            <p className="text-center text-gray-500 dark:text-gray-400 py-4">
              No issues to display
            </p>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      {legendItems.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t dark:border-gray-700">
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{stats.critical_issues || 0}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Critical</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-500">{stats.high_issues || 0}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">High</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-500">{stats.medium_issues || 0}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Medium</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-500">{stats.low_issues || 0}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Low</div>
          </div>
        </div>
      )}
    </Card>
  );
}