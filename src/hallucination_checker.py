"""
Script to help detect hallucinations from the model output.
"""

import pandas as pd
import os
from utils import *
from tqdm import tqdm
import re


def check_hallucination(pdf_folder, excel_path_meta=None, excel_path_mut=None, save_path="./") -> pd.DataFrame:
    """
    Check the mutations in the excel and verify they are present in the pdfs. 
    If they are not presents, write a report indicating which report must be verified.
    Args:
        pdf_folder (str): Path to the folder containing the PDFs.
        excel_path_meta (str): Path to the Excel file containing metadata data.
        excel_path_mut (str): Path to the Excel file containing mutation data.
        save_path (str): Path to save the report, must specify the name of the file.
    returns:
        report (pd.DataFrame): DataFrame containing the report of mutations not found in PDFs.
    """

    # Initialize a list to store the report
    report = []

    if excel_path_mut is not None :
        # Load the mutation data from the Excel file
        df_mut = pd.read_excel(excel_path_mut)
        df_mut.dropna(subset=['Examen', 'Mutation'], inplace=True)

        # Iterate through each row in the DataFrame
        for index, row in tqdm(df_mut.iterrows()):
            pdf_name = row['Examen']
            mutation = row['Mutation']

            # Check if the PDF exists in the specified folder
            pdf_path = f"{pdf_folder}/{pdf_name}.pdf"
            if not os.path.exists(pdf_path):
                report.append({
                    'pdf_name': pdf_name,
                    'mutations': mutation,
                    'status': 'PDF not found'
                })
                continue

            # Extract text from the PDF and search the mutation in it
            try: 
                pdf_text = extract_with_pdfplumber(pdf_path)
            except Exception as e:
                report.append({
                    'pdf_name': pdf_name,
                    'mutations': mutation,
                    'status': f'Error extracting PDF: {e}'
                })
                continue
            
            # Use regex for exact match (whole word, accept end of line and spaces around)
            pattern = r'{}\s|{}$'.format(re.escape(str(mutation)), re.escape(str(mutation)))
            if not re.search(pattern, pdf_text):
                report.append({
                    'pdf_name': pdf_name,
                    'mutations': mutation,
                    'status': 'Mutation not found in PDF or ambiguity'
                })

    if excel_path_meta is not None :
        df_meta = pd.read_excel(excel_path_meta)
        for index, row in tqdm(df_meta.iterrows()):
            pdf_name = row['Examen']

            # Check if the PDF exists in the specified folder
            pdf_path = f"{pdf_folder}/{pdf_name}.pdf"
            if not os.path.exists(pdf_path):
                report.append({
                    'pdf_name': pdf_name,
                    'status': 'PDF not found or exam number incorrect'
                })
                continue


    # Convert the report to a DataFrame and save it
    report_df = pd.DataFrame(report)
    report_df.to_excel(save_path, index=False)
    
    return report_df

if __name__ == "__main__":
    # Example usage
    pdf_folder = 'data/PDF'
    # excel_path_meta = 'out/metadata_gemma3_4B.xlsx'
    # excel_path_mut = 'out/mutation_gemma3_4B.xlsx'
    excel_path_meta = 'prompt_engineering/experiments/metadata_llama32_3B_grok.xlsx'
    excel_path_mut = 'prompt_engineering/experiments/mutation_llama32_3B_grok.xlsx'
    save_path = 'out/hallucination_report.xlsx'

    report_df = check_hallucination(pdf_folder, excel_path_meta, excel_path_mut, save_path)
    print(report_df)