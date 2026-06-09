# AWS Deployment Guide

This guide summarizes how this FastAPI agent app is containerized and deployed on AWS using:

```text
FastAPI app
  -> Docker image
  -> Amazon ECR
  -> ECS Fargate service
  -> Application Load Balancer
  -> RDS PostgreSQL
  -> Secrets Manager
```

## Required Variables

Fill these values before running the AWS CLI commands in this guide.

### AWS Account And Region

```bash
export AWS_ACCOUNT_ID=347387311652
export AWS_REGION=us-east-1
```

### ECR / Image

```bash
export ECR_REPOSITORY=ai-agent-platform
export IMAGE_TAG=<image-tag>
export IMAGE_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
```

Current task definition image example:

```text
347387311652.dkr.ecr.us-east-1.amazonaws.com/ai-agent-platform:amd64-20260608203805
```

### ECS

```bash
export CLUSTER_NAME=<ecs-cluster-name>
export SERVICE_NAME=<ecs-service-name>
export TASK_FAMILY=ai-agent-platform-task
export CONTAINER_NAME=ai-agent-platform
export CONTAINER_PORT=8000
```

### Networking

```bash
export VPC_ID=<your-vpc-id>
export PUBLIC_SUBNET_1=<public-subnet-id-1>
export PUBLIC_SUBNET_2=<public-subnet-id-2>
export ALB_SECURITY_GROUP_ID=<alb-security-group-id>
export ECS_SECURITY_GROUP_ID=<ecs-security-group-id>
export RDS_SECURITY_GROUP_ID=<rds-security-group-id>
```

### ALB

```bash
export ALB_NAME=ai-agent-platform-alb
export TARGET_GROUP_NAME=ai-agent-platform-tg
export ALB_ARN=<load-balancer-arn>
export TARGET_GROUP_ARN=<target-group-arn>
export ALB_DNS=<alb-dns-name>
```

### RDS

```bash
export RDS_INSTANCE_ID=ai-agent-platform-db
export RDS_ENDPOINT=ai-agent-platform-db.c3wgqma4geuk.us-east-1.rds.amazonaws.com
export DB_PORT=5432
export DB_NAME=postgres
export DB_USER=postgres
export DB_SSLMODE=require
export RAG_DB_NAME=postgres
export RAG_TABLE_NAME=documents
```

Because the RDS instance was created without `--db-name`, this deployment uses the default `postgres` database for both app tables and the RAG vector table.

### Secrets Manager

```bash
export OPENAI_SECRET_ARN=arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:ai-agent-platform/openai-api-key
export DB_PASSWORD_SECRET_ARN=arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:ai-agent-platform/db-password
```

These secrets map to container environment variables:

```text
OPENAI_API_KEY <- OPENAI_SECRET_ARN
DB_PASSWORD <- DB_PASSWORD_SECRET_ARN
RAG_DB_PASSWORD <- DB_PASSWORD_SECRET_ARN
```

### App API Auth

```bash
export APP_API_KEY=<your-api-key>
```

Current task definition uses `dev-secret` as a plaintext placeholder. For a production-like eval endpoint, move `APP_API_KEY` to Secrets Manager too.

## Current AWS Files

- `Dockerfile`: builds the FastAPI container image.
- `.dockerignore`: keeps local files, `.env`, caches, logs, and virtualenvs out of the image.
- `ecs-task-definition.json`: ECS Fargate task definition for the app container.
- `ecs-trust-policy.json`: IAM trust policy for ECS tasks.
- `docker-compose.yml`: local-only stack for FastAPI + pgvector Postgres.
- `docker/postgres/init/01-create-databases.sql`: local Compose init script for `rag_db` and `vector`.

## Docker Image

The Docker image:

- Uses `python:3.12-slim`.
- Installs dependencies from `requirements.txt`.
- Copies the app into `/app`.
- Runs as a non-root `app` user.
- Exposes port `8000`.
- Runs:

```bash
uvicorn app:app --host 0.0.0.0 --port ${PORT} --proxy-headers
```

Build locally:

```bash
docker build -t ai-agent-platform:latest .
```

## Push Image to ECR

Create the ECR repository if it does not exist:

```bash
aws ecr create-repository \
  --repository-name ai-agent-platform \
  --region us-east-1
```

Login:

```bash
aws ecr get-login-password --region us-east-1 | docker login \
  --username AWS \
  --password-stdin 347387311652.dkr.ecr.us-east-1.amazonaws.com
```

Build for ECS/Fargate:

```bash
docker build --platform linux/amd64 \
  -t ai-agent-platform:amd64-$(date +%Y%m%d%H%M%S) .
```

Tag and push:

```bash
docker tag ai-agent-platform:<local-tag> \
  347387311652.dkr.ecr.us-east-1.amazonaws.com/ai-agent-platform:<image-tag>

docker push \
  347387311652.dkr.ecr.us-east-1.amazonaws.com/ai-agent-platform:<image-tag>
```

Then update `ecs-task-definition.json`:

