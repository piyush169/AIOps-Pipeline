import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, ArrayType
import json

# ============================================================
# AIOps Golden Dataset ETL Job
# 
# Reads: Kaggle CI/CD failures (45k rows) + LogChunks (797 rows)
# Outputs: golden_dataset.json to S3
#
# BEFORE RUNNING: Update the table names below to match
# exactly what your Glue Crawler created in aiops_raw_db.
# You can find them in: AWS Console → Glue → Databases → aiops_raw_db → Tables
# ============================================================

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# ----------------------------------------------------------
# STEP 1: Read both tables from Glue Data Catalog
# UPDATE THESE TABLE NAMES to match your crawler output!
# ----------------------------------------------------------
GLUE_DATABASE = "aiops_raw_db"
KAGGLE_TABLE = "kaggle"           # ← Change if your crawler named it differently
LOGCHUNKS_TABLE = "logchunks"     # ← Change if your crawler named it differently
OUTPUT_S3_PATH = "s3://aiops-pipeline-data/golden/"

kaggle_dyf = glueContext.create_dynamic_frame.from_catalog(
    database=GLUE_DATABASE, 
    table_name=KAGGLE_TABLE
)
logchunks_dyf = glueContext.create_dynamic_frame.from_catalog(
    database=GLUE_DATABASE, 
    table_name=LOGCHUNKS_TABLE
)

kaggle_df = kaggle_dyf.toDF()
logchunks_df = logchunks_dyf.toDF()

# ----------------------------------------------------------
# STEP 2: Process Kaggle — extract unique fault profiles
# ----------------------------------------------------------
# The Kaggle dataset has 45k rows but only 10 failure_types × 3 stages = 30 combos.
# We extract the distinct combinations with aggregated metadata.
kaggle_profiles = kaggle_df.groupBy("failure_type", "failure_stage", "severity") \
    .agg(
        F.count("*").alias("occurrence_count"),
        F.avg("cpu_usage_pct").alias("avg_cpu"),
        F.avg("memory_usage_mb").alias("avg_memory"),
        F.collect_set("ci_tool").alias("ci_tools"),
        F.collect_set("language").alias("languages")
    ) \
    .orderBy(F.desc("occurrence_count"))

# ----------------------------------------------------------
# STEP 3: Process LogChunks — extract real error keywords per category
# ----------------------------------------------------------
# Clean up the keywords and error_chunk columns
logchunks_clean = logchunks_df.select(
    F.col("language"),
    F.col("keywords"),
    F.col("error_chunk"),
    F.col("category")
).filter(F.col("error_chunk").isNotNull() & (F.col("error_chunk") != ""))

# Collect real error samples grouped by common keywords
# We'll grab a sample of real errors to attach to each fault category
logchunks_samples = logchunks_clean.select(
    F.col("keywords"),
    F.col("error_chunk"),
    F.col("language")
).limit(200).collect()

# Build a lookup of real error samples by keyword pattern
error_samples_by_keyword = {}
for row in logchunks_samples:
    kw = row["keywords"] if row["keywords"] else ""
    chunk = row["error_chunk"] if row["error_chunk"] else ""
    if chunk:
        error_samples_by_keyword[kw] = chunk[:300]

