# Operation Report Jedi - Production Cost Estimate

**Date:** 2026-05-21  
**Currency:** USD  
**Region used for estimate:** US East (N. Virginia, `us-east-1`) unless noted  
**Architecture:** Portal upload -> API Gateway -> ECS/Fargate web app + worker -> S3/RDS/ElastiCache -> Textract -> AWS Bedrock Claude -> CloudWatch

This estimate uses the current public AWS pricing data available on 2026-05-21 and a **100-page/month** production workload assumption. It excludes taxes, enterprise support, private discounts, free-tier credits, data transfer to the public internet, NAT Gateway, WAF, CI/CD, backups beyond the assumptions below, and any non-AWS portal licensing.

## 1. Service Purpose

| Service | Purpose in Operation Report Jedi |
|---|---|
| Amazon API Gateway | Receives portal API traffic for evidence upload initiation, audit job submission, job status polling, metadata reads, and report download requests. |
| AWS ECS/Fargate Web App | Hosts the backend API, orchestrator, and lightweight control logic without managing EC2 servers. |
| AWS ECS/Fargate Worker | Runs report-generation jobs: parse uploaded evidence, assemble context, call Bedrock, validate results, and render output artifacts. |
| Amazon S3 | Durable object storage for uploaded evidence, parsed document cache, intermediate JSON, generated DOCX/PDF outputs, and downloadable packages. |
| Amazon Textract | OCR and document-structure extraction for PDFs/images where text, table, and layout extraction are needed before LLM processing. |
| AWS Bedrock Claude | LLM inference layer for constraint extraction, issue drafting, citation-aware validation, and critique/rewrite passes. |
| Amazon RDS for PostgreSQL | Relational metadata store for cases, jobs, users, report versions, audit log indexes, and artifact references. |
| Amazon ElastiCache Serverless for Valkey | Low-latency ephemeral store for job progress, locks, short-lived cache entries, and worker coordination state. |
| Amazon CloudWatch | Central logging, metrics, alarms, and operational visibility for API, worker, parsing, and report-generation failures. |
| Amazon EKS | Optional alternative container orchestration platform if CDL standardizes on Kubernetes; not required for the lower-cost ECS baseline. |

## 2. Base AWS Pricing

This section states the base public price for each service in the same style as the AWS pricing pages. Prices are for US East (N. Virginia, `us-east-1`) unless noted.

| Service | Base public price | How it applies in this project |
|---|---:|---|
| Amazon Textract - Detect Document Text | $1.50 per 1,000 pages for the first 1M pages/month; $0.60 per 1,000 pages after that | Cheapest OCR-only option for extracting plain text from uploaded documents |
| Amazon Textract - AnalyzeDocument Tables | $15.00 per 1,000 pages for the first 1M pages/month; $10.00 per 1,000 pages after that | Used when audit evidence contains structured tables |
| Amazon Textract - AnalyzeDocument Layout | $4.00 per 1,000 pages for the first 1M pages/month; $3.00 per 1,000 pages after that | Used to preserve document layout and section structure |
| Amazon Textract - AnalyzeDocument Forms | $50.00 per 1,000 pages for the first 1M pages/month; $40.00 per 1,000 pages after that | Optional; only needed if key-value form extraction is required |
| AWS Bedrock Claude Sonnet 4.6 | $3.00 per 1M input tokens; $15.00 per 1M output tokens | Used for constraint extraction, drafting, validation, and critique |
| Amazon API Gateway HTTP API | $1.00 per 1M requests for the first 300M requests/month; $0.90 per 1M requests after that | Handles upload, run, status, metadata, and download API calls |
| AWS Fargate Linux/x86 compute | $0.04048 per vCPU-hour and $0.004445 per GB-hour | Runs the always-on web app and short-lived report workers |
| Amazon S3 Standard storage | $0.023 per GB-month for the first 50 TB/month | Stores uploaded evidence, parsed cache, and output artifacts |
| Amazon S3 PUT/COPY/POST/LIST | $0.005 per 1,000 requests | Charged when files and metadata are uploaded or listed |
| Amazon S3 GET and other requests | $0.004 per 10,000 requests | Charged when reports and artifacts are downloaded/read |
| Amazon ElastiCache Serverless for Valkey storage | $0.084 per GB-hour | Stores short-lived job state and coordination data |
| Amazon ElastiCache Serverless for Valkey processing | $0.0023 per 1M ECPUs | Charged for cache request processing |
| Amazon RDS for PostgreSQL db.t4g.micro Single-AZ | $0.016 per DB instance-hour | Runs the production metadata database |
| Amazon RDS for PostgreSQL gp3 storage | $0.115 per GB-month | Stores case/job/report metadata and audit trail references |
| Amazon CloudWatch Logs ingestion | $0.50 per GB ingested | Collects API, worker, and orchestration logs |
| Amazon CloudWatch Logs storage | $0.03 per GB-month | Retains operational logs for audit and troubleshooting |
| Amazon CloudWatch custom metrics | $0.30 per metric-month for the first 10,000 metrics | Tracks job counts, failures, latency, token usage, and parsing status |
| Amazon CloudWatch standard alarms | $0.10 per alarm-month | Alerts on failed jobs, high error rate, or abnormal latency |
| Amazon EKS standard cluster support | $0.10 per cluster-hour | Optional Kubernetes alternative to ECS; not included in the ECS baseline |

