# MLOps Churn Project — Interview Q&A Guide

> **How to use this document:**  
> Each answer is written in a natural, first-person, conversational tone — the way you'd actually speak in an interview.  
> Read them aloud. Make them your own. Don't memorize word-for-word; understand the *why* behind each answer.

---

## Q1. Explain your MLOps project to me like I'm a non-technical manager.

**Answer:**

"Sure — let me give you the big picture first.

We had a machine learning model that predicts customer churn — basically, it tells us which customers are likely to cancel their subscription. That model was built by the data science team, but a model sitting on a laptop helps no one. My job was to take that model and build the *plumbing* around it so it could actually run in production, at scale, reliably.

Think of it like this: the data scientists built the engine. I built the car around it — the chassis, the dashboard, the safety systems.

Specifically, I did four things:

1. **Deployed the model to AWS** — so it runs in the cloud and can handle real traffic 24/7.
2. **Built a monitoring dashboard** — so the team could see at a glance if the model was healthy, how fast it was responding, and whether it was making accurate predictions. No more digging through logs.
3. **Automated the retraining process** — models get stale. Customer behavior changes. I set up a pipeline that automatically retrains the model on fresh data on a schedule.
4. **Fixed security and configuration issues** — there were IAM permission problems that were blocking deployments. I resolved those so the team could ship without manual workarounds.

The end result: the model went from something that needed constant babysitting to a system that largely takes care of itself."

---

## Q2. What is MLOps and why does a machine learning model need infrastructure care?

**Answer:**

"MLOps stands for Machine Learning Operations. It's essentially DevOps practices — CI/CD, monitoring, infrastructure as code — applied specifically to machine learning systems.

The reason ML models need special care is something called **data drift** or **model drift**. Here's the core problem: when you train a model, you train it on historical data. But the real world keeps changing. Customer behavior changes, market conditions change, even the way data gets collected can change. Over time, the patterns the model learned become less and less accurate.

The scary part? The model doesn't crash when this happens. It just quietly becomes wrong. A crashed service is obvious — someone calls you. A model that degrades from 95% accuracy to 75% accuracy over six months? Nobody notices until business metrics start tanking.

So MLOps exists to solve that. You need:
- **Monitoring** to detect drift and accuracy drops early
- **Automated retraining pipelines** to refresh the model on new data
- **Versioning** so you can roll back if a new model is worse
- **Infrastructure as code** so all of this is reproducible and auditable

Without all of this, you're essentially flying blind. A model in production without MLOps is a liability, not an asset."

---

## Q3. What was the model accuracy degradation problem and how did you solve it?

**Answer:**

"When I came onto the project, the model was deployed but there was no retraining pipeline. It was trained once on historical data and then left running. Over time — we're talking months — the model's accuracy had degraded by about **18%**. That's significant. For a churn model, that means we were either failing to flag customers who were about to leave, or worse, flagging customers who weren't at risk and wasting retention resources on them.

The root cause was clear: the model had no mechanism to learn from new data.

My solution was to build an **automated retraining pipeline using Apache Airflow**. The pipeline does the following on a scheduled basis:

1. Pulls fresh customer data from the data warehouse
2. Preprocesses and validates the data (checks for schema drift, null rates, etc.)
3. Retrains the model using the updated dataset
4. Evaluates the new model against a holdout test set
5. If the new model meets a minimum accuracy threshold, it replaces the old one in production
6. If it doesn't, the pipeline raises an alert and the old model stays live

After implementing this, we reduced the accuracy degradation from **18% to about 5%** — a **72% improvement** in model freshness. The key insight was treating model retraining the same way you'd treat a software release — automated, validated, with rollback capability."

---

## Q4. How did Prometheus scrape metrics from ECS Fargate workloads? What's the challenge there?

**Answer:**

"This is a genuinely tricky problem, and it's one of the more interesting technical challenges of the project.

The core issue with ECS Fargate is **dynamic IPs**. In a traditional setup, Prometheus uses a static config — you hardcode the IP addresses of your targets. But Fargate containers are ephemeral. Every time a task restarts, it gets a new private IP. You can't hardcode anything.

So you need **service discovery** — a way for Prometheus to dynamically discover what to scrape.

**My approach** was to use **AWS CloudWatch as a middle layer**. Here's the flow:

1. Each FastAPI container exposes a `/metrics` endpoint in Prometheus format using the `prometheus_client` Python library.
2. The application also ships custom metrics to **CloudWatch** — inference latency, prediction counts, error rates.
3. Prometheus then uses the **CloudWatch Exporter** (`prometheus/cloudwatch-exporter`) to pull those metrics from CloudWatch and expose them in Prometheus format.

This approach trades some real-time granularity (CloudWatch has a minimum 1-minute resolution) for reliability and simplicity. You don't have to fight Fargate's networking model.

An alternative I considered was using **AWS HTTP Service Discovery** — AWS exposes a REST endpoint that lists running ECS tasks with their IPs. Prometheus has native support for this via `ecs_sd_configs`. That gives you lower latency metrics but requires more network configuration — specifically, Prometheus needs to be in the same VPC and the security groups need to allow scraping traffic on the metrics port."

