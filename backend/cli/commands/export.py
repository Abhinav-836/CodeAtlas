"""
CLI export command.
"""
import json
import sys
from pathlib import Path
from typing import Optional
import requests

BASE_URL = "http://127.0.0.1:8000"


def export_command(format_type: str = "json", report_id: Optional[str] = None) -> None:
    """
    Export analysis report.
    
    Args:
        format_type: Export format (json, html, markdown)
        report_id: Report ID to export (if not provided, uses latest)
    """
    try:
        if not report_id:
            # Try to get the latest report
            try:
                response = requests.get(f"{BASE_URL}/analyze/queue/stats", timeout=5)
                if response.status_code == 200:
                    stats = response.json()
                    # Find a completed task
                    tasks_response = requests.get(f"{BASE_URL}/analyze/queue/stats", timeout=5)
                    if tasks_response.status_code == 200:
                        tasks = tasks_response.json()
                        # Simplified: use first task if available
                        if tasks.get("total_tasks", 0) > 0:
                            # This is a simplification - in real app, you'd have better logic
                            print("⚠️  Please specify a report_id. Use: codeatlas export <report_id> --format <format>")
                            return
            except requests.exceptions.RequestException:
                pass
            
            print("❌ No report_id provided and couldn't find recent reports.")
            print("   Usage: codeatlas export <report_id> --format <format>")
            return
        
        # Get the analysis results
        print(f"📥 Fetching report: {report_id}")
        response = requests.get(
            f"{BASE_URL}/analyze/results/{report_id}",
            timeout=30
        )
        
        if response.status_code == 404:
            print(f"❌ Report not found: {report_id}")
            return
        elif response.status_code != 200:
            print(f"❌ Failed to fetch report: {response.status_code} - {response.text}")
            return
        
        analysis_data = response.json()
        
        # Generate filename
        timestamp = analysis_data.get("timestamp", "").split("T")[0].replace("-", "")
        repo_name = Path(analysis_data.get("path", "unknown")).name
        filename = f"codeatlas_{repo_name}_{timestamp}.{format_type}"
        
        # Export based on format
        if format_type == "json":
            content = json.dumps(analysis_data, indent=2, default=str)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ JSON report saved: {filename}")
            
        elif format_type == "html":
            # Generate HTML report
            html_content = _generate_html(analysis_data)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✅ HTML report saved: {filename}")
            
        elif format_type == "markdown":
            # Generate Markdown report
            md_content = _generate_markdown(analysis_data)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(md_content)
            print(f"✅ Markdown report saved: {filename}")
            
        else:
            print(f"❌ Unsupported format: {format_type}")
            print("   Supported formats: json, html, markdown")
            
    except requests.exceptions.Timeout:
        print("❌ Request timeout. Server might be busy.")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to CodeAtlas server.")
        print("   Make sure the server is running: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Export failed: {str(e)}")


def _generate_html(analysis_data: dict) -> str:
    """Generate HTML report."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeAtlas Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        .metric { display: inline-block; margin: 10px 20px 10px 0; padding: 10px; background: #f8f9fa; border-radius: 3px; }
        .success { color: #27ae60; }
        .warning { color: #f39c12; }
        .danger { color: #e74c3c; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; }
        pre { background: #f8f9fa; padding: 15px; border-radius: 3px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗺️ CodeAtlas Analysis Report</h1>
            <p>Generated on {timestamp}</p>
        </div>
    """.format(timestamp=analysis_data.get("timestamp", "Unknown"))
    
    # Summary section
    if "summary" in analysis_data:
        html += f"""
        <div class="section">
            <h2>📊 Summary</h2>
            <p><strong>Repository:</strong> {analysis_data.get('path', 'Unknown')}</p>
            <p><strong>Analysis ID:</strong> {analysis_data.get('analysis_id', 'Unknown')}</p>
            <p><strong>Total Files:</strong> {analysis_data['summary'].get('total_files', 0)}</p>
        </div>
        """
    
    # Metrics section
    if "metrics" in analysis_data:
        metrics = analysis_data["metrics"]
        html += """
        <div class="section">
            <h2>📈 Metrics</h2>
            <div>
        """
        for key, value in metrics.items():
            if key != "error":
                html += f'<div class="metric"><strong>{key}:</strong> {value}</div>'
        html += """
            </div>
        </div>
        """
    
    # Security section
    if "security" in analysis_data:
        security = analysis_data["security"]
        html += f"""
        <div class="section">
            <h2>🔒 Security</h2>
            <p><strong>Secrets Found:</strong> {security.get('secrets_found', 0)}</p>
            <p><strong>Vulnerabilities Found:</strong> {security.get('vulnerabilities_found', 0)}</p>
        """
        if security.get("secrets"):
            html += "<h3>Potential Secrets:</h3><ul>"
            for secret in security.get("secrets", [])[:5]:
                html += f"<li>{secret}</li>"
            html += "</ul>"
        html += "</div>"
    
    html += """
    </div>
</body>
</html>
    """
    return html


def _generate_markdown(analysis_data: dict) -> str:
    """Generate Markdown report."""
    md = f"""# CodeAtlas Analysis Report

## 📋 Overview
- **Repository**: `{analysis_data.get('path', 'Unknown')}`
- **Analysis ID**: `{analysis_data.get('analysis_id', 'Unknown')}`
- **Timestamp**: {analysis_data.get('timestamp', 'Unknown')}
- **Status**: {analysis_data.get('status', 'Unknown')}

"""
    
    # Summary
    if "summary" in analysis_data:
        summary = analysis_data["summary"]
        md += f"""## 📊 Summary
- **Total Files**: {summary.get('total_files', 0)}
"""
        if "file_types" in summary:
            md += "- **File Types**:\n"
            for file_type, count in summary["file_types"].items():
                md += f"  - {file_type}: {count}\n"
    
    # Metrics
    if "metrics" in analysis_data and "error" not in analysis_data["metrics"]:
        metrics = analysis_data["metrics"]
        md += "\n## 📈 Metrics\n"
        for key, value in metrics.items():
            md += f"- **{key.replace('_', ' ').title()}**: {value}\n"
    
    # Security
    if "security" in analysis_data:
        security = analysis_data["security"]
        md += f"""
## 🔒 Security
- **Secrets Found**: {security.get('secrets_found', 0)}
- **Vulnerabilities Found**: {security.get('vulnerabilities_found', 0)}
"""
        if security.get("secrets"):
            md += "\n### Potential Secrets\n"
            for secret in security.get("secrets", [])[:5]:
                md += f"- {secret}\n"
    
    # Architecture
    if "architecture" in analysis_data:
        arch = analysis_data["architecture"]
        md += f"""
## 🏗️ Architecture
- **Layers Identified**: {arch.get('layer_count', 0)}
"""
        if "files_per_layer" in arch:
            md += "\n### Files by Layer\n"
            for layer, count in arch["files_per_layer"].items():
                md += f"- **{layer}**: {count} files\n"
    
    md += "\n---\n*Report generated by CodeAtlas*"
    return md


def main():
    """CLI entry point for export."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export analysis reports")
    parser.add_argument("report_id", nargs="?", help="Report ID to export")
    parser.add_argument("--format", choices=["json", "html", "markdown"], 
                       default="json", help="Export format")
    
    args = parser.parse_args()
    
    export_command(args.format, args.report_id)


if __name__ == "__main__":
    main()