## 3. Unit Rates Used

| Service | Unit rate | Source |
|---|---:|---|
| Claude Sonnet 4.6 input | $3.00 / 1M tokens | Anthropic pricing; AWS Bedrock model card points to Bedrock pricing |
| Claude Sonnet 4.6 output | $15.00 / 1M tokens | Anthropic pricing; AWS Bedrock model card points to Bedrock pricing |
| Textract AnalyzeDocument Tables | $0.015 / page | AWS Price List, `AmazonTextract`, us-east-1 |
| Textract AnalyzeDocument Layout | $0.004 / page | AWS Price List, `AmazonTextract`, us-east-1 |
| Textract DetectDocumentText OCR only | $0.0015 / page | AWS Price List, `AmazonTextract`, us-east-1 |
| API Gateway HTTP API | $1.00 / 1M requests | AWS Price List, `AmazonApiGateway`, us-east-1 |
| Fargate Linux/x86 vCPU | $0.04048 / vCPU-hour | AWS Price List, `AmazonECS`, us-east-1 |
| Fargate Linux/x86 memory | $0.004445 / GB-hour | AWS Price List, `AmazonECS`, us-east-1 |
| S3 Standard storage | $0.023 / GB-month | AWS Price List, `AmazonS3`, us-east-1 |
| S3 PUT/COPY/POST/LIST | $0.005 / 1,000 requests | AWS Price List, `AmazonS3`, us-east-1 |
| S3 GET and other requests | $0.004 / 10,000 requests | AWS Price List, `AmazonS3`, us-east-1 |
| ElastiCache Serverless Valkey storage | $0.084 / GB-hour | AWS Price List, `AmazonElastiCache`, us-east-1 |
| ElastiCache Serverless Valkey ECPU | $0.0023 / 1M ECPUs | AWS Price List, `AmazonElastiCache`, us-east-1 |
| RDS PostgreSQL db.t4g.micro Single-AZ | $0.016 / hour | AWS Price List, `AmazonRDS`, us-east-1 |
| RDS PostgreSQL gp3 storage | $0.115 / GB-month | AWS Price List, `AmazonRDS`, us-east-1 |
| CloudWatch log ingestion | $0.50 / GB | AWS Price List, `AmazonCloudWatch`, us-east-1 |
| CloudWatch log storage | $0.03 / GB-month | AWS Price List, `AmazonCloudWatch`, us-east-1 |
| CloudWatch custom metrics | $0.30 / metric-month | AWS Price List, `AmazonCloudWatch`, us-east-1 |
| CloudWatch standard alarms | $0.10 / alarm-month | AWS Price List, `AmazonCloudWatch`, us-east-1 |
| EKS standard cluster fee | $0.10 / cluster-hour | Amazon EKS pricing page |

## 4. Workload Assumptions

| Parameter | Value | Notes |
|---|---:|---|
| Audit pages per year | 1,200 pages | 100 pages/month x 12 |
| Pages per month | 100 pages | Updated sizing assumption |
| Tokens per page | 1,000 tokens | Approx. 250 words/page x 4 tokens/word |
| Total document tokens/year | 1.2M tokens | 1,200 x 1,000 |
| LLM input/output ratio | 90% input / 10% output | Typical document-processing split |
| LLM input tokens/year | 1.08M | 1.2M x 90% |
| LLM output tokens/year | 0.12M | 1.2M x 10% |
| Audit/report jobs/year | 24 jobs | Assumes 2 report generations/re-runs per month |
| Worker runtime/job | 30 minutes | Includes orchestration, parsing calls, Bedrock calls, DOCX rendering |
| Average raw + parsed + output storage | 5 GB | Conservative for uploaded evidence, parsed cache, generated reports, metadata exports |
| API requests/year | 5,000 | Portal upload, run status, download, metadata calls |
| CloudWatch logs | 1 GB/month | Application + worker logs |
| RDS size | 20 GB gp3 | Case metadata, audit log references, job/report metadata |
| Cache size | 100 MB minimum | ElastiCache Serverless for Valkey minimum metered storage |

