import pandas as pd
import os
import unicodedata
import Levenshtein

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

def evaluate_model_metadata(model_excel_path, true_csv_path, key_column=None):
    """
    Compare model results with true results line by line, matching on exam number, and print evaluation metrics.
    Returns:
        accuracy (float): row-level accuracy
        col_accuracy (dict): column-level accuracy
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
            if isinstance(m_val, str) or isinstance(t_val, str): #check if there are strings
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
    if mismatches: #if there are mismatches
        print(f"\nTotal mismatches: {len(mismatches)}")
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
    col_accuracy = {}
    if matched_model_rows and matched_true_rows:
        matched_model_df = pd.DataFrame(matched_model_rows)
        matched_true_df = pd.DataFrame(matched_true_rows)
        print("\nPer-column accuracy (for matched exam numbers):")
        for col in matched_true_df.columns:
            if col not in matched_model_df.columns:
                print(f"  {col}: column missing in model results")
                col_accuracy[col] = None
                continue
            m_vals = matched_model_df[col]
            t_vals = matched_true_df[col]
            # Normalize strings for comparison
            if m_vals.dtype == object or t_vals.dtype == object: #check if there are strings
                m_vals_norm = m_vals.apply(lambda x: normalize_string(str(x)))
                t_vals_norm = t_vals.apply(lambda x: normalize_string(str(x)))
                acc = (m_vals_norm == t_vals_norm).mean()
            else:
                acc = (m_vals == t_vals).mean()
            print(f"  {col}: {acc:.3f}")
            col_accuracy[col] = acc
    print("\nEvaluation complete.")
    return accuracy, col_accuracy # Return accuracy and column accuracy

def norm_row(row):
    return tuple(normalize_string(str(x)) if isinstance(x, str) else x for x in row)

def evaluate_model_mutations(model_path, true_path):
    model_df = pd.read_excel(model_path)
    true_df = pd.read_csv(true_path)

    # Ensure columns are in the same order and names
    model_df = model_df[true_df.columns.intersection(model_df.columns)]
    true_df = true_df[model_df.columns]

    # Group by exam number
    exam_col = true_df.columns[0]
    model_grouped = model_df.groupby(exam_col)
    true_grouped = true_df.groupby(exam_col)

    all_exam_numbers = set(model_grouped.groups.keys()) | set(true_grouped.groups.keys()) # Union of all exam numbers
    total = len(all_exam_numbers)
    exact_matches = 0
    mismatches = []

    for exam in sorted(all_exam_numbers):
        model_rows = model_grouped.get_group(exam) if exam in model_grouped.groups else pd.DataFrame(columns=model_df.columns)
        true_rows = true_grouped.get_group(exam) if exam in true_grouped.groups else pd.DataFrame(columns=true_df.columns)

        # Convert all values to tuple of normalized strings for fair comparison
        model_set = set(norm_row(row) for row in model_rows.values)
        true_set = set(norm_row(row) for row in true_rows.values)

        if model_set == true_set:
            exact_matches += 1
        else:
            # For easier debugging, show the normalized sets as well
            mismatches.append((exam, list(model_set), list(true_set)))

    accuracy = exact_matches / total if total > 0 else 0
    print(f"Extracted mutations accuracy : {accuracy:.3f} ({exact_matches}/{total})")
    if mismatches:
        print("Mismatches (up to 5):")
        for exam, model_vals, true_vals in mismatches[:5]:
            print(f"Exam {exam}:")
            print(f"  Model: {model_vals}\n  True:  {true_vals}")
    else:
        print("All exam mutation sets match exactly.")

def levenshtein_distance(s1, s2):
    if pd.isna(s1) and pd.isna(s2):
        return 0
    if pd.isna(s1) or pd.isna(s2):
        return max(len(str(s1)), len(str(s2)))
    return Levenshtein.distance(str(s1), str(s2))


def evaluate_model_metadata_levenshtein(model_excel_path, true_csv_path):
    """
    Compare model results with true results using Levenshtein distance (row and column-wise).
    Prints average Levenshtein distance per row and per column.
    """
    model_df = pd.read_excel(model_excel_path)
    true_df = pd.read_csv(true_csv_path)

    exam_col_true = true_df.columns[0]
    exam_col_model = model_df.columns[0]

    model_df_indexed = model_df.set_index(exam_col_model)
    true_df_indexed = true_df.set_index(exam_col_true)

    matched_model_rows = []
    matched_true_rows = []
    for exam_number, true_row in true_df_indexed.iterrows():
        if exam_number not in model_df_indexed.index:
            continue
        model_row = model_df_indexed.loc[exam_number]
        matched_model_rows.append(model_row)
        matched_true_rows.append(true_row)

    if not matched_model_rows or not matched_true_rows:
        print("No matching rows found for Levenshtein evaluation.")
        return None, None

    matched_model_df = pd.DataFrame(matched_model_rows)
    matched_true_df = pd.DataFrame(matched_true_rows)

    # Row-wise Levenshtein (sum of distances for each row)
    row_distances = []
    for m_row, t_row in zip(matched_model_df.values, matched_true_df.values):
        row_distance = sum(levenshtein_distance(m, t) for m, t in zip(m_row, t_row))
        row_distances.append(row_distance)
    avg_row_distance = sum(row_distances) / len(row_distances) if row_distances else None
    print(f"Average Levenshtein distance per row: {avg_row_distance:.3f}")

    # Column-wise Levenshtein (average per column)
    col_distances = {}
    print("\nAverage Levenshtein distance per column:")
    for col in matched_true_df.columns:
        if col not in matched_model_df.columns:
            print(f"  {col}: column missing in model results")
            col_distances[col] = None
            continue
        m_vals = matched_model_df[col]
        t_vals = matched_true_df[col]
        distances = [levenshtein_distance(m, t) for m, t in zip(m_vals, t_vals)]
        avg_col_dist = sum(distances) / len(distances) if distances else None
        print(f"  {col}: {avg_col_dist:.3f}")
        col_distances[col] = avg_col_dist
    print("\nLevenshtein evaluation complete.")
    return avg_row_distance, col_distances

def evaluate_model_mutations_levenshtein(model_path, true_path):
    """
    Compare model mutation results with true results using Levenshtein distance.
    Prints average Levenshtein distance per exam (set of rows).
    """
    model_df = pd.read_excel(model_path)
    true_df = pd.read_csv(true_path)

    # Ensure columns are in the same order and names
    model_df = model_df[true_df.columns.intersection(model_df.columns)]
    true_df = true_df[model_df.columns]

    # Group by exam number
    exam_col = true_df.columns[0]
    model_grouped = model_df.groupby(exam_col)
    true_grouped = true_df.groupby(exam_col)

    all_exam_numbers = set(model_grouped.groups.keys()) | set(true_grouped.groups.keys())
    total = len(all_exam_numbers)
    exam_distances = []
    mismatches = []

    for exam in sorted(all_exam_numbers):
        model_rows = model_grouped.get_group(exam) if exam in model_grouped.groups else pd.DataFrame(columns=model_df.columns)
        true_rows = true_grouped.get_group(exam) if exam in true_grouped.groups else pd.DataFrame(columns=true_df.columns)

        # Convert all values to tuple of normalized strings for fair comparison
        model_set = [norm_row(row) for row in model_rows.values]
        true_set = [norm_row(row) for row in true_rows.values]

        # Compute pairwise Levenshtein distances between all rows in model_set and true_set
        if not model_set and not true_set:
            exam_distances.append(0)
            continue
        if not model_set or not true_set:
            # All rows missing, penalize by length of the other set
            max_len = max(len(model_set), len(true_set))
            exam_distances.append(max_len)
            mismatches.append((exam, model_set, true_set))
            continue
        # For each row in true_set, find the closest row in model_set
        used = set()
        total_dist = 0
        for t_row in true_set:
            min_dist = None
            min_idx = None
            for idx, m_row in enumerate(model_set):
                if idx in used:
                    continue
                dist = sum(levenshtein_distance(m, t) for m, t in zip(m_row, t_row))
                if min_dist is None or dist < min_dist:
                    min_dist = dist
                    min_idx = idx
            if min_idx is not None:
                used.add(min_idx)
                total_dist += min_dist
            else:
                total_dist += sum(len(str(x)) for x in t_row)  # Penalize missing row
        # Penalize extra model rows
        total_dist += sum(sum(len(str(x)) for x in model_set[idx]) for idx in range(len(model_set)) if idx not in used)
        avg_exam_dist = total_dist / max(len(true_set), len(model_set))
        exam_distances.append(avg_exam_dist)
        if avg_exam_dist > 0:
            mismatches.append((exam, model_set, true_set))

    avg_exam_distance = sum(exam_distances) / total if total > 0 else None
    print(f"Average Levenshtein distance per exam (mutations): {avg_exam_distance:.3f}")
    if mismatches:
        print("Mismatches (up to 5):")
        for exam, model_vals, true_vals in mismatches[:5]:
            print(f"Exam {exam}:")
            print(f"  Model: {model_vals}\n  True:  {true_vals}")
    else:
        print("All exam mutation sets match exactly.")
    print("\nLevenshtein mutation evaluation complete.")
    return avg_exam_distance

if __name__ == "__main__":
    model_excel_path = 'out/extracted_metadata.xlsx'
    true_csv_path = 'data/verified_metadata.csv'
    
    # Check if files exist
    if not os.path.exists(model_excel_path):
        print(f"Model results file not found: {model_excel_path}")
    if not os.path.exists(true_csv_path):
        print(f"True results file not found: {true_csv_path}")
    # Evaluate the model results
    evaluate_model_metadata(model_excel_path, true_csv_path)

    model_excel_path = 'out/extracted_results_mutation.xlsx'
    true_csv_path = 'data/verified_mutations_without_none.csv'

    evaluate_model_mutations(model_excel_path, true_csv_path)
    # Evaluate Levenshtein distances
    print("\nEvaluating Levenshtein distances for metadata...")
    evaluate_model_metadata_levenshtein(model_excel_path, true_csv_path)
    print("\nEvaluating Levenshtein distances for mutations...")
    evaluate_model_mutations_levenshtein(model_excel_path, true_csv_path)
    print("\nEvaluation complete.")
    print("All evaluations completed successfully.")