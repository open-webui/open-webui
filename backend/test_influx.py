from influxdb_client import InfluxDBClient
import os
print("Testing InfluxDB connection...")
client = InfluxDBClient(url=os.getenv("INFLUXDB_URL"), 
  token=os.getenv("INFLUXDB_TOKEN"), org=os.getenv("INFLUXDB_ORG"))
health = client.health()
print(f"✅ InfluxDB Health: {health.status}")
client.close()
