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
    Check the mutations and metadata in the excel files and verify they are present in the pdfs.
    If they are not present, write a report indicating which report must be verified.
    Args:
        pdf_folder (str): Path to the folder containing the PDFs.
        excel_path_meta (str): Path to the Excel file containing metadata data.
        excel_path_mut (str): Path to the Excel file containing mutation data.
        save_path (str): Path to save the report, must specify the name of the file.
    Returns:
        report (pd.DataFrame): DataFrame containing the report of mutations/metadata not found in PDFs.
    """

    report = []

    # Collect all unique pdf names from both meta and mut files
    pdf_names = set()
    meta_rows = []
    mut_rows = []

    if excel_path_meta is not None:
        df_meta = pd.read_excel(excel_path_meta)
        for index, row in df_meta.iterrows():
            pdf_name = row['Examen']
            sample = row['N° du prélèvement']
            pdf_names.add(pdf_name)
            meta_rows.append((pdf_name, sample))

    if excel_path_mut is not None:
        df_mut = pd.read_excel(excel_path_mut)
        df_mut.dropna(subset=['Examen', 'Mutation'], inplace=True)
        for index, row in df_mut.iterrows():
            pdf_name = row['Examen']
            mutation = row['Mutation']
            pdf_names.add(pdf_name)
            mut_rows.append((pdf_name, mutation))

    # Extract text for each PDF only once
    pdf_texts = {}
    for pdf_name in tqdm(pdf_names, desc="Extracting PDF texts"):
        pdf_path = f"{pdf_folder}/{pdf_name}.pdf"
        if not os.path.exists(pdf_path):
            pdf_texts[pdf_name] = None
        else:
            try:
                pdf_texts[pdf_name] = extract_with_pdfplumber(pdf_path)
            except Exception as e:
                pdf_texts[pdf_name] = f"ERROR: {e}"

    # Check mutations
    for pdf_name, mutation in mut_rows:
        pdf_text = pdf_texts.get(pdf_name)
        if pdf_text is None:
            report.append({
                'pdf_name': pdf_name,
                'mutations': mutation,
                'status': 'PDF not found'
            })
            continue
        if isinstance(pdf_text, str) and pdf_text.startswith("ERROR:"):
            report.append({
                'pdf_name': pdf_name,
                'mutations': mutation,
                'status': pdf_text
            })
            continue
        pattern = r'{}\s|{}$'.format(re.escape(str(mutation)), re.escape(str(mutation)))
        if not re.search(pattern, pdf_text):
            report.append({
                'pdf_name': pdf_name,
                'mutations': mutation,
                'status': 'Mutation not found in PDF or ambiguity'
            })

    # Check metadata samples
    for pdf_name, sample in meta_rows:
        pdf_text = pdf_texts.get(pdf_name)
        if pdf_text is None:
            report.append({
                'pdf_name': pdf_name,
                'sample': sample,
                'status': 'PDF not found or exam number incorrect'
            })
            continue
        if isinstance(pdf_text, str) and pdf_text.startswith("ERROR:"):
            report.append({
                'pdf_name': pdf_name,
                'sample': sample,
                'status': pdf_text
            })
            continue
        pattern = r'{}[\s-]|{}$'.format(re.escape(str(sample)), re.escape(str(sample)))
        if not re.search(pattern, pdf_text):
            report.append({
                'pdf_name': pdf_name,
                'sample': sample,
                'status': 'N° de prélèvement not found in PDF or ambiguity'
            })

    # Convert the report to a DataFrame and save it
    report_df = pd.DataFrame(report)
    if 'status' in report_df.columns:
        status_col = report_df.pop('status')
        report_df['status'] = status_col
    report_df.to_excel(save_path, index=False)

    return report_df


if __name__ == "__main__":
    # Example usage
    pdf_folder = 'data/PDF'
    excel_path_meta = 'out/metadata_gemma3_4B.xlsx'
    excel_path_mut = 'out/mutation_gemma3_4B.xlsx'
    # excel_path_meta = 'prompt_engineering/experiments/metadata_llama32_3B_grok.xlsx'
    # excel_path_mut = 'prompt_engineering/experiments/mutation_llama32_3B_grok.xlsx'
    save_path = 'out/hallucination_report.xlsx'

    report_df = check_hallucination(pdf_folder, excel_path_meta, excel_path_mut, save_path)
    print(report_df)