## 5. Detailed Calculation

### 5.1 AWS Bedrock Claude

Assumed model: Claude Sonnet 4.6 on AWS Bedrock. The AWS model card lists Claude Sonnet 4.6 as active, with a 1M token context window, 64K max output, and Bedrock model IDs such as `anthropic.claude-sonnet-4-6` and `global.anthropic.claude-sonnet-4-6`.

Baseline calculation:

| Item | Formula | Annual cost |
|---|---:|---:|
| Input tokens | 1.08M x $3.00 / MTok | $3.24 |
| Output tokens | 0.12M x $15.00 / MTok | $1.80 |
| **Total Bedrock Claude** | $3.24 + $1.80 | **$5.04** |

If the implementation uses a regional/geo endpoint with a 10% premium instead of a global endpoint, budget approximately **$5.54/year** for the same token volume.

### 5.2 Amazon Textract

Baseline assumes every page is sent through AnalyzeDocument with Tables + Layout:

| Item | Formula | Annual cost |
|---|---:|---:|
| Tables | 1,200 pages x $0.015/page | $18.00 |
| Layout | 1,200 pages x $0.004/page | $4.80 |
| **Total Textract baseline** | $18.00 + $4.80 | **$22.80** |

Sensitivity:

| Parse profile | Formula | Annual cost |
|---|---:|---:|
| OCR only | 1,200 x $0.0015 | $1.80 |
| Tables only | 1,200 x $0.015 | $18.00 |
| Tables + Layout | 1,200 x ($0.015 + $0.004) | $22.80 |
| Forms + Tables + Layout | 1,200 x ($0.05 + $0.015 + $0.004) | $82.80 |

Recommendation: keep the default production parser at Tables + Layout for audit documents, and only enable Forms for specific document classes where key-value extraction is needed.

### 5.3 Amazon API Gateway

Assumption: HTTP API, 5,000 requests/year.

| Item | Formula | Annual cost |
|---|---:|---:|
| HTTP API requests | 5,000 / 1,000,000 x $1.00 | $0.01 |
| **Total API Gateway** |  | **$0.01** |

If REST API is required instead of HTTP API, the first-tier request price is $3.50 per 1M requests, so the same workload is still only about $0.02/year before data transfer.

### 5.4 AWS Fargate - Web App and Worker

Baseline web app: 1 always-on ECS/Fargate task, Linux/x86, 0.25 vCPU, 0.5 GB RAM, 730 hours/month.

| Item | Formula | Annual cost |
|---|---:|---:|
| Web vCPU | 0.25 vCPU x $0.04048 x 730 x 12 | $88.65 |
| Web memory | 0.5 GB x $0.004445 x 730 x 12 | $19.47 |
| **Total web app task** |  | **$108.12** |

Baseline worker: 24 jobs/year, 30 minutes/job, 1 vCPU, 2 GB RAM.

| Item | Formula | Annual cost |
|---|---:|---:|
| Worker vCPU | 24 x 0.5 hr x 1 vCPU x $0.04048 | $0.49 |
| Worker memory | 24 x 0.5 hr x 2 GB x $0.004445 | $0.11 |
| **Total worker tasks** |  | **$0.59** |

For production HA, run at least 2 web tasks across availability zones. That adds approximately **$108.12/year**.

### 5.5 Amazon S3

Assumption: 5 GB average S3 Standard storage, 5,000 PUT/LIST-type requests/year, 12,000 GET-type requests/year.

| Item | Formula | Annual cost |
|---|---:|---:|
| Storage | 5 GB x $0.023 x 12 | $1.38 |
| PUT/COPY/POST/LIST | 5,000 / 1,000 x $0.005 | $0.03 |
| GET and other requests | 12,000 / 10,000 x $0.004 | $0.00 |
| **Total S3** |  | **$1.41** |

### 5.6 Amazon ElastiCache

