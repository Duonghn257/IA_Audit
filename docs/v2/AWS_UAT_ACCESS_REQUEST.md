# Minimal AWS UAT Access Request

> **Product:** Operation Report Jedi  
> **Environment:** Internal UAT  
> **Region:** `ap-southeast-1` (or the company-standard region)  
> **Scope:** [SRS 0.4](SOFTWARE_REQUIREMENTS_SPECIFICATION.md)

## Required services only

| Service | Why it is needed | Request |
|---|---|---|
| IAM | Deploy and run containers with scoped access | One delivery deployment role, one ECS task execution role, and one application task role; UAT resources only |
| Amazon ECR | Store private portal/API and worker images | Two private repositories; allow the delivery role to push images |
| Amazon ECS on Fargate | Run the portal/API and background worker | One cluster, one portal/API service, one worker service |
| VPC, security groups, internal ingress | Private communication and internal-only portal access | Allow the portal only from corporate VPN/approved corporate IP ranges; no public RDS or S3 |
| ALB + HTTPS certificate | Stable internal HTTPS URL and 100 MB folder upload | One ALB, listener, target group and certificate. Route 53 only if company DNS is hosted in AWS. |
| Amazon RDS for PostgreSQL | Projects, versions, issues, durable job records/events and audit metadata | One encrypted PostgreSQL UAT instance/database with automated backups |
| Amazon S3 | Source snapshot, parsed artefacts, central assets and versioned DOCX output | One private bucket, Block Public Access, TLS-only policy and lifecycle rules |
| AWS Secrets Manager | Anthropic API key, database password and app secrets | Permit ECS tasks to read only named UAT secrets |
| Amazon CloudWatch | Container logs and basic operational troubleshooting | UAT log groups, retention policy and basic ECS/error alarms |

### Minimal implementation choices

- The worker reads durable jobs from PostgreSQL; **SQS/DLQ is not required** in this UAT.
- The application calls Anthropic using the existing API key over outbound HTTPS; **Amazon Bedrock is not required**.
- Scanned-PDF OCR is not in scope; **Amazon Textract is not required**.
- The UAT has no application login, RBAC or project-level authorization. Entra ID registration is deferred and is not an AWS request. Internal network access is the UAT access boundary.
- Use AWS-managed encryption for UAT rather than requesting a customer-managed KMS key.

## IAM access requested

### 1. Delivery deployment role (shared by the two developers)

Scope this role to `operation-report-jedi-uat-*` resources only:

- ECR image push/pull.
- ECS task-definition registration and API/worker service deployment.
- `iam:PassRole` only for the named UAT ECS roles.
- Read-only ECS, ALB, RDS, VPC and CloudWatch diagnostics.
- UAT S3 object read/list access for deployment verification only.

Do not grant account administrator, unrestricted IAM, or access to production data.

### 2. ECS task execution role

Use the standard ECS task execution permissions to pull private ECR images,
write CloudWatch logs and inject only named UAT secrets.

### 3. ECS application task role (shared by API and worker for UAT)

- Read/write/list objects only in the UAT S3 bucket/prefixes needed by the app.
- Read only named UAT Secrets Manager secrets.
- No Bedrock, Textract, SQS, Cognito or broad KMS permissions.

## Network and storage guardrails

- ALB HTTPS ingress: corporate VPN/approved corporate egress IP ranges only.
- ECS API receives inbound traffic only from the ALB; the worker receives no inbound traffic.
- RDS port 5432 accepts traffic only from the ECS application security group.
- S3 remains private; users download DOCX through the application, not a public bucket URL.
- ECS needs outbound HTTPS (443) to the Anthropic API and required AWS endpoints.
- Store no AWS access keys in source code, browser code or task-definition plaintext.

## Explicitly not requested for this UAT

Amazon Bedrock, Amazon Textract, SQS/DLQ, Amazon Cognito, customer-managed
KMS, API Gateway, Lambda, EKS, EFS, ElastiCache, WAF, SharePoint/Microsoft
Graph, and Entra ID configuration.

## Copy-ready request for Cloud/Infrastructure

> Please provision a minimal internal UAT environment for Operation Report Jedi
> in `ap-southeast-1` (or our standard region): private ECR repositories; ECS
> Fargate portal/API and worker services; an HTTPS ALB restricted to our corporate
> VPN/approved corporate IP ranges; RDS PostgreSQL; a private S3 bucket; Secrets
> Manager; and CloudWatch logs. Please create one least-privilege deployment
> role for the two developers, one ECS task execution role, and one scoped ECS
> application task role. The worker uses PostgreSQL-backed jobs and the existing
> Anthropic API key, so Bedrock, Textract, SQS/DLQ, Cognito, and a customer-managed
> KMS key are not needed. There is no application login or RBAC in this UAT;
> access is restricted at the internal network boundary.

## Reference

- [Amazon ECS task IAM roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
