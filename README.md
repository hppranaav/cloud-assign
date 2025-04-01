# cloud-assign-1
This assignment deals with scaling a FaaS running on a container using a scaling controller service and a custom load balancer. The Load balancer has two routing protocols (round_robin and state_aware) and the scaling controller has two algorithms (regression and sliding window).

## Pre-requisites
### Building the webapp image
To build the FaaS image, you run the following command from the root folder of this repository
``` docker build -t webapp -f webapp/Dockerfile .```

### Load balancer

### Building the load balancer image

### Running the scaling controller

## Architecture
In our scenario, we have kept the load balancer and the scaling controller as seperate entities, with the load balancer running as a container on the same network as the webapp containers and the scaling controller running as a daemon.
The load balancer uses round robin in default but can be switched to use the state aware routing by sending a HTTP GET request to the ```/algo``` endpoint of the load balancer
The scaling controller service however would need to be restarted in order to switch the scaling algorithm

## Experiments
### Caliberations
### Benchmarking

## API Specification

### Load Balancer API

#### `GET /metrics`
- **Description**: Retrieves the current metrics from the load balancer.
- **Response**:
    - `200 OK`: Returns all present metrics for all containers running and the load balancer itself

#### `GET /algo`
- **Description**: Retrieves the current routing protocol used by the load balancer.
- **Response**:
    - `200 OK`: Returns the current routing protocol (`round_robin` or `state_aware`).

#### `POST /algo`
- **Description**: Updates the routing protocol of the load balancer.
- **Request Body**:
    ```json
    {
        "algorithm": "round_robin" | "state_aware"
    }
    ```
- **Response**:
    - `200 OK`: Confirms the routing protocol has been updated.
    - `400 Bad Request`: Invalid or missing `algorithm` parameter.

---

### Scaling Controller API

#### `POST /scale`
- **Description**: Manually triggers scaling of the webapp containers.
- **Request Body**:
    ```json
    {
        "action": "scale_up" | "scale_down",
        "count": <number_of_containers>
    }
    ```
- **Response**:
    - `200 OK`: Confirms the scaling action has been performed.
    - `400 Bad Request`: Invalid or missing parameters.

#### `GET /status`
- **Description**: Retrieves the current status of the scaling controller.
- **Response**:
    - `200 OK`: Returns the current scaling algorithm and container count.
    ```json
    {
        "algorithm": "regression" | "sliding_window",
        "container_count": <number_of_containers>
    }
    ```

#### `POST /algorithm`
- **Description**: Updates the scaling algorithm used by the scaling controller.
- **Request Body**:
    ```json
    {
        "algorithm": "regression" | "sliding_window"
    }
    ```
- **Response**:
    - `200 OK`: Confirms the scaling algorithm has been updated.
    - `400 Bad Request`: Invalid or missing `algorithm` parameter.
