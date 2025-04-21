import pandas as pd
import matplotlib.pyplot as plt

# Example of reading Locust CSV results
data_single = pd.read_csv("single_container_50_users_stats.csv")
data_multi = pd.read_csv("multi_container_2_containers_stats.csv")

# Plot example: Average response time
plt.figure(figsize=(10, 6))
plt.plot(data_single['Timestamp'], data_single['Average Response Time'], label='Single Container')
plt.plot(data_multi['Timestamp'], data_multi['Average Response Time'], label='Two Containers')
plt.xlabel("Time")
plt.ylabel("Average Response Time (ms)")
plt.title("Latency Comparison: Single vs Two Containers")
plt.legend()
plt.grid(True)
plt.savefig("latency_comparison.png")
plt.show()
