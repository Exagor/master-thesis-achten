# Medical document understanding and information extraction

By Alexandre Achten - Master Thesis - 2024-2025

## Introduction

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

## Installation of models

And to use the LayoutXLM model, you need to install the following package:

```bash
python3 -m pip install 'git+https://github.com/facebookresearch/detectron2.git'
python3 -m pip install torchvision tesseract
```

If you have problems installing detectron2, go check this [link](https://detectron2.readthedocs.io/en/latest/tutorials/install.html).
If you have problems installing tesseract, go check this [link](https://github.com/tesseract-ocr/tesseract).

## Data

The data exploited here are medical protocols from various belgians hospitals in the oncology departement. The data are in french and are in the form of a pdf file.

## Docker

### Build the Docker images from the current directory and give them a tag

```bash
docker build -t llm-pipeline .
```

### Commands to run the Docker containers

The first command runs the container without GPU support, while the second command runs it with GPU support if available. Both commands mount the current directory's `out` folder to the container's `/app/out` directory, where the output files will be saved.

```bash
docker run --rm -v $(pwd)/out:/app/out llm-pipeline
```
or
```bash
docker run --gpus all -v $(pwd)/out:/app/out llm-pipeline
```
## HuggingFace

Don't forget to use a login token from the HuggingFace website to access the models. The token is set in the ``login_huggingface.txt`` file.