"""
HTML export for analysis reports.
"""
from typing import Dict, Any
import json
from datetime import datetime


def export_html(report: Dict[str, Any]) -> str:
    """
    Export analysis report as HTML.
    
    Args:
        report: Analysis report dictionary
        
    Returns:
        HTML string
    """
    # Prepare data for template
    data = {
        'title': f"CodeAtlas Analysis: {report.get('path', 'Unknown')}",
        'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'report': report,
        'summary': report.get('summary', {}),
        'metrics': report.get('metrics', {}),
        'architecture': report.get('architecture', {}),
        'security': report.get('security', {}),
        'python_analysis': report.get('python_analysis', {}),
        'json_data': json.dumps(report, indent=2, default=str),
    }
    
    # Generate HTML sections
    security_html = _generate_security_html(report.get('security', {}))
    architecture_html = _generate_architecture_html(report.get('architecture', {}))
    python_html = _generate_python_html(report.get('python_analysis', {}))
    
    # Render template with all sections
    template = _get_html_template()
    html = template.format(
        title=data['title'],
        generated_date=data['generated_date'],
        report_path=report.get('path', 'Unknown'),
        analysis_id=report.get('analysis_id', 'N/A'),
        summary_total_files=data['summary'].get('total_files', 0),
        metrics_risk=data['metrics'].get('risk', 'unknown'),
        metrics_risk_score=data['metrics'].get('risk_score', 0),
        metrics_total_size_kb=data['metrics'].get('total_size_kb', 'N/A'),
        metrics_languages=', '.join(data['metrics'].get('languages', [])),
        security_html=security_html,
        architecture_html=architecture_html,
        python_html=python_html,
        json_data=data['json_data']
    )
    
    return html


