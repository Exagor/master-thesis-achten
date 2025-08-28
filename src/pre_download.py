# used for pre-download the model
import logging
from huggingface_hub import login
from transformers import AutoModelForCausalLM
import os

# Optionally set a custom cache directory for transformers
os.makedirs("./models", exist_ok=True)
os.environ["HF_HUB_CACHE"] = "./models"

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Login to Hugging Face
with open("login_huggingface.txt", "r") as f:
    token = f.read().strip()

try:
    login(token)
    logger.info("Logged in to Hugging Face successfully")
except Exception as e:
    logger.error(f"Failed to login to Hugging Face: {e}")
    raise

# Pre-download the model
model_name = "google/gemma-3-27b-it" # Qwen/Qwen2.5-VL-3B-Instruct or google/gemma-3-4b-it or google/gemma-3-12b-it
try:
    AutoModelForCausalLM.from_pretrained(model_name)
    logger.info(f"Pre-downloaded model: {model_name}")
except Exception as e:
    logger.error(f"Failed to download model {model_name}: {e}")
    raise
