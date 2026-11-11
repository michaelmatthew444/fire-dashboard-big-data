import os
from pathlib import Path
import datetime

# API Key
NASA_FIRMS_MAP_KEY = "8560b8f49dcf044f593a2e476e3ad28b"

# Server
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC_NAME = "nasa-firms-hotspots"

# Testing
TEST_LATITUDE = -6.200000
TEST_LONGITUDE = 106.816666

TEST_DATE = datetime.datetime(2023, 1, 1)  # Set to a specific date for testing

TESTING_MODE = True  # Set to False for production mode


# Fectching Interval
FIRMS_POLL_INTERVAL = 10 if TESTING_MODE else 300  # Poll every 10 seconds in testing, every 5 minute in production
METEO_POLL_INTERVAL = 10 if TESTING_MODE else 3600  # Poll every 10 seconds in testing, every hour in production


# Area

INDONESIA_BBOX = "94.0000,-11.0000,141.0000,6.0000"
KALIMANTAN_BBOX = "108.5000,-4.5000,119.0000,4.5000"
CURR_BBOX = KALIMANTAN_BBOX  # Current bounding box for fetching data

# Database

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "fire_forest_db")
DB_USER = os.getenv("DB_USER", "matthew")
DB_PASSWORD = os.getenv("DB_PASSWORD", "fire1234")

DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


DB_JDBC_URL = f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"
DB_JDBC_PROPERTIES = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "driver": "org.postgresql.Driver"
}

# Saved Spark ML model path
ROOT_DIR = Path(__file__).resolve().parent
MODEL_PATH = str(ROOT_DIR / "data" / "saved_model" / "fire_predictor_spark_v1")