Assumption: ElastiCache Serverless for Valkey, minimum 100 MB metered data, 1M ECPUs/year.

| Item | Formula | Annual cost |
|---|---:|---:|
| Valkey cached data | 0.1 GB x $0.084 x 8,760 hours | $73.58 |
| ECPUs | 1M x $0.0023 / 1M | $0.00 |
| **Total ElastiCache** |  | **$73.59** |

Alternative: a dedicated `cache.t4g.micro` Valkey node is about **$112.13/year** (`$0.0128 x 8,760`). For this workload, Serverless Valkey is cheaper and simpler.

### 5.7 Amazon RDS for PostgreSQL

Assumption: Single-AZ `db.t4g.micro`, 20 GB gp3 storage.

| Item | Formula | Annual cost |
|---|---:|---:|
| DB instance | $0.016/hour x 8,760 hours | $140.16 |
| GP3 storage | 20 GB x $0.115 x 12 | $27.60 |
| **Total RDS** |  | **$167.76** |

Multi-AZ instance cost for the same instance class is $0.032/hour, or **$280.32/year** before storage and backup effects. Use Multi-AZ when this becomes a production system of record rather than a low-volume internal tool.

### 5.8 Amazon CloudWatch

Assumption: 1 GB/month log ingestion, 1 GB/month retained log storage, 10 custom metrics, 5 standard alarms.

| Item | Formula | Annual cost |
|---|---:|---:|
| Log ingestion | 12 GB x $0.50 | $6.00 |
| Log storage | 12 GB-month x $0.03 | $0.36 |
| Custom metrics | 10 metrics x $0.30 x 12 | $36.00 |
| Standard alarms | 5 alarms x $0.10 x 12 | $6.00 |
| **Total CloudWatch** |  | **$48.36** |

Cost note: custom metrics are the main CloudWatch driver in this small workload. Prefer built-in ECS/RDS metrics where possible and add custom metrics only for job status, parsing failure rate, Bedrock token usage, validation warnings, and report generation duration.

## 6. Production Options and Sensitivity

### 6.1 LLM Cost by Output Ratio

Using 1.2M total tokens/year and Claude Sonnet 4.6 rates:

| Output ratio | Input tokens | Output tokens | Annual Bedrock cost |
|---:|---:|---:|---:|
| 10% output | 1.08M | 0.12M | $5.04 |
| 25% output | 0.90M | 0.30M | $7.20 |
| 50% output | 0.60M | 0.60M | $10.80 |
| 75% output | 0.30M | 0.90M | $14.40 |

Output length matters because Claude output tokens cost 5x input tokens in this model.

### 6.2 LLM Cost by Report Iterations

If every report is generated multiple times, token cost scales linearly unless prompt caching or cached parsed context is used.

| Generation passes/year | Annual Bedrock cost |
|---:|---:|
| 1x baseline | $5.04 |
| 3x drafts/re-runs | $15.12 |
| 5x drafts/re-runs | $25.20 |
| 10x drafts/re-runs | $50.40 |

### 6.3 Page Volume Sensitivity

Assuming the baseline parse profile (Textract Tables + Layout), 90/10 LLM split, and fixed infrastructure unchanged:

| Pages/year | Bedrock cost | Textract cost | Variable subtotal |
|---:|---:|---:|---:|
| 1,200 | $5.04 | $22.80 | $27.84 |
| 4,500 | $18.90 | $85.50 | $104.40 |
| 10,000 | $42.00 | $190.00 | $232.00 |
| 25,000 | $105.00 | $475.00 | $580.00 |

Fixed infrastructure in the baseline is about **$400/year** before HA. At low volume, fixed costs dominate. At high volume, Textract becomes the main variable cost.

## 7. Cost Optimization Recommendations

1. Use ECS/Fargate first, not EKS, unless Kubernetes is required by platform standards. EKS adds about $876/year per standard cluster before worker compute.
2. Keep the web app small and autoscale workers per job. The worker cost is negligible when it only runs during report generation.
3. Use Textract selectively. Many DOCX/XLSX/text PDFs can be parsed without Textract; reserve Textract Tables/Layout for scanned PDFs and image-heavy audit evidence.
4. Cache parsed documents and reusable guideline/SOP context. This prevents repeated Textract charges and reduces Bedrock input tokens during re-runs.
5. Consider Bedrock/Claude prompt caching for stable reference documents such as Guidelines, SOP, Process Understanding, and report templates.
6. Avoid NAT Gateway if possible for this small workload. Prefer private subnets with VPC endpoints for AWS services, or public Fargate tasks locked down through security groups if the security model allows it.
7. Keep CloudWatch custom metrics minimal. Logs are cheap at this scale; custom metrics can exceed the logs bill.
8. Revisit RDS once metadata requirements are clearer. For a first production build, RDS is reasonable. If metadata stays simple, DynamoDB or S3 metadata manifests could reduce fixed database cost.

