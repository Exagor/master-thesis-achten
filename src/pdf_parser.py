"""
Simple implementation using pdf parser
"""
import camelot
import fitz  # PyMuPDF
import logging
import os
import pandas as pd
import re

# Create a logger
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

def extract_with_pymupdf(pdf_path:str) -> dict:
    # Open the PDF file
    try:
        document = fitz.open(pdf_path)
    except Exception as e:
        logging.error(f"Failed to open PDF file: {e}")
        return pd.DataFrame()
    text = ""

    # Iterate through each page
    for page_num in range(len(document)):
        page = document.load_page(page_num)
        text += page.get_text()
    logging.info("Text extracted from the PDF file")

    # Extract the information next to the followin keywords
    examen_info = re.findall(r'EXAMEN\s*:\s*(\S+)', text)
    prelev_info = re.findall(r'N° du prélèvement\s*:\s*(\S+)', text)
    zone_info = re.findall(r'Origine du prélèvement\s*:\s*(\S+)', text)
    percentage_info = re.findall(r'% de cellules tumorales\s*:\s*<?\s*(\d+)', text)
    analyse_info = re.findall(r'% de cellules à analyser\s*:\s*<?\s*(\d+)', text)
    logging.info("Information extracted from the text")

    # Extract the first match from each list
    examen_info = examen_info[0] if examen_info else ""
    prelev_info = prelev_info[0] if prelev_info else ""
    zone_info = zone_info[0] if zone_info else ""
    percentage_info = percentage_info[0] if percentage_info else ""
    analyse_info = analyse_info[0] if analyse_info else ""
    # Combine the extracted information into a DataFrame
    data = {
        "EXAMEN": examen_info,
        "N° du prélèvement": prelev_info,
        "Origine du prélèvement": zone_info,
        "% de cellules tumorales": percentage_info,
        "% de cellules à analyser": analyse_info
    }

    return data

def extract_tables_camelot(pdf_path:str, filename:str, save_folder_path:str):
    tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
    base_filename = os.path.splitext(filename)[0]
    tables.export(f'{save_folder_path}/tables_{base_filename}.csv', f='csv')
    logging.info(f"Tables extracted")
    return tables

if __name__ == "__main__":
    # Find all PDF files in the pdf folder and save them in a list
    pdf_folder_path = "data/PDF"
    save_folder_path = "data/processed_parser"
    pdf_files = [f for f in os.listdir(pdf_folder_path) if f.endswith('.pdf')]

    all_data = []
    for file in pdf_files:
        pdf_path = f"{pdf_folder_path}/{file}"
        data = extract_with_pymupdf(pdf_path)
        table_list = extract_tables_camelot(pdf_path, file, save_folder_path)
        if data:
            all_data.append(data)

    df = pd.DataFrame(all_data)

    # Save the dataframe to a csv file
    df.to_csv(f"{save_folder_path}/extracted_pdfparser.csv", index=False)