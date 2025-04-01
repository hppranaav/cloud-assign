# Web application for assignment 1

This is the Web application to deploy and scale for assignment 1 of the
Cloud Computing course at Leiden University. The Web application is in fact
a FaaS function that will apply a watermark to a provided image. The
function uses Google's functions framework.

After installing the requirements using pip (see requirements.txt), the
function can be started from the directory `function` with the command:

    functions-framework --target=watermark

You can add a `--debug` option if needed for debugging purposes.

Watermark images in three sizes are provided as part of this materials
packages in the directory `data/watermarks/`. As discussed in the assignment
text, these watermarks must be made available to the function running in a
container through a volume.

The file `test_watermark.py` is a working example of how the call the FaaS
function. You need to bring your own input file (and modify the filename in
the test program).


## References

The functions framework that we use is downloaded from PyPi but also
available through:

<https://github.com/GoogleCloudPlatform/functions-framework-python>

Sources watermark images:
- small.png: Leiden University Logo.
- medium.png and large.png were sourced from OpenClipboard.