def _get_html_template() -> str:
    """Get HTML template string."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .header h1 {{
            color: #2d3748;
            font-size: 2.5em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .header h1::before {{
            content: "🗺️";
            font-size: 1.2em;
        }}
        
        .subtitle {{
            color: #718096;
            font-size: 1.1em;
            margin-bottom: 20px;
        }}
        
        .card {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
        }}
        
        .card h2 {{
            color: #2d3748;
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .metric-box {{
            background: #f7fafc;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #4299e1;
        }}
        
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2d3748;
            margin: 10px 0;
        }}
        
        .metric-label {{
            color: #718096;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .risk-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .risk-critical {{ background: #fed7d7; color: #9b2c2c; }}
        .risk-high {{ background: #feebc8; color: #9c4221; }}
        .risk-medium {{ background: #fefcbf; color: #744210; }}
        .risk-low {{ background: #c6f6d5; color: #276749; }}
        .risk-none {{ background: #e2e8f0; color: #4a5568; }}
        
        .findings-list {{
            list-style: none;
        }}
        
        .finding-item {{
            padding: 15px;
            margin-bottom: 10px;
            background: #f7fafc;
            border-radius: 8px;
            border-left: 4px solid #e53e3e;
        }}
        
        .finding-item.low {{ border-left-color: #38a169; }}
        .finding-item.medium {{ border-left-color: #d69e2e; }}
        .finding-item.high {{ border-left-color: #dd6b20; }}
        .finding-item.critical {{ border-left-color: #c53030; }}
        
        .finding-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .finding-type {{
            font-weight: bold;
            color: #2d3748;
        }}
        
        .finding-file {{
            font-family: 'Courier New', monospace;
            color: #718096;
            font-size: 0.9em;
        }}
        
        .architecture-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .layer-card {{
            background: #f7fafc;
            padding: 20px;
            border-radius: 8px;
        }}
        
        .layer-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .layer-name {{
            font-weight: bold;
            color: #2d3748;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .layer-count {{
            background: #4299e1;
            color: white;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.9em;
        }}
        
        .file-list {{
            list-style: none;
            max-height: 200px;
            overflow-y: auto;
        }}
        
        .file-item {{
            padding: 8px 0;
            border-bottom: 1px solid #e2e8f0;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #4a5568;
        }}
        
        .file-item:last-child {{
            border-bottom: none;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: white;
            font-size: 0.9em;
        }}
        
        .footer a {{
            color: white;
            text-decoration: underline;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CodeAtlas Analysis Report</h1>
            <div class="subtitle">
                <strong>Repository:</strong> {report_path}<br>
                <strong>Generated:</strong> {generated_date}<br>
                <strong>Analysis ID:</strong> {analysis_id}
            </div>
        </div>
        
        <!-- Summary Card -->
        <div class="card">
            <h2>📊 Summary</h2>
            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="metric-label">Files</div>
                    <div class="metric-value">{summary_total_files}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Risk Level</div>
                    <div class="metric-value">
                        <span class="risk-badge risk-{metrics_risk}">{metrics_risk.upper()}</span>
                    </div>
                    <div class="metric-label">Score: {metrics_risk_score}/100</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Total Size</div>
                    <div class="metric-value">{metrics_total_size_kb} KB</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Languages</div>
                    <div class="metric-value">{len(metrics_languages.split(', ')) if metrics_languages else 0}</div>
                    <div class="metric-label">{metrics_languages}</div>
                </div>
            </div>
        </div>
        
        <!-- Security Card -->
        {security_html}
        
        <!-- Architecture Card -->
        {architecture_html}
        
        <!-- Python Analysis Card -->
        {python_html}
        
        <!-- Raw Data Card (Collapsible) -->
        <div class="card">
            <h2>📄 Raw Data</h2>
            <details>
                <summary>Click to view complete JSON data</summary>
                <pre style="margin-top: 20px; padding: 15px; background: #f7fafc; border-radius: 5px; overflow-x: auto; max-height: 400px; overflow-y: auto;">{json_data}</pre>
            </details>
        </div>
    </div>
    
    <div class="footer">
        <p>Generated by <strong>CodeAtlas</strong> • AI-Powered Code Intelligence Platform</p>
        <p>For more information, visit the <a href="http://localhost:8000/docs">CodeAtlas API Documentation</a></p>
    </div>
    
    <script>
        // Add interactivity
        document.addEventListener('DOMContentLoaded', function() {{
            // Make all external links open in new tab
            document.querySelectorAll('a[href^="http"]').forEach(link => {{
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
            }});
            
            // Add copy functionality to code blocks
            document.querySelectorAll('pre').forEach(pre => {{
                const button = document.createElement('button');
                button.textContent = 'Copy';
                button.style.cssText = `
                    position: absolute;
                    top: 5px;
                    right: 5px;
                    padding: 5px 10px;
                    background: #4299e1;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 12px;
                `;
                pre.style.position = 'relative';
                pre.appendChild(button);
                
                button.addEventListener('click', () => {{
                    navigator.clipboard.writeText(pre.textContent.replace('Copy', '').trim())
                        .then(() => {{
                            button.textContent = 'Copied!';
                            setTimeout(() => button.textContent = 'Copy', 2000);
                        }});
                }});
            }});
        }});
    </script>
</body>
</html>
"""


