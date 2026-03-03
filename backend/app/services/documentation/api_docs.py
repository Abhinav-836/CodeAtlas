"""
OpenAPI/Swagger documentation generator with custom enhancements.
"""
import json
from typing import Dict, List, Any, Optional
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
import yaml
import logging

logger = logging.getLogger(__name__)


class APIDocumentation:
    """Advanced API documentation generator."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.custom_docs = {}
    
    def generate_openapi_schema(self) -> Dict[str, Any]:
        """Generate enhanced OpenAPI schema."""
        # Get base schema
        schema = get_openapi(
            title=self.app.title,
            version=self.app.version,
            description=self.app.description,
            routes=self.app.routes,
        )
        
        # Add security schemes
        schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "Enter your API key for authentication",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter JWT token for authentication",
            },
        }
        
        # Add global security requirement
        schema["security"] = [{"ApiKeyAuth": []}]
        
        # Add tags with descriptions
        schema["tags"] = self._get_tags_metadata()
        
        # Add servers
        schema["servers"] = [
            {
                "url": "http://localhost:8000",
                "description": "Development server",
            },
            {
                "url": "https://api.codeatlas.ai",
                "description": "Production server",
            },
        ]
        
        # Add external docs
        schema["externalDocs"] = {
            "description": "GitHub Repository",
            "url": "https://github.com/yourusername/codeatlas",
        }
        
        # Add examples to schemas
        schema = self._add_examples_to_schemas(schema)
        
        # Add operation metadata
        schema = self._enhance_operations(schema)
        
        return schema
    
    def _get_tags_metadata(self) -> List[Dict[str, str]]:
        """Get metadata for API tags."""
        return [
            {
                "name": "health",
                "description": "Health checks and system monitoring endpoints",
                "externalDocs": {
                    "description": "Learn more",
                    "url": "https://microservices.io/patterns/observability/health-check-api.html",
                },
            },
            {
                "name": "auth",
                "description": "Authentication, authorization, and API key management",
            },
            {
                "name": "upload",
                "description": "Upload files, repositories, and external sources",
            },
            {
                "name": "analyze",
                "description": "Code analysis, scanning, and processing endpoints",
            },
            {
                "name": "reports",
                "description": "Report generation, export, and management",
            },
            {
                "name": "webhooks",
                "description": "Webhook configuration and event subscriptions",
            },
            {
                "name": "admin",
                "description": "Administrative endpoints (development only)",
            },
        ]
    
    def _add_examples_to_schemas(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add examples to request/response schemas."""
        # Example for analysis request
        if "AnalysisRequest" not in schema.get("components", {}).get("schemas", {}):
            schema["components"]["schemas"]["AnalysisRequest"] = {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "example": "/path/to/repository",
                        "description": "Path to the repository to analyze",
                    },
                    "options": {
                        "type": "object",
                        "example": {
                            "include_security": True,
                            "include_complexity": True,
                            "generate_docs": True,
                            "depth": "standard",
                        },
                        "description": "Analysis options",
                    },
                },
                "required": ["path"],
            }
        
        # Example for analysis response
        if "AnalysisResponse" not in schema.get("components", {}).get("schemas", {}):
            schema["components"]["schemas"]["AnalysisResponse"] = {
                "type": "object",
                "properties": {
                    "success": {
                        "type": "boolean",
                        "example": True,
                        "description": "Whether analysis started successfully",
                    },
                    "analysis_id": {
                        "type": "string",
                        "example": "550e8400-e29b-41d4-a716-446655440000",
                        "description": "Unique analysis identifier",
                    },
                    "task_id": {
                        "type": "string",
                        "example": "task_1234567890",
                        "description": "Background task identifier",
                    },
                    "status": {
                        "type": "string",
                        "example": "queued",
                        "description": "Current analysis status",
                        "enum": ["queued", "running", "completed", "failed"],
                    },
                    "message": {
                        "type": "string",
                        "example": "Analysis started for repository",
                        "description": "Human-readable message",
                    },
                    "check_status_url": {
                        "type": "string",
                        "example": "/api/analyze/status/task_1234567890",
                        "description": "URL to check analysis status",
                    },
                    "get_results_url": {
                        "type": "string",
                        "example": "/api/analyze/results/task_1234567890",
                        "description": "URL to get analysis results",
                    },
                    "estimated_time": {
                        "type": "integer",
                        "example": 120,
                        "description": "Estimated analysis time in seconds",
                    },
                },
            }
        
        # Example for error response
        if "ErrorResponse" not in schema.get("components", {}).get("schemas", {}):
            schema["components"]["schemas"]["ErrorResponse"] = {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "example": "API key required. Use header: X-API-Key",
                        "description": "Error description",
                    },
                    "error_code": {
                        "type": "string",
                        "example": "AUTH_REQUIRED",
                        "description": "Machine-readable error code",
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "example": "2024-01-15T10:30:00Z",
                        "description": "When the error occurred",
                    },
                    "path": {
                        "type": "string",
                        "example": "/api/analyze",
                        "description": "Request path",
                    },
                },
            }
        
        return schema
    
    def _enhance_operations(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata to operations."""
        for path, methods in schema.get("paths", {}).items():
            for method, operation in methods.items():
                # Add operation ID if missing
                if "operationId" not in operation:
                    operation["operationId"] = self._generate_operation_id(path, method)
                
                # Add summary if missing
                if "summary" not in operation:
                    operation["summary"] = self._generate_summary(path, method)
                
                # Add descriptions
                operation["description"] = self._generate_description(path, method, operation)
                
                # Add parameters
                operation = self._add_parameters(operation, path, method)
                
                # Add responses
                operation = self._add_responses(operation, path, method)
                
                # Add security requirements
                if "/api/" in path and path != "/api/health":
                    operation["security"] = [{"ApiKeyAuth": []}]
        
        return schema
    
    def _generate_operation_id(self, path: str, method: str) -> str:
        """Generate operation ID from path and method."""
        # Clean path
        clean_path = path.replace("/api/", "").replace("/", "_").replace("-", "_").strip("_")
        
        # Convert method to present tense verb
        method_verbs = {
            "get": "get",
            "post": "create",
            "put": "update",
            "patch": "partial_update",
            "delete": "delete",
        }
        
        verb = method_verbs.get(method.lower(), "execute")
        return f"{verb}_{clean_path}"
    
    def _generate_summary(self, path: str, method: str) -> str:
        """Generate summary for operation."""
        summaries = {
            ("/api/analyze", "post"): "Start code analysis",
            ("/api/analyze/status/{task_id}", "get"): "Check analysis status",
            ("/api/analyze/results/{task_id}", "get"): "Get analysis results",
            ("/api/upload/zip", "post"): "Upload and extract ZIP file",
            ("/api/reports", "get"): "List analysis reports",
            ("/api/reports/{report_id}", "get"): "Get report in specified format",
            ("/api/health", "get"): "Health check",
        }
        
        return summaries.get((path, method.lower()), f"{method.upper()} {path}")
    
    def _generate_description(self, path: str, method: str, operation: Dict[str, Any]) -> str:
        """Generate detailed description for operation."""
        descriptions = {
            "/api/analyze": "Start analysis of a code repository. The analysis runs in the background and includes security scanning, complexity analysis, architecture inference, and AI-powered insights.",
            "/api/upload/zip": "Upload a ZIP file containing source code. The file will be extracted securely and made available for analysis. Maximum file size is 100MB.",
            "/api/reports": "Browse and search analysis reports with pagination and filtering capabilities.",
            "/api/health": "Check the health status of the API and its dependencies. Useful for monitoring and readiness probes.",
        }
        
        base_desc = descriptions.get(path, operation.get("summary", ""))
        
        # Add method-specific details
        if method.lower() == "post":
            base_desc += "\n\n**Note:** This is an asynchronous operation. Use the returned task ID to check status and retrieve results."
        elif method.lower() == "get" and "{task_id}" in path:
            base_desc += "\n\n**Note:** Results are cached for 24 hours after analysis completion."
        
        return base_desc
    
    def _add_parameters(self, operation: Dict[str, Any], path: str, method: str) -> Dict[str, Any]:
        """Add common parameters to operation."""
        if "parameters" not in operation:
            operation["parameters"] = []
        
        # Add common query parameters for GET endpoints
        if method.lower() == "get":
            if "/api/reports" in path and not path.endswith("}"):
                operation["parameters"].extend([
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "minimum": 1, "maximum": 1000},
                        "description": "Maximum number of items to return",
                        "example": 50,
                        "required": False,
                    },
                    {
                        "name": "offset",
                        "in": "query",
                        "schema": {"type": "integer", "minimum": 0},
                        "description": "Pagination offset",
                        "example": 0,
                        "required": False,
                    },
                    {
                        "name": "sort",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["created", "modified", "size", "name"]},
                        "description": "Field to sort by",
                        "example": "created",
                        "required": False,
                    },
                    {
                        "name": "order",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["asc", "desc"]},
                        "description": "Sort order",
                        "example": "desc",
                        "required": False,
                    },
                ])
        
        # Add format parameter for report endpoints
        if "/api/reports/{report_id}" in path and method.lower() == "get":
            operation["parameters"].append({
                "name": "format",
                "in": "query",
                "schema": {"type": "string", "enum": ["json", "html", "markdown", "pdf"]},
                "description": "Output format",
                "example": "json",
                "required": False,
            })
        
        return operation
    
    def _add_responses(self, operation: Dict[str, Any], path: str, method: str) -> Dict[str, Any]:
        """Add standardized responses to operation."""
        if "responses" not in operation:
            operation["responses"] = {}
        
        # Add common responses
        common_responses = {
            "400": {
                "description": "Bad Request - Invalid input",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "detail": "Invalid input parameters",
                            "error_code": "INVALID_INPUT",
                            "timestamp": "2024-01-15T10:30:00Z",
                        },
                    }
                },
            },
            "401": {
                "description": "Unauthorized - Missing or invalid API key",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "detail": "API key required. Use header: X-API-Key",
                            "error_code": "AUTH_REQUIRED",
                            "timestamp": "2024-01-15T10:30:00Z",
                        },
                    }
                },
            },
            "404": {
                "description": "Not Found - Resource not found",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "detail": "Report not found",
                            "error_code": "NOT_FOUND",
                            "timestamp": "2024-01-15T10:30:00Z",
                        },
                    }
                },
            },
            "429": {
                "description": "Too Many Requests - Rate limit exceeded",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "detail": "Rate limit exceeded. Try again in 60 seconds.",
                            "error_code": "RATE_LIMITED",
                            "timestamp": "2024-01-15T10:30:00Z",
                        },
                    }
                },
            },
            "500": {
                "description": "Internal Server Error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "detail": "Internal server error",
                            "error_code": "INTERNAL_ERROR",
                            "timestamp": "2024-01-15T10:30:00Z",
                        },
                    }
                },
            },
        }
        
        # Add success response based on method
        success_response = {
            "200": {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/AnalysisResponse"},
                    }
                },
            }
        }
        
        if method.lower() == "post":
            success_response = {
                "202": {
                    "description": "Accepted - Request accepted for processing",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/AnalysisResponse"},
                        }
                    },
                }
            }
        
        # Merge responses
        operation["responses"].update(success_response)
        operation["responses"].update(common_responses)
        
        return operation
    
    def export_openapi_json(self, file_path: str = "openapi.json"):
        """Export OpenAPI schema as JSON."""
        schema = self.generate_openapi_schema()
        
        with open(file_path, "w") as f:
            json.dump(schema, f, indent=2)
        
        logger.info(f"OpenAPI schema exported to {file_path}")
        return file_path
    
    def export_openapi_yaml(self, file_path: str = "openapi.yaml"):
        """Export OpenAPI schema as YAML."""
        schema = self.generate_openapi_schema()
        
        with open(file_path, "w") as f:
            yaml.dump(schema, f, sort_keys=False)
        
        logger.info(f"OpenAPI schema exported to {file_path}")
        return file_path
    
    def generate_postman_collection(self, file_path: str = "postman_collection.json"):
        """Generate Postman collection from OpenAPI schema."""
        schema = self.generate_openapi_schema()
        
        postman_collection = {
            "info": {
                "name": schema.get("info", {}).get("title", "API"),
                "description": schema.get("info", {}).get("description", ""),
                "version": schema.get("info", {}).get("version", "1.0.0"),
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": [],
            "variable": [
                {
                    "key": "baseUrl",
                    "value": "{{baseUrl}}",
                    "type": "string",
                },
                {
                    "key": "apiKey",
                    "value": "your-api-key-here",
                    "type": "string",
                },
            ],
            "auth": {
                "type": "apikey",
                "apikey": [
                    {
                        "key": "value",
                        "value": "{{apiKey}}",
                        "type": "string",
                    },
                    {
                        "key": "key",
                        "value": "X-API-Key",
                        "type": "string",
                    },
                    {
                        "key": "in",
                        "value": "header",
                        "type": "string",
                    },
                ],
            },
        }
        
        # Convert paths to Postman items
        for path, methods in schema.get("paths", {}).items():
            for method, operation in methods.items():
                item = {
                    "name": operation.get("summary", f"{method.upper()} {path}"),
                    "request": {
                        "method": method.upper(),
                        "url": {
                            "raw": "{{baseUrl}}" + path,
                            "host": ["{{baseUrl}}"],
                            "path": path.strip("/").split("/"),
                        },
                        "description": operation.get("description", ""),
                        "header": [
                            {
                                "key": "X-API-Key",
                                "value": "{{apiKey}}",
                                "type": "string",
                            },
                        ],
                    },
                    "response": [],
                }
                
                # Add query parameters
                if "parameters" in operation:
                    query_params = []
                    for param in operation["parameters"]:
                        if param.get("in") == "query":
                            query_params.append({
                                "key": param["name"],
                                "value": param.get("example", ""),
                                "description": param.get("description", ""),
                            })
                    
                    if query_params:
                        item["request"]["url"]["query"] = query_params
                
                postman_collection["item"].append(item)
        
        with open(file_path, "w") as f:
            json.dump(postman_collection, f, indent=2)
        
        logger.info(f"Postman collection exported to {file_path}")
        return file_path


# Convenience functions
def generate_api_docs(routes: List[str]) -> Dict[str, Any]:
    """Generate API documentation from routes."""
    return {
        "endpoints": routes,
        "auth": {
            "type": "API Key",
            "header": "X-API-Key",
            "description": "Required for all endpoints except /health",
        },
        "rate_limits": {
            "default": "100 requests per hour",
            "authenticated": "1000 requests per hour",
        },
        "formats": {
            "request": "JSON",
            "response": "JSON",
        },
        "error_codes": {
            "400": "Bad Request",
            "401": "Unauthorized",
            "404": "Not Found",
            "429": "Rate Limited",
            "500": "Internal Server Error",
        },
    }


def validate_openapi_schema(schema: Dict[str, Any]) -> List[str]:
    """Validate OpenAPI schema and return errors."""
    errors = []
    
    # Check required fields
    required_fields = ["openapi", "info", "paths"]
    for field in required_fields:
        if field not in schema:
            errors.append(f"Missing required field: {field}")
    
    # Check info object
    if "info" in schema:
        info = schema["info"]
        info_required = ["title", "version"]
        for field in info_required:
            if field not in info:
                errors.append(f"Missing info.{field}")
    
    # Check paths
    if "paths" in schema:
        for path, methods in schema["paths"].items():
            if not path.startswith("/"):
                errors.append(f"Path must start with '/': {path}")
            
            for method in methods.keys():
                if method not in ["get", "post", "put", "patch", "delete", "head", "options", "trace"]:
                    errors.append(f"Invalid HTTP method: {method} at {path}")
    
    return errors