import json
import os
import sys
from pathlib import Path

# --- 1. Explicitly point Spark workers to active Python executable ---
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

# --- 2. Windows only: Hadoop native helpers ---
if os.name == "nt":
    os.environ.setdefault("HADOOP_HOME", r"C:\hadoop")
    os.environ["PATH"] = os.path.join(os.environ["HADOOP_HOME"], "bin") + os.pathsep + os.environ["PATH"]

import pandas as pd
from pyspark.ml import PipelineModel
from pyspark.ml import classification as spark_classification
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.functions import vector_to_array
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from config import MODEL_PATH  # noqa: E402

# Must match the columns (and ORDER) the model was trained with

FEATURE_COLS = [
    "temperature_2m",
    "humidity_2m",
    "precipitation",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "soil_temperature_0_to_7cm",
    "soil_temperature_7_to_28cm",
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
]


# Created once and reused (starting Spark and loading the model are the slow parts)
_spark_session = None
_model = None


def get_spark_session() -> SparkSession:
    global _spark_session
    if _spark_session is None:
        _spark_session = (
            SparkSession.builder.appName("FireDetectionMLService")
            .config("spark.ui.enabled", "false")
            .config("spark.hadoop.io.native_io.enabled", "false")  # Bypass NativeIO check
            .config("spark.python.worker.reuse", "true")           # Reuse worker processes
            .config("spark.python.worker.timeout", "120")          # Prevent premature timeouts
            .getOrCreate()
        )
    return _spark_session


def load_spark_model(path):
    """Load a saved Spark model of any supported type, detected from its metadata:
    - PipelineModel
    - a single Spark MLlib classifier (e.g. RandomForestClassificationModel)
    - an XGBoost-on-Spark model (xgboost.spark.SparkXGBClassifierModel)
    """
    meta_files = list(Path(path, "metadata").glob("part-*"))
    if not meta_files:
        raise FileNotFoundError(f"No Spark model metadata found under: {path}")
    meta = json.loads(meta_files[0].read_text(encoding="utf-8"))
    module_path, _, class_name = meta["class"].rpartition(".")
    print(f"[Spark ML Service] Saved model type: {class_name} (saved with Spark {meta.get('sparkVersion')})")

    if class_name == "PipelineModel":
        return PipelineModel.load(str(path))

    if module_path.startswith("xgboost.spark"):
        try:
            import xgboost.spark as xgb_spark
        except ImportError as exc:
            raise ImportError(
                f"Could not import xgboost.spark ({exc}). "
                "XGBoost-on-Spark needs: pip install xgboost scikit-learn"
            ) from exc
        return getattr(xgb_spark, class_name).load(str(path))

    model_cls = getattr(spark_classification, class_name, None)
    if model_cls is None:
        raise ValueError(f"Unsupported saved model class: {meta['class']}")
    return model_cls.load(str(path))


def get_model():
    global _model
    if _model is None:
        print(f"[Spark ML Service] Loading model from: {MODEL_PATH}")
        _model = load_spark_model(MODEL_PATH)
        try:
            n = _model.numFeatures  # exposed by MLlib classifiers; not by every model type
        except Exception:
            n = None
        if n is not None and n != len(FEATURE_COLS):
            raise ValueError(f"Model expects {n} features but FEATURE_COLS has {len(FEATURE_COLS)}.")
    return _model


def predict_fire_risk(df_forecast_pandas: pd.DataFrame):
    if df_forecast_pandas is None or df_forecast_pandas.empty:
        print("[Spark ML Service] Empty forecast DataFrame passed. Skipping.")
        return None

    spark = get_spark_session()
    model = get_model()

    df_spark = spark.createDataFrame(df_forecast_pandas)
    df_spark = df_spark.fillna(0.0, subset=FEATURE_COLS)

    if isinstance(model, PipelineModel):
        # A full pipeline normally contains its own VectorAssembler
        df_input = df_spark
    else:
        df_input = VectorAssembler(inputCols=FEATURE_COLS, outputCol="features").transform(df_spark)

    predictions = model.transform(df_input)

    ts_col = F.to_timestamp(
        F.concat_ws(" ", F.col("target_date").cast("string"), F.col("target_time").cast("string")),
        "yyyy-MM-dd HH:mm",
    )
    # Native vector -> array: no slow Python UDF
    risk_score_col = (
        vector_to_array(F.col("probability"))[1]
        if "probability" in predictions.columns
        else F.lit(0.0)
    )

    output_cols = [
        F.col("region_id").cast("integer"),
    ]

    if "weather_id" in predictions.columns:
        output_cols.append(F.col("weather_id").cast("integer"))

    output_cols.extend([
        ts_col.alias("forecast_timestamp"),
        risk_score_col.cast("double").alias("fire_risk_score"),
        F.col("prediction").cast("double").alias("is_fire_predicted"),
        F.current_timestamp().alias("created_at"),
        F.current_timestamp().alias("updated_at"),
    ])

    output_df = predictions.select(*output_cols)

    output_df.cache()
    print(f"\n[Spark ML Service] Classification completed for {output_df.count()} forecast records:")
    output_df.show(10, truncate=False)
    return output_df