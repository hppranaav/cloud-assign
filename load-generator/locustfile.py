from locust import HttpUser, task, between

class ContainerUser(HttpUser):
    wait_time = between(0.1, 0.5)  # Simulate user wait between actions

    # @task
    # def hit_main_endpoint(self):
    #     self.client.get("/")  # Replace with your container's endpoint

    @task
    def hit_api_endpoint(self):
        with open("/home/pranaav/Desktop/cloud-assign-1/materials-assignment1/function/data/images/input.jpg", "rb") as image_file:
            files = {"image": image_file}
            self.client.post("/watermark", data={'watermark-size': 'large'}, files=files)
