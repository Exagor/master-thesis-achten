import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import os
import unicodedata

def normalize_string(s):
    if not isinstance(s, str):
        return s
    # Remove accents, lowercase, and collapse multiple spaces
    s = unicodedata.normalize('NFKD', s)
    s = ''.join([c for c in s if not unicodedata.combining(c)])
    s = s.lower()
    s = s.replace("'", "")
    s = s.replace("’", "")
    s = ''.join(s.split())
    return s

def evaluate_model_results(model_excel_path, true_csv_path, key_column=None):
    """
    Compare model results with true results line by line, matching on exam number, and print evaluation metrics.
    Args:
        model_excel_path (str): Path to the model results Excel file.
        true_csv_path (str): Path to the true results CSV file.
        key_column (str, optional): Column to align/merge on if needed.
    """
    # Load data
    model_df = pd.read_excel(model_excel_path)
    true_df = pd.read_csv(true_csv_path)

    # Use the first column as the exam number key
    exam_col_true = true_df.columns[0]
    exam_col_model = model_df.columns[0]

    # Set index to exam number for fast lookup
    model_df_indexed = model_df.set_index(exam_col_model)
    true_df_indexed = true_df.set_index(exam_col_true)

    total = len(true_df_indexed)
    exact_matches = 0
    mismatches = []
    matched_model_rows = []
    matched_true_rows = []
    for exam_number, true_row in true_df_indexed.iterrows():
        if exam_number not in model_df_indexed.index:
            mismatches.append((exam_number, "Exam number missing in model results", None, true_row.values))
            continue
        model_row = model_df_indexed.loc[exam_number]
        matched_model_rows.append(model_row)
        matched_true_rows.append(true_row)
        # Compare each value with normalization for strings
        row_match = True
        for m_val, t_val in zip(model_row, true_row):
            if isinstance(m_val, str) or isinstance(t_val, str):
                if normalize_string(str(m_val)) != normalize_string(str(t_val)):
                    row_match = False
                    break
            else:
                if pd.isna(m_val) and pd.isna(t_val):
                    continue
                if m_val != t_val:
                    row_match = False
                    break
        if row_match:
            exact_matches += 1
        else:
            mismatches.append((exam_number, None, model_row.values, true_row.values))

    accuracy = exact_matches / total if total > 0 else 0
    print(f"Line-by-line exact match accuracy (exam number matched): {accuracy:.3f} ({exact_matches}/{total})")
    if mismatches:
        print(f"\nMismatched rows (showing up to 5):")
        for exam_number, exam_msg, model_vals, true_vals in mismatches[:5]:
            if exam_msg:
                print(f"Exam {exam_number}: {exam_msg}")
                print(f"  True:  {true_vals}")
            else:
                print(f"Exam {exam_number}:")
                print(f"  Model: {model_vals}\n  True:  {true_vals}")
    else:
        print("All rows match exactly.")

    # Per-column score (for matched exam numbers)
    if matched_model_rows and matched_true_rows:
        matched_model_df = pd.DataFrame(matched_model_rows)
        matched_true_df = pd.DataFrame(matched_true_rows)
        print("\nPer-column accuracy (for matched exam numbers):")
        for col in matched_true_df.columns:
            if col not in matched_model_df.columns:
                print(f"  {col}: column missing in model results")
                continue
            m_vals = matched_model_df[col]
            t_vals = matched_true_df[col]
            # Normalize strings for comparison
            if m_vals.dtype == object or t_vals.dtype == object:
                m_vals_norm = m_vals.apply(lambda x: normalize_string(str(x)))
                t_vals_norm = t_vals.apply(lambda x: normalize_string(str(x)))
                acc = (m_vals_norm == t_vals_norm).mean()
            else:
                acc = (m_vals == t_vals).mean()
            print(f"  {col}: {acc:.3f}")
    print("\nEvaluation complete.")

if __name__ == "__main__":
    model_excel_path = 'out/extracted_metadata.xlsx'
    true_csv_path = 'data/verified_metadata.csv'
    
    # Check if files exist
    if not os.path.exists(model_excel_path):
        print(f"Model results file not found: {model_excel_path}")
    if not os.path.exists(true_csv_path):
        print(f"True results file not found: {true_csv_path}")

    # Evaluate the model results
    evaluate_model_results(model_excel_path, true_csv_path)

    string = "AzfSA op.789 ééèà"
    print(normalize_string(string))