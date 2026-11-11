# test_line_graph.py
import logging
from database import SessionLocal
from services.data_service import DataService

logging.basicConfig(level=logging.INFO)

def run_test():
    session = SessionLocal()
    try:
        service = DataService(session)

        print("\n--- Fetching Line Graph Data for Today (Region 1) ---")
        graph_res = service.get_today_line_graph(region_id=1)
        
        print(f"Region ID  : {graph_res['region_id']}")
        print(f"Target Date: {graph_res['target_date']}")
        print(f"Total Hours: {graph_res['total_hours']}")
        print("-" * 50)

        for hour in graph_res["hourly_data"]:  # Print first 5 hours
            print(
                f"Time: {hour['target_time']:<5} | "
                f"Temp: {hour['temperature_2m']}°C | "
                f"Humidity: {hour['humidity_2m']}% | "
                f"Wind: {hour['wind_speed_10m']} km/h"
            )

    finally:
        session.close()

if __name__ == "__main__":
    run_test()