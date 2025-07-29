
import camelot
import fitz  # PyMuPDF
import json
import logging
import numpy as np
import os
import pdfplumber
from pdf2image import convert_from_path

# Create a logger
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

def extract_with_pdfplumber(pdf_path:str) -> str:
    """
    Extracts all text from a PDF file using pdfplumber.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        str: The extracted text from all pages, joined by newlines.
    """
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text.append(page.extract_text())
    text = "\n".join(text)
    logging.info("Text extracted from the PDF file")
    return text

def extract_with_pymupdf(pdf_path:str) -> str:
    """
    Extracts all text from a PDF file using PyMuPDF (fitz).
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        str: The extracted text from all pages, joined by newlines.
    """
    text = []
    with fitz.open(pdf_path) as pdf:
        for page in pdf:
            text.append(page.get_text())
    text = "\n".join(text)
    logging.info("Text extracted from the PDF file")
    return text

def extract_dict_from_string(s) -> dict:
    """
    Extracts the first dictionary found in a string and parses it as JSON.
    Args:
        s (str): The input string.
    Returns:
        dict or None: The extracted dictionary, or None if not found or not valid JSON.
    """
    start = s.find('{')
    if start == -1:
        return None  # No dictionary found

    brace_count = 0
    for i in range(start, len(s)):
        if s[i] == '{':
            brace_count += 1
        elif s[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                dict_str = s[start:i+1]
                try:
                    # Try parsing as JSON
                    return json.loads(dict_str)
                except json.JSONDecodeError:
                    logging.debug(f"Metadata output: {s}")
    return None  # No matching closing brace found

def extract_list_of_dicts_from_string(s) -> list:
    """
    Extracts the first list of dictionaries found in a string and parses it as JSON.
    Args:
        s (str): The input string.
    Returns:
        list or None: The extracted list of dictionaries, or None if not found or not valid JSON.
    """
    start = s.find('[')
    if start == -1:
        return None  # No list found

    bracket_count = 0
    for i in range(start, len(s)):
        if s[i] == '[':
            bracket_count += 1
        elif s[i] == ']':
            bracket_count -= 1
            if bracket_count == 0:
                list_str = s[start:i+1]
                try:
                    # Try to parse as JSON
                    return json.loads(list_str)
                except json.JSONDecodeError:
                    print(f"Failed JSON decode : {s}")

    return None  # No matching closing bracket


def extract_tables_camelot(pdf_path:str):
    """
    Extracts tables from a PDF file using Camelot (lattice flavor).
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        camelot.core.TableList: List of tables extracted from the PDF.
    """
    tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
    logging.info(f"Tables extracted")
    return tables

def extract_pdf2image(pdf_path, save=False, save_folder_path=None):
    """
    Converts each page of a PDF file to an image.
    Args:
        pdf_path (str): Path to the PDF file.
        save (bool): Whether to save the images to disk.
        save_folder_path (str, optional): Folder path to save images if save is True.
    Returns:
        list: List of PIL Image objects, one per page.
    """
    images = convert_from_path(pdf_path)
    if save:
        for i in range(len(images)):
            page_image = images[i]
            # Remove .pdf extension from pdf_file
            image_filename = os.path.splitext(pdf_path)[0]
            page_image.save(os.path.join(save_folder_path, f"{image_filename}_page_{i}.png"), "PNG")
    return images