---

## Q5. What Grafana dashboards did you build and what did they show?

**Answer:**

"I built three main dashboards, each targeting a different audience and use case.

**Dashboard 1 — Model Health Overview** (for the data science team and product managers):
- **Prediction volume** over time — how many inferences per minute
- **Model accuracy** on a rolling window — using labeled feedback data where available
- **Prediction distribution** — what percentage of predictions are 'will churn' vs 'won't churn' (a sudden shift here is an early drift signal)
- **Retraining pipeline status** — last run time, success/failure, model version in production

**Dashboard 2 — API Performance** (for the engineering team):
- **P50, P95, P99 inference latency** — the 95th percentile is the most important; it shows what your slowest users are experiencing
- **Request error rate** — 4xx vs 5xx broken out
- **Requests per second** — to correlate with latency spikes
- **HTTP status code distribution**

**Dashboard 3 — Infrastructure Health** (for ops):
- **ECS container CPU and memory utilization**
- **Container restart counts** — a spike here means instability
- **CloudWatch Alarm states** — green/red at a glance

The business impact was concrete: before the dashboards, detecting an inference issue meant someone had to manually dig through CloudWatch logs — which might take 30–45 minutes. With the dashboards and alert rules, we were detecting and triaging incidents **3x faster**."

---

## Q6. What does "tuned alert thresholds" mean on your resume and how did you decide what the thresholds should be?

**Answer:**

"Good question — 'tuned alert thresholds' sounds vague but it represents a real engineering discipline.

When you first set up monitoring, the temptation is to alert on everything — any spike, any anomaly. The problem is **alert fatigue**. If your team gets 50 alerts a day, they start ignoring all of them. And then when a real incident happens, it gets buried. Alert fatigue is one of the most dangerous failure modes in on-call culture.

On the other end, if your thresholds are too loose, real problems slip through undetected.

**My process for tuning thresholds:**

1. **Establish a baseline first.** I ran the system for two weeks without any alerts firing on action, just observing. I captured the normal distribution of latency, error rate, CPU — what does 'healthy' look like?

2. **Calculate statistical bounds.** For each metric, I calculated the mean and standard deviation over the baseline period. I set alert thresholds at roughly **mean + 2 standard deviations** for a first warning, and **mean + 3 standard deviations** for a critical alert.

3. **Add business context.** Pure statistics aren't enough. For example, we knew our SLA required P95 latency under 500ms. So regardless of what 'normal' looked like, 500ms was a hard ceiling for a warning, and 800ms triggered a page.

4. **Iterate in production.** I reviewed false positive rates weekly for the first month and adjusted. Some thresholds were too sensitive during batch processing windows and needed time-of-day awareness.

The result was an alert system that the team actually trusted — which is the whole point."

---

## Q7. What is Terraform and why did you use it instead of clicking through the AWS console?

**Answer:**

"Terraform is an **Infrastructure as Code** tool. Instead of clicking through the AWS console to create resources, you write configuration files — `.tf` files — that describe exactly what your infrastructure should look like. Then you run `terraform apply` and Terraform makes it so.

For this project, I used Terraform to provision:
- The **ECS Fargate cluster** and task definitions
- **IAM roles and policies** for the containers and CI/CD pipeline
- **CloudWatch log groups** and metric alarms
- **VPC, subnets, and security groups**
- **ECR repositories** for the Docker images

**Why Terraform over the console?**

- **Reproducibility:** If I need to spin up a staging environment that mirrors production exactly, I run the same Terraform config against a different AWS account. With console clicks, that's hours of work and you'll inevitably miss something.
- **Version control:** All infrastructure changes go through Git. You get a full history of who changed what and why. You can review infrastructure changes in pull requests the same way you review code.
- **No manual mistakes:** Console clicking is error-prone — wrong region, wrong permission, missed checkbox. Terraform is declarative and deterministic.
- **Disaster recovery:** If production goes down, you can rebuild the entire stack from scratch with a single command.

The specific pain point that motivated this: we had an IAM misconfiguration that was blocking ECS task startup. Because I had it all in Terraform, I could diff the current state against what it should be, identify the gap in 10 minutes, and fix it with a pull request. Without IaC, that's a multi-hour manual investigation."

---

## Q8. What is FastAPI and what role did it play in your project?

**Answer:**

"FastAPI is a modern Python web framework for building APIs. It's particularly popular in ML deployments because it's fast, has automatic OpenAPI documentation, and has excellent support for async operations and data validation via Pydantic.

In my project, FastAPI served as the **serving layer** for the machine learning model — the interface between the outside world and the model.

Here's the request flow:

```
Client Request → FastAPI → Feature Preprocessing → ML Model → Response
```

Concretely, the FastAPI application:

1. **Receives prediction requests** — a JSON payload with customer features (tenure, monthly charges, contract type, etc.)
2. **Validates the input** using Pydantic models — if required fields are missing or malformed, it returns a 422 immediately, before touching the model
3. **Preprocesses features** — same transformations that were applied during training (scaling, encoding)
4. **Calls the model** — loads the trained scikit-learn model from disk/S3 and calls `.predict_proba()`
5. **Returns the prediction** — a JSON response with the churn probability and a binary classification
6. **Emits metrics** — every request updates Prometheus counters for request count, latency, and error rate via the `/metrics` endpoint

