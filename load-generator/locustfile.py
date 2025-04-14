from locust import HttpUser, task, between
import itertools

class ContainerUser(HttpUser):
    wait_time = between(0.1, 0.5)  # Simulate user wait between actions

    DATA = ["small", "medium", "large"]
    FILE = ["small.jpg", "medium.jpg", "large.jpg", "x_large.jpg", "input.jpg"]

    combinations = list(itertools.product(DATA, FILE))

    # testing directly with the webapp container (no LB involved)
    # @task
    # def hit_api_endpoint(self):
    #     with open("/home/pranaav/Desktop/cloud-assign-1/materials-assignment1/function/data/images/input.jpg", "rb") as image_file:
    #         files = {"image": image_file}
    #         self.client.post("/watermark", data={'watermark-size': 'large'}, files=files)

    @task
    def single_endpoint_test(self):
        # Loop through all combinations of DATA and FILE for the /route endpoint
        for data_value, file_value in self.combinations:
            data = {
                "data": data_value, 
                "file": f"{file_value}",
                "output": ""
            }
            self.client.post("/route", data=data)
