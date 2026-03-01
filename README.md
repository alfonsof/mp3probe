# MP3Probe utility in Python

This repo contains an MP3Probe utility in Python code.

This utility extracts information from an MP3 file, including:

* MPEG audio
* ID3 v1 tag
* ID3 v2 tag
* Embedded Lyrics
* Embedded Album Art

It can also read information from AAC and FLAC files.

## Requirements

* You must have the following installed:
  * Python 3
  * ffprobe application (part of FFmpeg)

* The code was written for:
  * Python 3

## Use a Virtual Environment

A Python environment is a self-contained directory that includes a specific version of Python and a set of installed packages. It is recommended using Python virtual environments for each project.

1. Create a virtual environment

  Open your terminal and run:

  ```bash
  python -m venv .venv
  ```

  This creates a folder named `.venv` containing the environment.

2. Activate the environment

 On Windows:

 ```bash
.venv\Scripts\activate
 ```

 On macOS/Linux:

 ```bash
 source .venv/bin/activate
 ```

 Once activated, your terminal will show the environment name, like this:

 ```bash
 (.venv) $
 ```

3. Install packages inside the environment

 Now you can install packages without affecting your global Python setup:

 ```bash
pip install example
 ```

4. Deactivate the environment

 When you're done, simply run:

 ```bash
 deactivate
 ```

## Install library packages

The application uses only Python standard libraries. No external packages are required to run the script.

## Using the utility

* This utility reads information from MP3 files.

* Run the utility from the command line:

  ```bash
  python mp3probe.py <file_name>
  ```
  
* You will get the following information:

  * MPEG audio
  * ID3 v1 tag
  * ID3 v2 tag
  * Embedded Lyrics
  * Embedded Album Art

## Running Tests

This project includes unit tests to verify the functionality of the script. The tests use the standard `unittest` library and `unittest.mock` to simulate `ffprobe` output, so no external files or FFmpeg installation are required to run them.

To run the tests:

```bash
python test_mp3probe.py
```

Or if you want more details about the exit:

```bash
python test_mp3probe.py -v
```

## License

This code is released under the MIT License. See LICENSE file.