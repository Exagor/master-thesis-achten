import torch
from huggingface_hub import login
from pdf_parser import *
from transformers import pipeline

model_name = "google/gemma-3-4b-it" #google/gemma-3n-E4B-it or google/gemma-3n-E2B-it or google/gemma-3-4b-it or Qwen/Qwen2.5-VL-3B-Instruct or deepseek-ai/deepseek-vl2-tiny
model_name_shrt = "gemma3_4B" #used for output files

#get the prompt
with open(f"prompt/prompt_engineering_design_metadata.txt", "r") as f: #to test gpt4o, gpto3 and gemini
    system_prompt_meta = f.read()
with open(f"prompt/prompt_engineering_design_mutation.txt", "r") as f:
    system_prompt_mut = f.read()

# Login to Hugging Face to enable the use of gemma 3
with open("login_huggingface.txt", "r") as f:
    token = f.read()
try:
    login(token) #token from huggingface.co necessary to use gemma3
except Exception as e:
    print(f"Failed to login to hugging face: {e}")

# Create the model
device = "cuda" if torch.cuda.is_available() else "cpu"

pipe = pipeline(
    "text-generation", # "image-text-to-text" or "text-generation"
    model=model_name,
    torch_dtype=torch.bfloat16,
    device=device,
    #device_map="auto", #use "auto" to automatically use all available GPUs (but slows the code ??!!)
)

for iteration in range(3): #run 3 times to get a better result
    messages_meta = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "Tu es un assistant spécialisé dans l'ingénierie de prompt. Ton but est de générer des prompts."}]
        },
        {
            "role": "user",
            "content": (
                [{"type": "text", "text": system_prompt_meta}]
            )
        }
    ]

    messages_mut = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "Tu es un assistant spécialisé dans l'ingénierie de prompt. Ton but est de générer des prompts."}]
        },
        {
            "role": "user",
            "content": (
                [{"type": "text", "text": system_prompt_mut}]
            )
        }
    ]

    print(f"Iteration {iteration + 1} for metadata prompt")
    output_meta = pipe(text=messages_meta, max_new_tokens=1200)
    print(f"Iteration {iteration + 1} for mutation prompt")
    output_mut = pipe(text=messages_mut, max_new_tokens=1200)

    answer_meta = output_meta[0]["generated_text"][-1]["content"]
    answer_mut = output_mut[0]["generated_text"][-1]["content"]

    #save in a file
    with open(f"out/generated_prompt_metadata_{model_name_shrt}_{iteration}.txt", "w") as f:
        f.write(answer_meta)
    with open(f"out/generated_prompt_mutation_{model_name_shrt}_{iteration}.txt", "w") as f:
        f.write(answer_mut)

# ask the model to merge the 3 files
all_prompts_meta = "Fusionne ces prompts en un seul très bon prompt :\n"
all_prompts_mut = "Fusionne ces prompts en un seul très bon prompt :\n"
for iteration in range(3):
    with open(f"out/generated_prompt_metadata_{model_name_shrt}_{iteration}.txt", "r") as f:
        meta_content = f.read()
        all_prompts_meta += meta_content + "\n\n"
    with open(f"out/generated_prompt_mutation_{model_name_shrt}_{iteration}.txt", "r") as f:
        mut_content = f.read()
        all_prompts_mut += mut_content + "\n\n"

messages_meta = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "Tu es un assistant utile"}]
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": all_prompts_meta}
                ]
        }
    ]

messages_mut = [
    {
        "role": "system",
        "content": [{"type": "text", "text": "Tu es un assistant utile"}]
    },
    {
        "role": "user",
        "content": [
            {"type": "text", "text": all_prompts_mut}]
    }
]

print("Merging prompts for metadata")
output_meta = pipe(messages_meta, max_new_tokens=1200)
print("Merging prompts for mutation")
output_mut = pipe(messages_mut, max_new_tokens=1200)

answer_meta = output_meta[0]["generated_text"][-1]["content"]
answer_mut = output_mut[0]["generated_text"][-1]["content"]

#save in a file
with open(f"out/generated_prompt_metadata_{model_name_shrt}_merged.txt", "w") as f:
    f.write(answer_meta)
with open(f"out/generated_prompt_mutation_{model_name_shrt}_merged.txt", "w") as f:
    f.write(answer_mut)