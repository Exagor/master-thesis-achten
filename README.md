# Exploring Language Models and Prompt Engineering for Information Extraction of French Medical Documents

By Alexandre Achten - Master Thesis - 2024-2025

## Introduction

This work aims to extract information from medical documents, specifically oncology reports, using Large Language Models (LLMs). The goal is to create a pipeline that can process these documents and extract relevant information such as metadata, mutations, and other key details.

## Data

The data exploited here are medical protocols from various belgians hospitals in the oncology departement. The data are in french and are in the form of a pdf file.

## Installation of packages

To install the required packages, run the following command:

```bash
pip install -r requirements.txt
```

Carefull, that pdfplumber requires `pdfminer-six 20231228` and camelot requires `pdfminer.six-20240706`. So you need to choose which one to use.
You can choose using this command :

```bash
pip install pdfplumber pdfminer.six==20231228
```

or

```bash
pip install camelot-py pdfminer.six==20240706
```

## Usage

Put you pdf files in the `data` folder (can be modified in the `src/LLM_pipeline.py` file). The pdf files should be named with their exam number, for example `24EM03308.pdf`. Then run the docker container or run the LLM_pipeline.py file. If you need help on how to create and run docker containers, please read the Docker section of this README. The output files will be saved in the `out` folder (can be modified in the `src/LLM_pipeline.py` file).

## Docker

### Build the Docker images

Build the Docker image using the Dockerfile provided in the repository. This command will create a Docker image named `llm-pipeline`

```bash
docker build -t llm-pipeline .
```

### Run the Docker containers

The first command runs the container without GPU support, while the second command runs it with GPU support if available. Both commands mount the current directory's `out` folder to the container's `/app/out` directory, where the output files will be saved. Add the `-d` flag to run the container in detached mode if you want it to run in the background.

```bash
docker run --rm -v $(pwd)/out:/app/out llm-pipeline
```

or

```bash
docker run --gpus all -v $(pwd)/out:/app/out llm-pipeline
```

## HuggingFace

Don't forget to use a login token from the HuggingFace website to access the models. The token is set in the ``login_huggingface.txt`` file.