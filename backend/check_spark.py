"""Checks that Spark can read/write local files on Windows (the call that failed for you).
Usage:  python check_spark.py [path/to/saved_model]
"""
import os
import sys
import tempfile
from pathlib import Path

from pyspark.sql import SparkSession

print("HADOOP_HOME =", os.environ.get("HADOOP_HOME"))

spark = (SparkSession.builder.master("local[1]").appName("check_spark")
         .config("spark.ui.enabled", "false").getOrCreate())

# 1. Write then read a small dataset: exercises the same local-file listing code that failed
tmp = Path(tempfile.mkdtemp()) / "check_parquet"
spark.range(5).write.mode("overwrite").parquet(str(tmp))
count = spark.read.parquet(str(tmp)).count()
assert count == 5, f"expected 5 rows, got {count}"
print("[OK] Spark can write and read local files.")

# 2. Optionally load your actual saved ML model
if len(sys.argv) > 1:
    from pyspark.ml import PipelineModel
    model = PipelineModel.load(sys.argv[1])
    print("[OK] Model loaded. Stages:", [type(s).__name__ for s in model.stages])

spark.stop()