I also added a `/health` endpoint for ECS health checks — if the model fails to load, the health check fails, ECS kills the task, and a fresh one starts up. That's your automatic self-healing behavior."

---

## Q9. If your ML model's accuracy suddenly drops from 95% to 70% in production, how do you detect and respond?

**Answer:**

"This is the incident response question, and having a clear mental model here matters a lot.

**Detection — how do we know?**
With the monitoring setup I built, this would surface through two mechanisms:
1. A **Grafana alert** fires because the rolling accuracy metric crossed the threshold (I had it set to alert at < 85%)
2. A **prediction distribution alert** — if the model suddenly starts predicting 80% churn when it historically predicts 15%, that's a red flag even before you have labels

**Triage — what's the root cause?**
The first question is: is this a **data problem** or a **model problem**?

- Check the **input data quality dashboard** — are null rates spiking? Has the schema of incoming features changed? A feature engineering bug upstream can cause this.
- Check **CloudWatch logs** for exceptions or warnings from the preprocessing pipeline
- Check if the **timing correlates with a data pipeline change** — did someone update the ETL?

If the data looks fine, it's likely **concept drift** — the real-world relationship between features and churn has changed.

**Response — what do we do?**

1. **Immediately:** Check if this warrants a rollback. We keep the previous model version tagged in S3/ECR. If the situation is severe, roll back in under 5 minutes — it's a single Terraform variable change and a deploy.
2. **Short-term:** Manually trigger the retraining pipeline with the most recent data. Monitor the new model's validation metrics before promoting it.
3. **Medium-term:** Investigate why the drift happened. Was it a seasonal pattern we didn't account for? A business event (pricing change, new competitor)?
4. **Long-term:** Add a **data drift detection step** to the pipeline (e.g., using Evidently AI) so we catch distribution shifts before they become accuracy drops.

The key philosophy: **never sacrifice production stability for a fix**. Rollback first, diagnose second."

---

## Q10. What would you do differently if you built this project again today?

**Answer:**

"Honestly, a few things come to mind — and I think reflecting on this kind of thing is important engineering maturity.

**1. Model versioning from day one.**
I added model versioning mid-project, and retrofitting it was painful. The cleaner approach is to use **MLflow** from the very beginning — every training run gets logged with its parameters, metrics, and artifacts. You get a model registry, experiment tracking, and reproducibility out of the box. Starting without it meant I had models named `model_v2_final_final.pkl` in S3, which is a real thing that happened.

**2. Terraform modules instead of flat configs.**
My initial Terraform was a flat file of resources. As the project grew, it became hard to read and impossible to reuse. I'd structure it as proper modules from the start — a `networking` module, an `ecs_service` module, a `monitoring` module. Much cleaner, and you can version modules independently.

**3. Centralized structured logging earlier.**
We were using CloudWatch Logs but with unstructured log messages. Searching for specific errors was painful. I'd set up **structured JSON logging** from the start — every log line has a `request_id`, `model_version`, `latency_ms`, etc. as fields. Then you can query them in CloudWatch Insights or ship them to a proper log aggregation system.

**4. A data validation step at pipeline ingestion.**
Rather than discovering data quality issues when model accuracy dropped, I'd add a **Great Expectations** validation step at the very beginning of the retraining DAG. Define expectations for each feature — value ranges, null rates, cardinality. Fail fast if incoming data is bad, before you waste compute retraining on garbage.

**5. Better secrets management from the start.**
I started with environment variables for secrets. I'd go straight to **AWS Secrets Manager** with automatic rotation. The environment variable approach works but it's a security audit finding waiting to happen.

The meta-lesson: I'd treat the MLOps infrastructure like a product, not an afterthought. Every decision you defer creates tech debt that costs 3x more to fix later."

---

## Quick Reference — Key Numbers to Remember

| Metric | Value |
|---|---|
| Accuracy degradation (before retraining pipeline) | 18% |
| Accuracy degradation (after retraining pipeline) | 5% |
| Improvement in degradation | ~72% |
| Incident detection speed improvement | 3x faster |
| P95 latency SLA | < 500ms |
| Alert warning threshold | Mean + 2σ |
| Alert critical threshold | Mean + 3σ |

---

## Tech Stack Cheat Sheet

| Component | Technology |
|---|---|
| ML Model Serving | FastAPI + scikit-learn |
| Containerization | Docker |
| Container Orchestration | AWS ECS Fargate |
| Infrastructure as Code | Terraform |
| Pipeline Orchestration | Apache Airflow |
| Metrics Collection | Prometheus + CloudWatch Exporter |
| Dashboards & Alerting | Grafana |
| Container Registry | AWS ECR |
| Model Storage | AWS S3 |
| Logging | AWS CloudWatch Logs |

---

*Remember: In an interview, the story matters as much as the facts. Lead with the problem, explain your reasoning, quantify the impact.*