```json
"image": "347387311652.dkr.ecr.us-east-1.amazonaws.com/ai-agent-platform:<image-tag>"
```

## RDS PostgreSQL

The RDS instance was created with:

```bash
aws rds create-db-instance \
  --db-instance-identifier ai-agent-platform-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --allocated-storage 20 \
  --master-username postgres \
  --master-user-password <password> \
  --publicly-accessible
```

Because no `--db-name` was provided, the app uses the default database:

```text
DB_NAME=postgres
RAG_DB_NAME=postgres
```

Current task definition points both app persistence and RAG vector storage to:

```text
ai-agent-platform-db.c3wgqma4geuk.us-east-1.rds.amazonaws.com
```

The code supports both local and RDS database modes through environment variables:

```text
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
DB_SSLMODE

RAG_DB_HOST
RAG_DB_PORT
RAG_DB_NAME
RAG_DB_USER
RAG_DB_PASSWORD
RAG_DB_SSLMODE
RAG_TABLE_NAME
```

For RDS, use:

```text
DB_SSLMODE=require
RAG_DB_SSLMODE=require
```

## Secrets Manager

The task definition reads secrets from AWS Secrets Manager:

```json
"secrets": [
  {
    "name": "OPENAI_API_KEY",
    "valueFrom": "arn:aws:secretsmanager:us-east-1:347387311652:secret:ai-agent-platform/openai-api-key"
  },
  {
    "name": "DB_PASSWORD",
    "valueFrom": "arn:aws:secretsmanager:us-east-1:347387311652:secret:ai-agent-platform/db-password"
  },
  {
    "name": "RAG_DB_PASSWORD",
    "valueFrom": "arn:aws:secretsmanager:us-east-1:347387311652:secret:ai-agent-platform/db-password"
  }
]
```

Create or update secrets:

```bash
aws secretsmanager create-secret \
  --name ai-agent-platform/openai-api-key \
  --secret-string "<openai-api-key>" \
  --region us-east-1

aws secretsmanager create-secret \
  --name ai-agent-platform/db-password \
  --secret-string "<rds-password>" \
  --region us-east-1
```

If the secret already exists:

```bash
aws secretsmanager put-secret-value \
  --secret-id ai-agent-platform/openai-api-key \
  --secret-string "<openai-api-key>" \
  --region us-east-1
```

## IAM

`ecs-trust-policy.json` lets ECS tasks assume the task role:

```json
{
  "Principal": {
    "Service": "ecs-tasks.amazonaws.com"
  },
  "Action": "sts:AssumeRole"
}
```

The ECS task execution role must also be able to:

- Pull from ECR.
- Write logs to CloudWatch.
- Read the Secrets Manager secrets.

Minimum additional Secrets Manager permission:

```json
{
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": [
    "arn:aws:secretsmanager:us-east-1:347387311652:secret:ai-agent-platform/*"
  ]
}
```

## CloudWatch Logs

The task definition sends logs to:

```text
/ecs/ai-agent-platform
```

Create the log group if needed:

```bash
aws logs create-log-group \
  --log-group-name /ecs/ai-agent-platform \
  --region us-east-1
```

## ECS Task Definition

Register the task definition:

```bash
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json \
  --region us-east-1
```

Important task settings:

- Launch type: Fargate
- Network mode: `awsvpc`
- CPU: `512`
- Memory: `1024`
- Container port: `8000`
- Image: ECR image URI
- Secrets: OpenAI API key and DB password

## ECS Service

Create or update an ECS Fargate service using:

- Cluster: your ECS cluster
- Task definition: `ai-agent-platform-task`
- Desired count: `1`
- Launch type: Fargate
- Networking: subnets and security group that can reach RDS
- Load balancer: Application Load Balancer target group

If updating an existing service:

```bash
aws ecs update-service \
  --cluster <cluster-name> \
  --service <service-name> \
  --task-definition ai-agent-platform-task \
  --force-new-deployment \
  --region us-east-1
```

## Application Load Balancer

ALB target group should use:

```text
Target type: IP
Protocol: HTTP
Port: 8000
Health check path: /
```

The app health endpoint returns:

```json
{"status":"ok","app":"AI Agent Platform"}
```

## Expose As REST API With ALB

Use this path when the ECS task already runs successfully and you want a stable HTTP endpoint for eval jobs.

Set local shell variables first:

```bash
export AWS_REGION=us-east-1
export VPC_ID=<your-vpc-id>  #vpc-02f4def1c5eee6954
export PUBLIC_SUBNET_1=<public-subnet-id-1> #subnet-0855e9dcfa421ccaa
export PUBLIC_SUBNET_2=<public-subnet-id-2> #subnet-0ab8e46cd1a51c872
export CLUSTER_NAME=<ecs-cluster-name> #ai-agent-platform-cluster
export SERVICE_NAME=<ecs-service-name> #ai-agent-platform-service
```

### 1. Create Security Groups

Create an ALB security group:

