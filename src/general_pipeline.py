import logging
import os
import pandas as pd
import time
import torch
from huggingface_hub import login
from tqdm import tqdm
from transformers import pipeline

from utils import *

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# get pdfs
pdf_folder_path = "data/PDF"
pdf_files_path = [f for f in os.listdir(pdf_folder_path) if f.endswith('.pdf')]
out_folder = "out/"
# pdf_files = ["24EM03456.pdf"] #used for debug

#extract pdf text
pdf_texts = {}
for pdf_file in pdf_files_path:
    pdf_texts[os.path.splitext(pdf_file)[0]] = extract_with_pdfplumber(os.path.join(pdf_folder_path,pdf_file))

####################### Part to generate the prompt

# Load system prompts
with open("prompt/general_prompt_extraction.md", "r") as f:
    system_prompt_meta = f.read()

#######################

# Login to Hugging Face to enable the use of gemma 3
with open("login_huggingface.txt", "r") as f:
    token = f.read()
try:
    login(token) #token from huggingface.co necessary to use gemma3
    logger.info("login to hugging face done")
except Exception as e:
    logger.error(f"Failed to login to hugging face: {e}")

model_name = "google/gemma-3-4b-it"
model_name_shrt = "gemma3_4B" #used for output files

device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {device}")
try:
    pipe = pipeline(
        "text-generation", #or "image-text-to-text"
        model=model_name,
        torch_dtype=torch.bfloat16,
        device=device,
        #device_map="auto", #use "auto" to automatically use all available GPUs (but slows the code ??!!)
    )
    logger.info("pipeline initialized")
except Exception as e:
    logger.error(f"Failed to initialize pipeline: {e}")

metadata_data = []
# loop to process multiple pdfs
for pdf_number,text_pdf in tqdm(pdf_texts.items()):
    logger.info(f"Processing PDF: {pdf_number}")
    messages_meta = [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_prompt_meta}]
        },
        {
            "role": "user",
            "content": (
                [{"type": "text", "text": text_pdf}]
            )
        }
    ]

    # Run the inference
    start_time = time.time()
    output_meta = pipe(messages_meta, max_new_tokens=400)
    elapsed_time = time.time() - start_time
    logger.info(f"Pipeline inference time for metadata: {elapsed_time:.2f} seconds")

    # Process the output
    answer_meta = output_meta[0]["generated_text"][-1]["content"]
    cleaned_meta = extract_dict_from_string(answer_meta)
    if cleaned_meta is not None:
        metadata_data.append(cleaned_meta)
    else:
        logger.error(f"Failed to extract metadata from output for {pdf_number}, content: {answer_meta}")

#transform into DataFrame and save to excel
try:
    df_meta = pd.DataFrame(metadata_data)
    # Remove % from the '% cellules' column if it exists
    if '% de cellules' in df_meta.columns:
        df_meta['% de cellules'] = df_meta['% de cellules'].astype(str).str.replace('%', '', regex=False)
    df_meta.to_excel(f"{out_folder}metadata_{model_name_shrt}.xlsx", index=False)
    logger.info(f"Saved metadata to {out_folder}metadata_{model_name_shrt}.xlsx")
except Exception as e:
    logger.error(f"Failed to save output file: {e}")
