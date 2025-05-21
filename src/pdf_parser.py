"""
Simple implementation using pdf parser and a rule based approach to extract keys information and tables from PDF files.
"""

import camelot
import fitz
import logging
import numpy as np
import os
import pandas as pd
import pdfplumber
import re
from pdf2image import convert_from_path

# Create a logger
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

def extract_with_pdfplumber(pdf_path:str) -> str:
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text.append(page.extract_text())
    text = "\n".join(text)
    logging.info("Text extracted from the PDF file")
    return text

def extract_with_pymupdf(pdf_path:str) -> str:
    text = []
    with fitz.open(pdf_path) as pdf:
        for page in pdf:
            text.append(page.get_text())
    text = "\n".join(text)
    logging.info("Text extracted from the PDF file")
    return text

def format_metadata(text:str) -> dict:
    examen_info = re.findall(r'EXAMEN\s*:\s*(\S+)', text)
    # prelev_info = re.findall(r'N° du prélèvement\s*:\s*(\S+)', text)
    prelev_info = re.findall(r'N° du prélèvement\s*:\s*([^\n\r]+)', text)
    panel_keywords = {
        "Oncomine": "OST",
        "OVAIRE": "GP",
        "COLON & LUNG": "CLP",
        "THYROID": "TP"
    }
    panel_info = "CHP" #base case
    for keyword, value in panel_keywords.items():
        if re.search(keyword, text): # previously re.search(keyword, text, re.IGNORECASE)
            panel_info = value
            break
    zone_info = re.findall(r'Origine du prélèvement\s*:\s*((?:(?!  ).)+)', text)
    type_info = re.findall(r'Type de prélèvement\s*:\s*((?:(?!  ).)+)', text)
    percentage_info = re.findall(r'% de cellules tumorales\s*:\s*<?\s*(\d+)', text)
    analyse_info = re.findall(r'% de cellules à analyser\s*:\s*<?\s*(\d+)', text)
    quality_info = re.findall(r'Qualité du séquençage\s*:\s*(\S+)', text)
    logging.info("Information extracted from the text")

    # Extract the first match from each list
    examen_info = examen_info[0] if examen_info else ""
    prelev_info = prelev_info[0] if prelev_info else ""
    zone_info = zone_info[0] if zone_info else ""
    type_info = type_info[0] if type_info else ""
    percentage_info = percentage_info[0] if percentage_info else ""
    analyse_info = analyse_info[0] if analyse_info else ""
    quality_info = quality_info[0] if quality_info else ""
    # Combine the extracted information into a DataFrame
    data = {
        "Examen": examen_info,
        "N° du prélèvement": prelev_info,
        "Panel": panel_info,
        "Origine du prélèvement": zone_info,
        "Type de prélèvement": type_info,
        "% de cellules tumorales": percentage_info,
        "% de cellules à analyser": analyse_info,
        "Qualité du séquencage": quality_info
    }

    return data

def extract_tables_camelot(pdf_path:str):
    tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
    logging.info(f"Tables extracted")
    return tables

def extract_pdf2image(pdf_path, save=False, save_folder_path=None):
    images = convert_from_path(pdf_path)
    if save:
        for i in range(len(images)):
            page_image = images[i]
            # Remove .pdf extension from pdf_file
            image_filename = os.path.splitext(pdf_path)[0]
            page_image.save(os.path.join(save_folder_path, f"{image_filename}_page_{i}.png"), "PNG")
    return images

