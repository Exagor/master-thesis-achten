ARG CUDA="12.6"
ARG CUDNN="9"
ARG PYTORCH="2.7.1"

# Use a minimal base Python image
# FROM python:3.10-slim

# use PyTorch base image with specified versions
FROM pytorch/pytorch:${PYTORCH}-cuda${CUDA}-cudnn${CUDNN}-devel

# Set working directory
WORKDIR /app

# Copy dependencies file first (for layer caching)
COPY requirements.txt .

# Install Python dependencies (poppler-utils is required for PDF processing)
RUN apt-get update && apt-get install -y poppler-utils
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Run the pre-download script to already download the model weights
RUN python src/pre_download.py

# Default command to run the pipeline
CMD ["python", "src/LLM_pipeline.py"]
# CMD ["python", "src/evaluate_prompt.py"]
#CMD ["python", "src/generate_prompt.py"]
# CMD ["python", "src/LM_pipeline.py"]