import logging
import os
import pandas as pd
import time
import torch
from huggingface_hub import login
from tqdm import tqdm
from transformers import pipeline

from hallucination_checker import *
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
pdf_image = {} # used for images in pdfs, not used here
for pdf_file in pdf_files_path:
    pdf_texts[os.path.splitext(pdf_file)[0]] = extract_with_pdfplumber(os.path.join(pdf_folder_path,pdf_file))
    pdf_image[os.path.splitext(pdf_file)[0]] = extract_pdf2image(os.path.join(pdf_folder_path,pdf_file))

# Load system prompts
with open("prompt/final_prompt_metadata_final.md", "r") as f:
    system_prompt_meta = f.read()
with open("prompt/final_prompt_mutation_final.md", "r") as f:
    system_prompt_mut = f.read()

# Login to Hugging Face to enable the use of gemma 3
with open("login_huggingface.txt", "r") as f:
    token = f.read()
    token = token.strip() #to remove any leading/trailing whitespace
try:
    login(token) #token from huggingface.co necessary to use gemma3
    logger.info("login to hugging face done")
except Exception as e:
    logger.error(f"Failed to login to hugging face: {e}")

model_name = "google/gemma-3-27b-it"
model_name_shrt = "gemma3_27B" #used for output files

device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {device}")
try:
    pipe = pipeline(
        "text-generation", #"text-generation" or "image-text-to-text"
        model=model_name,
        torch_dtype=torch.bfloat16,
        device=device,
        model_kwargs={"attn_implementation": "eager"},
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
                #+ [{"type": "image", "image": img} for img in pdf_image[pdf_number]]
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
                #+ [{"type": "image", "image": img} for img in pdf_image[pdf_number]]
            )
        }
    ]

    # Run the inference
    start_time = time.time()
    output_meta = pipe(messages_meta, max_new_tokens=250) # if in image-text-to-text mode, must precise text= parameter
    elapsed_time = time.time() - start_time
    time_meta_data.append(elapsed_time)
    logger.info(f"Pipeline inference time for metadata: {elapsed_time:.2f} seconds")

    start_time = time.time()
    output_mut = pipe(messages_mut, max_new_tokens=650)
    elapsed_time = time.time() - start_time
    time_mutation_data.append(elapsed_time)
    logger.info(f"Pipeline inference time for mutations: {elapsed_time:.2f} seconds")

    # Process the output
    answer_meta = output_meta[0]["generated_text"][-1]["content"]
    cleaned_meta = extract_dict_from_string(answer_meta)
    if cleaned_meta is not None:
        metadata_data.append(cleaned_meta)
    else:
        logger.error(f"Failed to extract metadata from output for {pdf_number}, content: {answer_meta}")

    answer_mut = output_mut[0]["generated_text"][-1]["content"]
    cleaned_mut = extract_list_of_dicts_from_string(answer_mut)
    if cleaned_mut is not None:
        mutation_data.append(cleaned_mut)
    else:
        logger.error(f"Failed to extract mutation data from output for {pdf_number}, content: {answer_mut}")

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

try:
    # Flatten the mutation data
    flat_mutation_data = [item for sublist in mutation_data for item in sublist]
    df_mut = pd.DataFrame(flat_mutation_data)
    # Remove rows with any None values
    df_mut = df_mut.dropna()
    if "% d'ADN muté" in df_mut.columns:
        df_mut["% d'ADN muté"] = df_mut["% d'ADN muté"].astype(str).str.replace('%', '', regex=False)
    df_mut.to_excel(f"{out_folder}mutation_{model_name_shrt}.xlsx", index=False)
    logger.info(f"Saved mutation data to {out_folder}mutation_{model_name_shrt}.xlsx")
except Exception as e:
    logger.error(f"Failed to save output file: {e}")

try:
    # Save processing times
    df_times = pd.DataFrame({
        'PDF': pdf_files_path,
        'Time_Metadata': time_meta_data,
        'Time_Mutation': time_mutation_data
    })
    df_times.to_excel(f"{out_folder}times_{model_name_shrt}.xlsx", index=False)
    logger.info(f"Saved processing times to {out_folder}times_{model_name_shrt}.xlsx")
except Exception as e:
    logger.error(f"Failed to save output file: {e}")

#check for hallucination
try:
    logger.info("Checking for hallucination(s)")
    hallucination_report = check_hallucination(pdf_folder_path,
                                               f"{out_folder}metadata_{model_name_shrt}.xlsx",
                                               f"{out_folder}mutation_{model_name_shrt}.xlsx",
                                               f"{out_folder}hallucination_report_{model_name_shrt}.xlsx")
    logger.info("Hallucination report :")
    print(hallucination_report)
except Exception as e:
    logger.error(f"Failed to check hallucination(s): {e}")
