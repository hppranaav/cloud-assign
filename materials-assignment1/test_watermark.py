#!/usr/bin/env python3

#
# test_watermark.py - example of calling the watermark FaaS
#
# Part of the material provided for assignment 1 of the Cloud
# Computing course at Leiden University.
#
# Copyright (C) 2025  Leiden University, The Netherlands
#

from pathlib import Path
import requests
from enum import Enum

from typing import Optional

class WatermarkSize(Enum):
    Small = "small"
    Medium = "medium"
    Large = "large"

# TODO: may need to change the IP address to point to the server hosting
# the function.
target_url = "http://127.0.0.1:8081/watermark"


def perform_watermark_request(image_file : Path, watermark_size : WatermarkSize, output_file : Optional[Path] = None) -> bool:
    filedict = {"image": image_file.open("rb")}

    r = requests.post(target_url, data={'watermark-size': watermark_size.value}, files=filedict)

    if r.status_code != 200:
        print("error:", r.text)
        return False

    if ("Content-Type" not in r.headers or
        r.headers["Content-Type"] != "image/jpg"):
        print("error: response does not contain JPG file")
        return False

    if output_file:
        with output_file.open("wb") as fh:
            fh.write(r.content)

    return True


# Example function call
# TODO: provide an input file yourself
perform_watermark_request(Path("input.jpg"), WatermarkSize.Large, Path("output.jpg"))
