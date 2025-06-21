from pdf_parser import *
import os
import torch
from huggingface_hub import login
from transformers import pipeline
#save the output in json format
import json
import pandas as pd

pdf_folder_path = "data/PDF"
# pdf_files = [f for f in os.listdir(pdf_folder_path) if f.endswith('.pdf')]
pdf_files = ["24EM03456.pdf"]
image_save_folder_path = "data/images"

pdf_text_image = {}
for pdf_file in pdf_files:
    #could use langchain here to extract text from pdf and use Document object
    pdf_text_image[os.path.splitext(pdf_file)[0]] = {"text":extract_with_pdfplumber(os.path.join(pdf_folder_path,pdf_file))}
    pdf_images = extract_pdf2image(f"{pdf_folder_path}/{pdf_file}")
    pdf_text_image[os.path.splitext(pdf_file)[0]]["image"] = pdf_images

print(pdf_text_image.keys())
print(pdf_text_image)

with open("prompt/system_prompt_metadata.md", "r") as f:
    system_prompt_meta = f.read()
print(system_prompt_meta)

with open("prompt/system_prompt_mutation.md", "r") as f:
    system_prompt_mut = f.read()
print(system_prompt_mut)

device = "cuda" if torch.cuda.is_available() else "cpu"
# device = "cpu"
print(f"Using device: {device}")

with open("login.txt", "r") as f:
    token = f.read()
login(token) #token from huggingface.co necessary to use gemma3
print("login done")

model_name = "google/gemma-3-4b-it"

pipe = pipeline(
    "text-generation", #"image-text-to-text"
    model=model_name,
    torch_dtype=torch.bfloat16,
    device=device, #uses "cpu" here because the "cuda" requires 3 Go more of VRAM (5GO total)
)
print("pipeline initialized")

messages_meta = [
    {
        "role": "system",
        "content": [{"type": "text", "text": system_prompt_meta}]
    },
    {
        "role": "user",
        "content": (
            [{"type": "text", "text": pdf_text_image["24EM03456"]["text"]}]
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
            [{"type": "text", "text": pdf_text_image["24EM03456"]["text"]}]
            #+ [{"type": "image", "image": img} for img in pdf_text_image["24EM03352"]["image"]]
        )
    }
]

output_gemma_4B = pipe(messages_meta, max_new_tokens=250) #temperature=0
print(output_gemma_4B[0]["generated_text"][-1]["content"])
output_gemma_4B2 = pipe(messages_mut, max_new_tokens=250) #temperature=0
print(output_gemma_4B2[0]["generated_text"][-1]["content"])

answer_meta = output_gemma_4B[0]["generated_text"][-1]["content"]
cleaned_meta = answer_meta.replace("```json", "").replace("```", "").strip() #clean the answer
data = json.loads(cleaned_meta)
print(data)

answer_mut = output_gemma_4B2[0]["generated_text"][-1]["content"]
cleaned_mut = answer_mut.replace("```json", "").replace("```", "").strip() #clean the answer
data2 = json.loads(cleaned_mut)
print(data2)

df = pd.DataFrame([data])
df.to_excel("out/metadata_gemma3_4B.xlsx", index=False)
df2 = pd.DataFrame(data2)
df2.to_excel("out/mutation_gemma3_4B.xlsx", index=False)