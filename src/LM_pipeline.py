from pdf_parser import *
import os
from transformers import AutoTokenizer, AutoModelForQuestionAnswering, pipeline
import json
import pandas as pd

pdf_folder_path = "data/PDF/"
pdf_files_path = [f for f in os.listdir(pdf_folder_path) if f.endswith('.pdf')]

pdf_text = {}
for pdf_file in pdf_files_path:
    pdf_text[os.path.splitext(pdf_file)[0]] = extract_with_pdfplumber(os.path.join(pdf_folder_path,pdf_file))

model = AutoModelForQuestionAnswering.from_pretrained("almanach/camembertav2-base-fquad")
tokenizer = AutoTokenizer.from_pretrained("almanach/camembertav2-base-fquad")

qa_pipeline = pipeline("question-answering", model=model, tokenizer=tokenizer)

with open("prompt/metadata_columns_prompt.json", "r") as f:
    metadata_prompt = json.load(f)

# Prepare all (id, col_name, question, context) tuples
batch_inputs = []
id_col_pairs = []
for id, text in pdf_text.items():
    for col_name, question in metadata_prompt.items():
        batch_inputs.append({"question": question, "context": text})
        id_col_pairs.append((id, col_name))
print("Batches ready")

# Run the pipeline in batch
results = qa_pipeline(batch_inputs)

# Fill the final_table
final_table = {}
for (id, col_name), result in zip(id_col_pairs, results):
    if id not in final_table:
        final_table[id] = {}
    final_table[id][col_name] = result['answer']

print(final_table)

# save the results in an xlsx file
df = pd.DataFrame.from_dict(final_table, orient='index')
df.to_excel("out/metadata_camembert.xlsx", index=False)