```bash
aws ec2 create-security-group \
  --group-name ai-agent-platform-alb-sg \
  --description "ALB access for ai-agent-platform" \
  --vpc-id $VPC_ID \
  --region $AWS_REGION
```

Allow public HTTP traffic to the ALB:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-0b5b6e0611ee80f44 \ 
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region $AWS_REGION
```
#sg-0b5b6e0611ee80f44

Create an ECS task security group:

```bash
aws ec2 create-security-group \
  --group-name ai-agent-platform-ecs-sg \
  --description "ECS task access for ai-agent-platform" \
  --vpc-id $VPC_ID \
  --region $AWS_REGION
```

Allow only the ALB to reach the ECS task on app port `8000`:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-03fbb228cc33d99d5 \
  --protocol tcp \
  --port 8000 \
  --source-group sg-0b5b6e0611ee80f44 \
  --region $AWS_REGION
```

Make sure the RDS security group allows inbound PostgreSQL from the ECS task security group:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <rds-security-group-id sg-0c4d439f509ca127b> \
  --protocol tcp \
  --port 5432 \
  --source-group sg-0b5b6e0611ee80f44 \
  --region $AWS_REGION
```

### 2. Create The ALB

```bash
aws elbv2 create-load-balancer \
  --name ai-agent-platform-alb \
  --type application \
  --scheme internet-facing \
  --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 \
  --security-groups sg-0b5b6e0611ee80f44 \
  --region $AWS_REGION
```

Save the returned ALB ARN and DNS name:

```bash
export ALB_ARN=<load-balancer-arn>
export ALB_DNS=<alb-dns-name>
```

### 3. Create Target Group

For Fargate, target type must be `ip`:

```bash
aws elbv2 create-target-group \
  --name ai-agent-platform-tg \
  --protocol HTTP \
  --port 8000 \
  --target-type ip \
  --vpc-id $VPC_ID \
  --health-check-protocol HTTP \
  --health-check-path / \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher HttpCode=200 \
  --region $AWS_REGION
```

Save the target group ARN:

```bash
export TARGET_GROUP_ARN=<target-group-arn>
```

### 4. Create HTTP Listener

```bash
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
  --region $AWS_REGION
```

### 5. Attach ALB To ECS Service

If creating a new service, include the target group:

```bash
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition ai-agent-platform-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$PUBLIC_SUBNET_1,$PUBLIC_SUBNET_2],securityGroups=[<ecs-security-group-id>],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=ai-agent-platform,containerPort=8000" \
  --region $AWS_REGION
```

If the service already exists without a load balancer, the cleanest path is usually to create a replacement ECS service with the ALB attached. ECS service load balancer configuration is not something you can freely add to every existing service in-place after creation.

### 6. Verify Target Health

```bash
aws elbv2 describe-target-health \
  --target-group-arn $TARGET_GROUP_ARN \
  --region $AWS_REGION
```

Wait until targets show:

```text
State: healthy
```

### 7. Use As Eval REST API

Health check:

```bash
curl "http://$ALB_DNS/"
```

List tools:

```bash
curl \
  -H "X-API-Key: dev-secret" \
  "http://$ALB_DNS/tools"
```

Chat request for eval:

```bash
curl \
  -X POST "http://$ALB_DNS/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{
    "message": "What is in the return policy?",
    "session_id": "eval-run-001"
  }'
```

Your eval runner should call:

```text
POST http://<alb-dns-name>/chat
Header: X-API-Key: <APP_API_KEY>
Body: {"message": "...", "session_id": "..."}
```

For production-like evals, move `APP_API_KEY` from plaintext task environment to Secrets Manager and use HTTPS on the ALB.

## Security Groups

Recommended rules:

- ALB security group:
  - Inbound HTTP/HTTPS from the internet.
  - Outbound to ECS task security group.
- ECS task security group:
  - Inbound `8000` from ALB security group.
  - Outbound `5432` to RDS security group.
  - Outbound HTTPS for OpenAI API.
- RDS security group:
  - Inbound `5432` from ECS task security group.

Even if RDS is public, prefer allowing only the ECS task security group.

## RAG Setup on RDS

The RAG vector store uses PostgreSQL plus pgvector. On RDS PostgreSQL, enable the extension once:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Then build the index with RDS environment variables:

```bash
python build_index.py
```

This can be run locally against RDS or as a one-off ECS task.

## API Checks

Health check:

```bash
curl http://<alb-dns-name>/
```

List tools:

```bash
curl \
  -H "X-API-Key: dev-secret" \
  http://<alb-dns-name>/tools
```

Chat:

```bash
curl \
  -X POST http://<alb-dns-name>/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{"message":"What is in the return policy?","session_id":"demo"}'
```

## Production Notes

- Move `APP_API_KEY` to Secrets Manager instead of keeping it as plaintext in the task definition.
- Rotate any secrets that were ever pasted into local files or terminal output.
- Prefer private subnets for ECS tasks and RDS when a NAT Gateway is available.
- Use HTTPS on the ALB before exposing the service broadly.
- Consider an explicit migration flow instead of creating draft tables on app startup.
