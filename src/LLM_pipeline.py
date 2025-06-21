import json
import logging
import os
import pandas as pd
import torch
import time
from huggingface_hub import login
from pdf_parser import *
from transformers import pipeline

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

pdf_folder_path = "data/PDF"
# pdf_files = [f for f in os.listdir(pdf_folder_path) if f.endswith('.pdf')]
pdf_files = ["24EM03456.pdf"]

pdf_texts = {}
for pdf_file in pdf_files:
    #could use langchain here to extract text from pdf and use Document object
    pdf_texts[os.path.splitext(pdf_file)[0]] = {"text":extract_with_pdfplumber(os.path.join(pdf_folder_path,pdf_file))}

with open("prompt/system_prompt_metadata.md", "r") as f:
    system_prompt_meta = f.read()

with open("prompt/system_prompt_mutation.md", "r") as f:
    system_prompt_mut = f.read()

device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {device}")

with open("login.txt", "r") as f:
    token = f.read()
try:
    login(token) #token from huggingface.co necessary to use gemma3
    logger.info("login to hugging face done")
except Exception as e:
    logger.error(f"Failed to login to hugging face: {e}")

model_name = "google/gemma-3-4b-it"

try:
    pipe = pipeline(
        "text-generation", #"image-text-to-text"
        model=model_name,
        torch_dtype=torch.bfloat16,
        device=device, #uses "cpu" here because the "cuda" requires 3 Go more of VRAM (5GO total)
    )
    logger.info("pipeline initialized")
except Exception as e:
    logger.error(f"Failed to initialize pipeline: {e}")

#add a for loop to process multiple pdfs #TODO
messages_meta = [
    {
        "role": "system",
        "content": [{"type": "text", "text": system_prompt_meta}]
    },
    {
        "role": "user",
        "content": (
            [{"type": "text", "text": pdf_texts["24EM03456"]["text"]}]
            #+ [{"type": "image", "image": img} for img in pdf_text_image["24EM03352"]["image"]]
        )
    }
]

messages_mut = [
    {
        "role": "system",
        "content": [{"type": "text", "text": system_prompt_mut}]
    },
    {
        "role": "user",
        "content": (
            [{"type": "text", "text": pdf_texts["24EM03456"]["text"]}]
        )
    }
]


start_time = time.time()
output_gemma_4B = pipe(messages_meta, max_new_tokens=250) #temperature=0
elapsed_time = time.time() - start_time
logger.info(f"Pipeline inference time: {elapsed_time:.2f} seconds")
start_time = time.time()
output_gemma_4B2 = pipe(messages_mut, max_new_tokens=250) #temperature=0
elapsed_time = time.time() - start_time
logger.info(f"Pipeline inference time: {elapsed_time:.2f} seconds")

answer_meta = output_gemma_4B[0]["generated_text"][-1]["content"]
cleaned_meta = answer_meta.replace("```json", "").replace("```", "").strip() #clean the answer
data = json.loads(cleaned_meta)
logger.info(f"Metadata output: {data}")

answer_mut = output_gemma_4B2[0]["generated_text"][-1]["content"]
cleaned_mut = answer_mut.replace("```json", "").replace("```", "").strip() #clean the answer
data2 = json.loads(cleaned_mut)
logger.info(f"Mutation output: {data2}")

try:
    df = pd.DataFrame([data])
    df.to_excel("out/metadata_gemma3_4B.xlsx", index=False)
    logger.info("Saved metadata to out/metadata_gemma3_4B.xlsx")
    df2 = pd.DataFrame(data2)
    df2.to_excel("out/mutation_gemma3_4B.xlsx", index=False)
    logger.info("Saved mutation data to out/mutation_gemma3_4B.xlsx")
except Exception as e:
    logger.error(f"Failed to save output files: {e}")