def post_process_data(metadata:dict, tables):
    # Process the metadata
    df_doc = pd.DataFrame(metadata)
    # Merge the two columns named "% de cellules tumorales" and "% de cellules à analyser"
    df_doc["% de cellules"] = df_doc["% de cellules tumorales"] + df_doc["% de cellules à analyser"]
    df_doc.drop(columns=["% de cellules tumorales", "% de cellules à analyser"], inplace=True)

    # Process the tables
    df_table = pd.DataFrame()
    for i,table in enumerate(tables):
        if table.n < 3: # if there's no table results
            df = None
        else:
            df = table[2].df
            
            # Extract the first row and split it by '\n' to get the column names
            column_names = df.iloc[0, 0].split('\n')
            df = df.drop(0).reset_index(drop=True)
            # Split the remaining rows by '\n' and create a new DataFrame
            df = df[0].str.split('\n', expand=True)
            df.columns = column_names
            df["Examen"] = df_doc.loc[i, "Examen"] #add the exam number
            for _, row in df.iterrows():
                df_table = df_table._append(row, ignore_index=True)

    # Drop column unused
    columns_to_drop = ["muté", "% d’ADN "]
    df_table.drop(columns=[col for col in columns_to_drop if col in df_table.columns], inplace=True)

    # Handles the impact clinique
    df_table["Impact clinique"] = None
    impact_clinique = None
    for index, row in df_table.iterrows():
        if row["Gène "] == "Mutations avec impact clinique potentiel":
            impact_clinique = "potentiel"
            delete_row = True
        elif row["Gène "] == "Mutations avec impact clinique indéterminé":
            impact_clinique = "indéterminé"
            delete_row = True
        elif row["Gène "] == "Mutations avec impact clinique avéré":
            impact_clinique = "avéré"
            delete_row = True
        else:
            df_table.at[index, "Impact clinique"] = impact_clinique
            delete_row = False
        if delete_row:
            df_table.drop(index, inplace=True)
            delete_row = False

    # Reorder the columns of df_table
    columns = ["Examen"] + [col for col in df_table.columns if col != "Examen"]
    df_table = df_table[columns]

    # Remove the last space in the column names
    df_table.columns = [col[:-1] if col.endswith(" ") else col for col in df_table.columns]

    logging.info("Data post-processed")
    return df_doc, df_table

def extract_all(pdf_path: str) -> str:
    """
    Extract all text from the PDF and insert tables (found with camelot) in the text at the place where they should be, in markdown format.
    Returns a single string with text and tables in order.
    """

    doc = fitz.open(pdf_path)
    num_pages = doc.page_count
    output = []

    tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
    tables_by_page = {}
    for table in tables:
        page = table.page - 1  # camelot pages are 1-based, fitz is 0-based
        if page not in tables_by_page:
            tables_by_page[page] = []
        tables_by_page[page].append(table)

    for page_num in range(num_pages):
        page = doc[page_num]
        blocks = page.get_text("blocks")
        blocks = sorted(blocks, key=lambda b: b[1])  # sort by y0
        page_tables = tables_by_page.get(page_num, [])
        table_idx = 0
        block_idx = 0
        while block_idx < len(blocks) or table_idx < len(page_tables):
            next_block_y = blocks[block_idx][1] if block_idx < len(blocks) else float('inf')
            if table_idx < len(page_tables):
                next_table_y = page_tables[table_idx]._bbox[1]
            else:
                next_table_y = float('inf')
            if next_table_y < next_block_y:
                md = page_tables[table_idx].df.to_markdown(index=False)
                output.append(md)
                table_idx += 1
            elif block_idx < len(blocks):
                text = blocks[block_idx][4].strip()
                if text:
                    output.append(text)
                block_idx += 1
            else:
                break
        while table_idx < len(page_tables):
            md = page_tables[table_idx].df.to_markdown(index=False)
            output.append(md)
            table_idx += 1
    return '\n\n'.join(output)

if __name__ == "__main__":
    # Find all PDF files in the pdf folder and save them in a list
    pdf_folder_path = "data/PDF"
    save_folder_path = "out/"
    pdf_files = [f for f in os.listdir(pdf_folder_path) if f.endswith('.pdf')]
    # pdf_files = ["24EM03355.pdf"]

    list_data = []
    table_list = []
    for file in pdf_files:
        pdf_path = f"{pdf_folder_path}/{file}"
        text = extract_with_pdfplumber(pdf_path)
        metadata = format_metadata(text)
        if metadata:
            list_data.append(metadata)
        table_list.append(extract_tables_camelot(pdf_path))
    
    df_doc, df_tables = post_process_data(list_data, table_list)

    # Save the dataframe to a csv file
    df_doc.to_excel(f"{save_folder_path}/extracted_metadata.xlsx", index=False)
    df_tables.to_excel(f"{save_folder_path}/extracted_results_mutation.xlsx", index=False)