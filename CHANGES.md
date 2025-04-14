- make use of ```:z``` on the volume mount in Red Hat environments.

- Average CPU usage of webapp container hovers aroound 0.05%

- Images sizes to be tested
    - [small.jpg](https://unsplash.com/photos/brown-2-door-window-gCuSEdv7W7w) - 640 x 960 (61.3KB)
    - [medium.jpg](https://unsplash.com/photos/the-northern-lights-dance-across-the-night-sky-z20CpvTLaZk) - 1920 x 1281 (412KB)
    - [large.jpg](https://unsplash.com/photos/an-elephant-stands-in-the-african-savanna-hcBVdd2leJs) - 2400 x 1600 (684.7KB)
    - [x_large.jpg](https://unsplash.com/photos/a-van-and-a-dog-sit-by-the-sea-hvnqLm01za4) - 7430 x 4953 (14.4MB)

- I have added a scaling-controller code, but it only contains code to retrieve metrics and container information from the host podman. There is a hardcoded value in `load_balancer.py` which points to the gateway of the host (required as using localhost within the containers will point to the container itself)
- Changed the above to dynamically pull gateway ip from the host on launch 