def _generate_security_html(security: Dict[str, Any]) -> str:
    """Generate HTML for security section."""
    if not security or 'error' in security:
        return '<div class="card"><h2>🔒 Security</h2><p>No security issues found.</p></div>'
    
    secrets_found = security.get('secrets_found', 0)
    vulns_found = security.get('vulnerabilities_found', 0)
    
    html = f"""
    <div class="card">
        <h2>🔒 Security</h2>
        <div class="metrics-grid">
            <div class="metric-box">
                <div class="metric-label">Secrets Found</div>
                <div class="metric-value">{secrets_found}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Vulnerabilities</div>
                <div class="metric-value">{vulns_found}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Overall Risk</div>
                <div class="metric-value">
                    <span class="risk-badge risk-{security.get('risk_level', 'none')}">
                        {security.get('risk_level', 'none').upper()}
                    </span>
                </div>
            </div>
        </div>
    """
    
    # Add findings if any
    if secrets_found > 0:
        html += '<h3 style="margin-top: 20px;">Potential Secrets</h3><ul class="findings-list">'
        for secret in security.get('secrets', [])[:3]:
            if isinstance(secret, dict):
                risk_class = secret.get('risk_level', 'medium')
                html += f"""
                <li class="finding-item {risk_class}">
                    <div class="finding-header">
                        <span class="finding-type">{secret.get('type', 'Secret')}</span>
                        <span class="risk-badge risk-{risk_class}">{risk_class.upper()}</span>
                    </div>
                    <div class="finding-file">{secret.get('file', 'Unknown')}:{secret.get('line', 'N/A')}</div>
                    <p style="margin-top: 10px; color: #4a5568;">{secret.get('context', '')[:100]}...</p>
                </li>
                """
        if secrets_found > 3:
            html += f'<li style="color: #718096; padding: 10px;">... and {secrets_found - 3} more secrets</li>'
        html += '</ul>'
    
    return html + '</div>'


def _generate_architecture_html(architecture: Dict[str, Any]) -> str:
    """Generate HTML for architecture section."""
    if not architecture or 'error' in architecture:
        return '<div class="card"><h2>🏗️ Architecture</h2><p>No architecture analysis available.</p></div>'
    
    layers = architecture.get('layers', {})
    if not layers:
        return '<div class="card"><h2>🏗️ Architecture</h2><p>No clear architecture detected.</p></div>'
    
    html = """
    <div class="card">
        <h2>🏗️ Architecture</h2>
        <div class="architecture-grid">
    """
    
    for layer, files in layers.items():
        if files:  # Only show non-empty layers
            html += f"""
            <div class="layer-card">
                <div class="layer-header">
                    <span class="layer-name">{layer}</span>
                    <span class="layer-count">{len(files)} files</span>
                </div>
                <ul class="file-list">
            """
            for file in files[:5]:
                html += f'<li class="file-item">{file}</li>'
            if len(files) > 5:
                html += f'<li class="file-item" style="color: #718096; font-style: italic;">... {len(files) - 5} more</li>'
            html += '</ul></div>'
    
    return html + '</div></div>'


def _generate_python_html(python_analysis: Dict[str, Any]) -> str:
    """Generate HTML for Python analysis section."""
    if not python_analysis or 'error' in python_analysis:
        return ''
    
    html = f"""
    <div class="card">
        <h2>🐍 Python Analysis</h2>
        <div class="metrics-grid">
            <div class="metric-box">
                <div class="metric-label">Python Files</div>
                <div class="metric-value">{python_analysis.get('python_files_count', 0)}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Functions</div>
                <div class="metric-value">{python_analysis.get('total_functions', 0)}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Classes</div>
                <div class="metric-value">{python_analysis.get('total_classes', 0)}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Avg Complexity</div>
                <div class="metric-value">{python_analysis.get('avg_complexity_score', 0)}</div>
            </div>
        </div>
    """
    
    # Show most complex files
    complex_files = python_analysis.get('most_complex_files', [])
    if complex_files:
        html += '<h3 style="margin-top: 20px;">Most Complex Files</h3><ul class="findings-list">'
        for file_data in complex_files[:3]:
            html += f"""
            <li class="finding-item">
                <div class="finding-header">
                    <span class="finding-type">{file_data.get('file', 'Unknown').split('/')[-1]}</span>
                    <span>Complexity: {file_data.get('complexity_score', 0)}</span>
                </div>
                <div style="color: #718096; margin-top: 5px;">
                    Functions: {file_data.get('functions', 0)} • 
                    Classes: {file_data.get('classes', 0)} • 
                    Imports: {file_data.get('imports', 0)}
                </div>
            </li>
            """
        html += '</ul>'
    
    return html + '</div>'