"""
Deployment guides for CodeAtlas in various environments.
"""
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DeploymentEnvironment(Enum):
    """Deployment environments."""
    LOCAL = "local"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    HEROKU = "heroku"


class DatabaseType(Enum):
    """Database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"


@dataclass
class DeploymentStep:
    """A deployment step."""
    number: int
    title: str
    command: str
    description: str
    check_command: str = ""
    expected_output: str = ""
    is_optional: bool = False


@dataclass
class DeploymentConfig:
    """Deployment configuration."""
    environment: DeploymentEnvironment
    database: DatabaseType
    use_redis: bool = True
    use_celery: bool = True
    use_nginx: bool = True
    use_docker: bool = False
    monitoring: bool = True


class DeploymentGuide:
    """Generate deployment guides for different environments."""
    
    def __init__(self):
        self.configs = {}
    
    def generate_guide(self, config: DeploymentConfig) -> Dict[str, Any]:
        """Generate deployment guide for given configuration."""
        guide = {
            "environment": config.environment.value,
            "database": config.database.value,
            "prerequisites": self._get_prerequisites(config),
            "steps": self._get_deployment_steps(config),
            "configuration": self._get_configuration(config),
            "verification": self._get_verification_steps(config),
            "troubleshooting": self._get_troubleshooting(config),
            "scaling": self._get_scaling_guide(config),
            "cost_estimation": self._get_cost_estimation(config),
        }
        
        return guide
    
    def _get_prerequisites(self, config: DeploymentConfig) -> List[str]:
        """Get prerequisites for deployment."""
        prerequisites = []
        
        # Common prerequisites
        prerequisites.extend([
            "Python 3.9+",
            "Git",
            "pip (Python package manager)",
        ])
        
        # Environment-specific
        if config.environment == DeploymentEnvironment.DOCKER:
            prerequisites.extend([
                "Docker 20.10+",
                "Docker Compose 2.0+",
            ])
        elif config.environment == DeploymentEnvironment.KUBERNETES:
            prerequisites.extend([
                "kubectl",
                "Helm 3.0+ (optional)",
                "Kubernetes cluster",
            ])
        elif config.environment == DeploymentEnvironment.AWS:
            prerequisites.extend([
                "AWS CLI",
                "AWS account with appropriate permissions",
            ])
        
        # Database-specific
        if config.database == DatabaseType.POSTGRESQL:
            prerequisites.append("PostgreSQL 13+ (if not using Docker)")
        elif config.database == DatabaseType.MYSQL:
            prerequisites.append("MySQL 8.0+ (if not using Docker)")
        
        # Optional components
        if config.use_redis:
            prerequisites.append("Redis 6.0+ (if not using Docker)")
        
        return prerequisites
    
    def _get_deployment_steps(self, config: DeploymentConfig) -> List[DeploymentStep]:
        """Get deployment steps."""
        steps = []
        
        if config.environment == DeploymentEnvironment.LOCAL:
            steps = self._get_local_steps(config)
        elif config.environment == DeploymentEnvironment.DOCKER:
            steps = self._get_docker_steps(config)
        elif config.environment == DeploymentEnvironment.KUBERNETES:
            steps = self._get_kubernetes_steps(config)
        elif config.environment == DeploymentEnvironment.AWS:
            steps = self._get_aws_steps(config)
        
        return steps
    
    def _get_local_steps(self, config: DeploymentConfig) -> List[DeploymentStep]:
        """Get local deployment steps."""
        return [
            DeploymentStep(
                number=1,
                title="Clone repository",
                command="git clone https://github.com/yourusername/codeatlas.git",
                description="Clone the CodeAtlas repository",
                check_command="ls codeatlas",
                expected_output="README.md",
            ),
            DeploymentStep(
                number=2,
                title="Navigate to project",
                command="cd codeatlas",
                description="Change to project directory",
            ),
            DeploymentStep(
                number=3,
                title="Create virtual environment",
                command="python -m venv venv",
                description="Create Python virtual environment",
                check_command="ls venv/bin/activate",
            ),
            DeploymentStep(
                number=4,
                title="Activate virtual environment",
                command="source venv/bin/activate  # On Windows: venv\\Scripts\\activate",
                description="Activate the virtual environment",
            ),
            DeploymentStep(
                number=5,
                title="Install dependencies",
                command="pip install -r requirements.txt",
                description="Install Python dependencies",
                check_command="pip list | grep fastapi",
                expected_output="fastapi",
            ),
            DeploymentStep(
                number=6,
                title="Create environment file",
                command='''cat > .env << EOF
API_KEY=your-secure-api-key-here
OPENAI_API_KEY=sk-your-openai-key
DATABASE_URL=sqlite:///./codeatlas.db
DEBUG=True
MAX_WORKERS=4
EOF''',
                description="Create environment configuration file",
                check_command="ls .env",
            ),
            DeploymentStep(
                number=7,
                title="Initialize database",
                command="alembic upgrade head",
                description="Run database migrations",
            ),
            DeploymentStep(
                number=8,
                title="Start the server",
                command="uvicorn app.main:app --reload --host 0.0.0.0 --port 8000",
                description="Start the FastAPI development server",
                check_command="curl http://localhost:8000/health",
                expected_output='"status": "healthy"',
            ),
        ]
    
    def _get_docker_steps(self, config: DeploymentConfig) -> List[DeploymentStep]:
        """Get Docker deployment steps."""
        steps = [
            DeploymentStep(
                number=1,
                title="Clone repository",
                command="git clone https://github.com/yourusername/codeatlas.git",
                description="Clone the CodeAtlas repository",
            ),
            DeploymentStep(
                number=2,
                title="Navigate to project",
                command="cd codeatlas",
                description="Change to project directory",
            ),
            DeploymentStep(
                number=3,
                title="Create environment file",
                command='''cat > .env << EOF
API_KEY=your-secure-api-key-here
OPENAI_API_KEY=sk-your-openai-key
DATABASE_URL=postgresql+asyncpg://codeatlas:password@db:5432/codeatlas
REDIS_URL=redis://redis:6379/0
DEBUG=False
MAX_WORKERS=4
EOF''',
                description="Create environment configuration file",
            ),
        ]
        
        if config.database == DatabaseType.POSTGRESQL:
            steps.extend([
                DeploymentStep(
                    number=4,
                    title="Start with Docker Compose",
                    command="docker-compose up -d",
                    description="Start all services with Docker Compose",
                    check_command="docker-compose ps",
                    expected_output="Up (healthy)",
                ),
                DeploymentStep(
                    number=5,
                    title="Run migrations",
                    command="docker-compose exec app alembic upgrade head",
                    description="Run database migrations inside container",
                ),
            ])
        
        steps.extend([
            DeploymentStep(
                number=6,
                title="Verify deployment",
                command="curl http://localhost:8000/health",
                description="Check if API is running",
                expected_output='"status": "healthy"',
            ),
            DeploymentStep(
                number=7,
                title="View logs",
                command="docker-compose logs -f app",
                description="View application logs",
                is_optional=True,
            ),
        ])
        
        return steps
    
    def _get_kubernetes_steps(self, config: DeploymentConfig) -> List[DeploymentStep]:
        """Get Kubernetes deployment steps."""
        return [
            DeploymentStep(
                number=1,
                title="Create namespace",
                command="kubectl create namespace codeatlas",
                description="Create Kubernetes namespace",
            ),
            DeploymentStep(
                number=2,
                title="Create secrets",
                command='''kubectl create secret generic codeatlas-secrets \
  --namespace codeatlas \
  --from-literal=api-key='your-secure-api-key' \
  --from-literal=openai-api-key='sk-your-openai-key' \
  --from-file=database-url='./k8s/secrets/database-url.txt' \
  --from-file=redis-url='./k8s/secrets/redis-url.txt' ''',
                description="Create Kubernetes secrets for sensitive data",
            ),
            DeploymentStep(
                number=3,
                title="Apply configurations",
                command="kubectl apply -f k8s/configmap.yaml -f k8s/deployment.yaml -f k8s/service.yaml",
                description="Apply Kubernetes configurations",
            ),
            DeploymentStep(
                number=4,
                title="Deploy database",
                command="helm install codeatlas-db bitnami/postgresql --namespace codeatlas",
                description="Deploy PostgreSQL using Helm",
                is_optional=True,
            ),
            DeploymentStep(
                number=5,
                title="Deploy Redis",
                command="helm install codeatlas-redis bitnami/redis --namespace codeatlas",
                description="Deploy Redis using Helm",
                is_optional=True,
            ),
            DeploymentStep(
                number=6,
                title="Wait for pods",
                command="kubectl wait --for=condition=ready pod -l app=codeatlas --namespace codeatlas --timeout=300s",
                description="Wait for pods to be ready",
            ),
            DeploymentStep(
                number=7,
                title="Check deployment",
                command="kubectl get all --namespace codeatlas",
                description="Check all resources in namespace",
            ),
            DeploymentStep(
                number=8,
                title="Port forward",
                command="kubectl port-forward service/codeatlas-service 8000:80 --namespace codeatlas",
                description="Forward local port to service",
                is_optional=True,
            ),
        ]
    
    def _get_aws_steps(self, config: DeploymentConfig) -> List[DeploymentStep]:
        """Get AWS deployment steps."""
        return [
            DeploymentStep(
                number=1,
                title="Create ECR repository",
                command="aws ecr create-repository --repository-name codeatlas",
                description="Create Elastic Container Repository",
            ),
            DeploymentStep(
                number=2,
                title="Build and push Docker image",
                command='''docker build -t codeatlas .
docker tag codeatlas:latest $(aws sts get-caller-identity --query Account --output text).dkr.ecr.region.amazonaws.com/codeatlas:latest
aws ecr get-login-password --region region | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.region.amazonaws.com
docker push $(aws sts get-caller-identity --query Account --output text).dkr.ecr.region.amazonaws.com/codeatlas:latest''',
                description="Build Docker image and push to ECR",
            ),
            DeploymentStep(
                number=3,
                title="Create RDS instance",
                command='''aws rds create-db-instance \
  --db-instance-identifier codeatlas-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password "secure-password-here" \
  --allocated-storage 20''',
                description="Create PostgreSQL RDS instance",
            ),
            DeploymentStep(
                number=4,
                title="Create ElastiCache Redis",
                command='''aws elasticache create-cache-cluster \
  --cache-cluster-id codeatlas-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1''',
                description="Create Redis cluster",
            ),
            DeploymentStep(
                number=5,
                title="Create ECS cluster",
                command='''aws ecs create-cluster --cluster-name codeatlas-cluster
aws ecs register-task-definition --cli-input-json file://aws/task-definition.json
aws ecs create-service --cluster codeatlas-cluster --service-name codeatlas-service --task-definition codeatlas-task --desired-count 2''',
                description="Create ECS cluster and service",
            ),
            DeploymentStep(
                number=6,
                title="Create Application Load Balancer",
                command='''aws elbv2 create-load-balancer --name codeatlas-lb --subnets subnet-xxx subnet-yyy --security-groups sg-xxx
aws elbv2 create-target-group --name codeatlas-tg --protocol HTTP --port 80 --vpc-id vpc-xxx
aws elbv2 create-listener --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/codeatlas-lb/xxx --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/codeatlas-tg/xxx''',
                description="Create load balancer and configure routing",
            ),
        ]
    
    def _get_configuration(self, config: DeploymentConfig) -> Dict[str, Any]:
        """Get configuration details."""
        configurations = {
            "environment_variables": self._get_env_vars(config),
            "database_config": self._get_db_config(config),
            "redis_config": self._get_redis_config(config) if config.use_redis else None,
            "api_configuration": {
                "port": 8000,
                "workers": config.MAX_WORKERS if hasattr(config, 'MAX_WORKERS') else 4,
                "timeout": 300,
                "max_upload_size": "100MB",
            },
            "security": {
                "cors_origins": ["http://localhost:3000", "https://yourdomain.com"],
                "rate_limiting": "100 requests/minute",
                "api_key_rotation": "Recommended every 90 days",
            },
        }
        
        return configurations
    
    def _get_env_vars(self, config: DeploymentConfig) -> Dict[str, str]:
        """Get environment variables."""
        env_vars = {
            "API_KEY": "Secure API key for authentication",
            "OPENAI_API_KEY": "OpenAI API key for AI features",
            "DEBUG": "False in production",
            "DATABASE_URL": self._get_database_url(config),
        }
        
        if config.use_redis:
            env_vars["REDIS_URL"] = "Redis connection URL"
            