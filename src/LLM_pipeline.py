import json
import logging
import os
import pandas as pd
import torch
import time
from huggingface_hub import login
from pdf_parser import *
from transformers import pipeline
from tqdm import tqdm

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

#get pdfs
pdf_folder_path = "data/PDF"
pdf_files = [f for f in os.listdir(pdf_folder_path) if f.endswith('.pdf')]
# pdf_files = ["24EM03456.pdf"] #used for debug

#extract pdf text
pdf_texts = {}
for pdf_file in pdf_files:
    #could use langchain here to extract text from pdf and use Document object
    pdf_texts[os.path.splitext(pdf_file)[0]] = extract_with_pdfplumber(os.path.join(pdf_folder_path,pdf_file))

# Load system prompts
with open("prompt/system_prompt_metadata.md", "r") as f:
    system_prompt_meta = f.read()
with open("prompt/system_prompt_mutation.md", "r") as f:
    system_prompt_mut = f.read()

# Login to Hugging Face to enable the use of gemma 3
with open("login_huggingface.txt", "r") as f:
    token = f.read()
try:
    login(token) #token from huggingface.co necessary to use gemma3
    logger.info("login to hugging face done")
except Exception as e:
    logger.error(f"Failed to login to hugging face: {e}")

model_name = "google/gemma-3-4b-it"

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

time_meta_data = [] # to store processing times
time_mutation_data = [] # to store processing times
metadata_data = []
mutation_data = []
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

    messages_mut = [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_prompt_mut}]
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
    output_gemma_4B = pipe(messages_meta, max_new_tokens=250) #temperature=0
    elapsed_time = time.time() - start_time
    time_meta_data.append(elapsed_time)
    logger.info(f"Pipeline inference time for metadata: {elapsed_time:.2f} seconds")
    start_time = time.time()
    output_gemma_4B2 = pipe(messages_mut, max_new_tokens=550) #temperature=0
    elapsed_time = time.time() - start_time
    time_mutation_data.append(elapsed_time)
    logger.info(f"Pipeline inference time for mutations: {elapsed_time:.2f} seconds")

    # Process the output
    answer_meta = output_gemma_4B[0]["generated_text"][-1]["content"]
    cleaned_meta = answer_meta.replace("```json", "").replace("```", "").strip() #clean the answer
    try: #to handle when the answer is not a valid json
        data_meta = json.loads(cleaned_meta)
        metadata_data.append(data_meta)
        logger.debug(f"Metadata output: {data_meta}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON for {pdf_number}: {e} \nContent: {cleaned_meta}")

    answer_mut = output_gemma_4B2[0]["generated_text"][-1]["content"]
    cleaned_mut = answer_mut.replace("```json", "").replace("```", "").strip() #clean the answer
    try:
        data_mut = json.loads(cleaned_mut)
        mutation_data.append(data_mut)
        logger.debug(f"Mutation output: {data_mut}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON for {pdf_number}: {e} \nContent: {cleaned_mut}")

#transform into DataFrame and save to excel
try:
    df_meta = pd.DataFrame(metadata_data)
    # Remove % from the '% cellules' column if it exists
    if '% cellules' in df_meta.columns:
        df_meta['% cellules'] = df_meta['% cellules'].astype(str).str.replace('%', '', regex=False)
    df_meta.to_excel("out/metadata_gemma3_4B.xlsx", index=False)
    logger.info("Saved metadata to out/metadata_gemma3_4B.xlsx")

    # Flatten the mutation data
    flat_mutation_data = [item for sublist in mutation_data for item in sublist]
    df_mut = pd.DataFrame(flat_mutation_data)
    # Remove rows with any None values
    df_mut = df_mut.dropna()
    df_mut.to_excel("out/mutation_gemma3_4B.xlsx", index=False)
    logger.info("Saved mutation data to out/mutation_gemma3_4B.xlsx")
    
    # Save processing times
    df_times = pd.DataFrame({
        'PDF': pdf_files,
        'Time_Metadata': time_meta_data,
        'Time_Mutation': time_mutation_data
    })
    df_times.to_excel("out/times_gemma3_4B.xlsx", index=False)
    logger.info("Saved processing times to out/times_gemma3_4B.xlsx")
except Exception as e:
    logger.error(f"Failed to save output files: {e}")