"""
AI-powered analysis enhancements
"""
import json
from typing import Dict, Any
from app.services.ai.llm_client import llm_client
from app.core.config import settings

async def enhance_with_ai(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """Add AI-powered insights to the analysis"""
    
    if not settings.ENABLE_AI_INSIGHTS:
        return analysis_result
    
    try:
        # Generate AI summary of findings
        security_findings = analysis_result.get("security", {}).get("vulnerabilities", [])
        complex_files = analysis_result.get("python_analysis", {}).get("most_complex_files", [])
        
        prompt = f"""
        Analyze this code analysis report and provide insights:
        
        Repository: {analysis_result.get('repo_name')}
        Total Files: {analysis_result.get('summary', {}).get('total_files')}
        Risk Level: {analysis_result.get('overall_risk_level')}
        
        Security Findings ({len(security_findings)}):
        {json.dumps(security_findings[:3], indent=2)}
        
        Most Complex Files:
        {json.dumps(complex_files[:3], indent=2)}
        
        Provide:
        1. Key security concerns to address first
        2. Architecture improvement suggestions
        3. Code quality recommendations
        """
        
        ai_response = await llm_client.call_async(prompt)
        
        if ai_response["success"]:
            analysis_result["ai_insights"] = {
                "summary": ai_response["content"],
                "model": llm_client.model
            }
    
    except Exception as e:
        print(f"AI enhancement failed: {e}")
        analysis_result["ai_insights"] = {"error": str(e)}
    
    return analysis_result