# ----------------------------------------------------------
# STEP 4: Define the mapping from failure_type → mutation config
# This is the core intelligence of the ETL
# ----------------------------------------------------------
FAULT_MAPPING = {
    "Dependency Error": {
        "target_files": ["package.json", "package-lock.json"],
        "mutation_prompt": "You are a Chaos Engineer. Mutate the Node.js codebase so that it fails during dependency installation. Examples: remove a critical dependency from package.json, add a non-existent package name, change a package version to an incompatible one, or corrupt package-lock.json. The mutation must cause 'npm install' to fail with a real-looking error.",
        "pipeline_stage_override": "build"
    },
    "Build Failure": {
        "target_files": ["Dockerfile", "src/index.js", "src/db.js"],
        "mutation_prompt": "You are a Chaos Engineer. Mutate the Node.js codebase so that it fails during the build or compilation stage. Examples: change the Dockerfile base image to a non-existent version, introduce a syntax error in a JS file that prevents parsing, remove a required module import, or break the COPY command in the Dockerfile. The mutation must cause either 'docker build' or 'node' to crash.",
        "pipeline_stage_override": "build"
    },
    "Test Failure": {
        "target_files": ["tests/app.test.js", "src/index.js"],
        "mutation_prompt": "You are a Chaos Engineer. Mutate the Node.js codebase so that one or more Jest unit tests fail. Examples: change an API route's response status code, modify the response body structure, alter validation logic so valid inputs are rejected, or change expected values in assertions. The mutation must cause 'npm test' to report FAIL with at least one broken test case.",
        "pipeline_stage_override": "test"
    },
    "Security Scan Failure": {
        "target_files": ["package.json", "src/db.js", "src/index.js", ".env"],
        "mutation_prompt": "You are a Chaos Engineer. Mutate the Node.js codebase so that it fails a security scan. Examples: hardcode a fake AWS access key (AKIA...) in a source file, downgrade a package to a version with known CVEs, add a dependency with critical vulnerabilities, or embed a database password directly in the code. The mutation must cause Trivy, Gitleaks, or npm audit to flag a HIGH or CRITICAL issue.",
        "pipeline_stage_override": "build"
    },
    "Configuration Error": {
        "target_files": ["docker-compose.yml", "Dockerfile", "src/db.js", "eslint.config.js"],
        "mutation_prompt": "You are a Chaos Engineer. Mutate the Node.js codebase so that it fails due to a configuration error. Examples: change the database port to an invalid number, remove a required environment variable reference, corrupt the docker-compose.yml syntax, break the eslint config, or change a service name so containers can't find each other. The mutation must cause a configuration-related crash.",
        "pipeline_stage_override": "build"
    },
    "Network Error": {
        "target_files": ["src/db.js", "docker-compose.yml"],
        "mutation_prompt": "You are a Chaos Engineer. Mutate the Node.js codebase so that it fails due to a network or connection error. Examples: change the database host to an unreachable address, set Redis URL to a wrong port, change the API port mapping in docker-compose so health checks fail, or add a connection timeout of 1ms. The mutation must cause a connection refused, timeout, or ECONNREFUSED error.",
        "pipeline_stage_override": "deploy"
    },
    "Permission Error": {
        "target_files": ["Dockerfile", "src/index.js", "docker-compose.yml"],
        "mutation_prompt": "You are a Chaos Engineer. Mutate the Node.js codebase so that it fails due to a permissions error. Examples: change file permissions in the Dockerfile using chmod 000, try to bind to port 80 without root, write to a read-only directory, or reference a file path that requires elevated privileges. The mutation must cause an EACCES or permission denied error.",
        "pipeline_stage_override": "deploy"
    },
    "Resource Exhaustion": {
        "target_files": ["src/index.js", "Dockerfile", "tests/app.test.js"],
        "mutation_prompt": "You are a Chaos Engineer. Mutate the Node.js codebase so that it fails due to resource exhaustion. Examples: add an infinite loop in a route handler, create a memory leak by pushing to an unbounded array, set the container memory limit extremely low in Dockerfile, or spawn thousands of concurrent requests in a test. The mutation must cause an out-of-memory, timeout, or heap overflow error.",
        "pipeline_stage_override": "test"
    },
    "Timeout": {
        "target_files": ["src/index.js", "src/db.js", "tests/app.test.js"],
        "mutation_prompt": "You are a Chaos Engineer. Mutate the Node.js codebase so that it fails due to a timeout. Examples: add a sleep/delay of 60 seconds inside a route handler, set Jest timeout to 1ms, make the database query hang by waiting for a lock, or add an await on a promise that never resolves. The mutation must cause a timeout error in either tests or the application.",
        "pipeline_stage_override": "test"
    },
    "Deployment Failure": {
        "target_files": ["Dockerfile", "docker-compose.yml", "src/index.js"],
        "mutation_prompt": "You are a Chaos Engineer. Mutate the Node.js codebase so that it fails during deployment. Examples: change the CMD in Dockerfile to run a non-existent script, remove the EXPOSE directive, break the health check endpoint so it returns 500, or make the app crash immediately on startup with an uncaught exception. The mutation must cause the container to fail to start or the health check to fail.",
        "pipeline_stage_override": "deploy"
    }
}

# ----------------------------------------------------------
# STEP 5: Build the Golden Dataset
# ----------------------------------------------------------
golden_rows = []
fault_id = 1

# Get real error samples list
sample_list = list(error_samples_by_keyword.values())
sample_idx = 0

for profile_row in kaggle_profiles.collect():
    failure_type = profile_row["failure_type"]
    failure_stage = profile_row["failure_stage"]
    severity = profile_row["severity"]
    occurrence_count = profile_row["occurrence_count"]
    
    if failure_type not in FAULT_MAPPING:
        continue
    
    mapping = FAULT_MAPPING[failure_type]
    
    # Attach a real error sample from LogChunks (round-robin)
    real_error = ""
    real_keywords = []
    if sample_list:
        real_error = sample_list[sample_idx % len(sample_list)]
        sample_idx += 1
    
    golden_rows.append({
        "fault_id": f"FAULT_{fault_id:04d}",
        "fault_category": failure_type,
        "pipeline_stage": failure_stage,
        "severity": severity,
        "occurrence_count": int(occurrence_count),
        "target_files": mapping["target_files"],
        "mutation_prompt": mapping["mutation_prompt"],
        "original_error_sample": real_error[:500],
        "source_dataset": "kaggle+logchunks"
    })
    fault_id += 1

# ----------------------------------------------------------
# STEP 6: Write the Golden Dataset to S3
# ----------------------------------------------------------
golden_df = spark.createDataFrame(golden_rows)

golden_df.coalesce(1).write \
    .mode("overwrite") \
    .json(OUTPUT_S3_PATH)

print(f"Golden Dataset written to {OUTPUT_S3_PATH}")
print(f"Total fault entries: {len(golden_rows)}")

job.commit()
