#!/usr/bin/env python3

#
# main.py - a simple watermark function hosted through FaaS using the
# function framework from Google Cloud Platform.
#
# Part of the material provided for assignment 1 of the Cloud
# Computing course at Leiden University.
#
# Copyright (C)  2025  Leiden University, The Netherlands.
#

import io
import flask
import werkzeug
import functions_framework

import PIL.Image as Image
from PIL import UnidentifiedImageError

from typing import Dict

# Available watermarks
# (we expect the data directory is mounted into the container through the
# volume feature).
watermark_files = {
  "small": "data/watermarks/small.png",
  "medium": "data/watermarks/medium.png",
  "large": "data/watermarks/large.png"
}

watermark_images: Dict[str, Image.Image] = {}

# Function arguments
WATERMARK_SIZE = "watermark-size"
IMAGE = "image"


@functions_framework.http
def watermark(request: flask.Request) -> flask.typing.ResponseReturnValue:
    # Validate request
    if WATERMARK_SIZE not in request.form:
        flask.abort(400, "watermark-size missing in request")

    watermark_size = request.form[WATERMARK_SIZE]
    if watermark_size not in watermark_files.keys():
        flask.abort(400, "invalid watermark size '{}'".format(watermark_size))

    files = request.files.to_dict()
    if not IMAGE in files:
        flask.abort(400, "image missing in request")

    # Generate the watermark
    buf = perform_watermark(files[IMAGE], watermark_images[watermark_size])

    # Return generated file in response
    response = flask.make_response(flask.send_file(buf,mimetype='image/jpg'))
    return response


def perform_watermark(image_file: werkzeug.datastructures.FileStorage, watermark: Image.Image) -> io.BytesIO:
    image = Image.open(image_file).convert("RGBA")

    # Paste watermark on image-sized later in upper-left corner
    watermark_layer = Image.new("RGBA", image.size)
    watermark_layer.paste(watermark, (watermark.width // 10, watermark.height // 10))

    # Composite the layers
    watermarked_image = Image.alpha_composite(image, watermark_layer)

    # Save image to a binary stream that can be returned to the client.
    buf = io.BytesIO()
    watermarked_image.convert("RGB").save(buf, format='JPEG')
    buf.seek(0)
    return buf


def preload_images():
    '''Preload the watermark images so that we do not have to open and
    decompress the watermark each time the FaaS function is invoked.'''
    for size, path in watermark_files.items():
        watermark_images[size] = Image.open(path).convert("RGBA")


# Run upon module import
preload_images()
