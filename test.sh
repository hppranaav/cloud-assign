#!/bin/bash

# Define the form fields and file
FIELD1="small"
OUTPUT_FILE_PATH="output.jpg"
FILE_PATH="input.jpg"

# Make the curl request and store the response in the output file
curl -X POST -F "data=$FIELD1" -F "file=$FILE_PATH" -F "output=$OUTPUT_FILE_PATH" -o "./output.jpg" http://0.0.0.0:8100/route