## 8. Sources Checked

Official AWS and Anthropic sources:

- [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
- [AWS Bedrock Claude Sonnet 4.6 model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4-6.html)
- [Anthropic Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [Amazon Textract pricing](https://aws.amazon.com/textract/pricing/)
- [AWS Fargate pricing](https://aws.amazon.com/fargate/pricing/)
- [Amazon API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/)
- [Amazon S3 pricing](https://aws.amazon.com/s3/pricing/)
- [Amazon ElastiCache pricing](https://aws.amazon.com/elasticache/pricing/)
- [Amazon RDS for PostgreSQL pricing](https://aws.amazon.com/rds/postgresql/pricing/)
- [Amazon CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [Amazon EKS pricing](https://aws.amazon.com/eks/pricing/)
- [AWS Price List Bulk API documentation](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-the-aws-price-list-bulk-api-fetching-price-list-files-manually.html)

AWS Price List files used for exact unit rates:

- `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonTextract/current/us-east-1/index.json` published `2024-10-29T16:40:50Z`
- `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/us-east-1/index.json` published `2026-05-15T17:28:46Z`
- `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonApiGateway/current/us-east-1/index.json` published `2025-11-20T01:06:52Z`
- `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-1/index.json` published `2026-05-12T17:05:32Z`
- `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonElastiCache/current/us-east-1/index.json` published `2026-05-20T17:06:00Z`
- `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json` published `2026-05-20T08:52:12Z`
- `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/us-east-1/index.json` published `2026-03-13T17:42:19Z`

## 9. Summary

| Cost area | Purpose | Annual cost | Monthly average | Notes |
|---|---|---:|---:|---|
| AWS Bedrock Claude Sonnet 4.6 | Generate and validate the audit report content from parsed evidence and references | $5.04 | $0.42 | 1.08M input tokens + 0.12M output tokens |
| Amazon Textract | Extract text, tables, and document layout from uploaded PDFs/images | $22.80 | $1.90 | Baseline assumes AnalyzeDocument Tables + Layout for all 1,200 pages |
| Amazon API Gateway | Expose portal-facing backend APIs for upload, job start, status, and download | $0.01 | $0.00 | HTTP API, 5,000 requests/year |
| AWS Fargate - always-on web app | Run the API/orchestrator container without managing servers | $108.12 | $9.01 | 1 task, 0.25 vCPU, 0.5 GB RAM, 24x7 |
| AWS Fargate - report workers | Run short-lived parsing/generation/rendering jobs on demand | $0.59 | $0.05 | 24 jobs/year, 30 minutes/job, 1 vCPU, 2 GB RAM |
| Amazon S3 | Store uploaded evidence, parsed cache, generated reports, and artifacts | $1.41 | $0.12 | 5 GB average storage + light requests |
| Amazon ElastiCache Serverless for Valkey | Track job state, progress, locks, and short-lived cache entries | $73.59 | $6.13 | 100 MB minimum cache footprint |
| Amazon RDS for PostgreSQL | Store case metadata, report metadata, user/job records, and audit trail references | $167.76 | $13.98 | Single-AZ db.t4g.micro + 20 GB gp3 |
| Amazon CloudWatch | Store logs, metrics, alarms, and operational traces | $48.36 | $4.03 | Logs, 10 custom metrics, 5 alarms |
| **Estimated baseline total** |  | **$427.67/year** | **$35.64/month** | Before tax/discounts/free tier |

Production high-availability options:

| Option | Incremental annual cost | New annual total | Notes |
|---|---:|---:|---|
| Add second always-on Fargate web task | +$108.12 | $535.79 | Basic app-level redundancy |
| Use EKS instead of ECS | +$876.00 | $1,303.67 | EKS standard cluster fee only; worker compute still billed separately |

Key takeaway: at this workload size, LLM and document parsing are not the main cost drivers. Always-on infrastructure, especially RDS, Fargate, ElastiCache, and CloudWatch metrics, dominates the bill.
