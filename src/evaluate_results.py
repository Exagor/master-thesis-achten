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
        for m_val, t_val in zip(model_row, true_row): # iterate through each value in the row
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
    print(f"\nExtracted mutations accuracy : {accuracy:.3f} ({exact_matches}/{total})")
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

def normalized_levenshtein_similarity(s1, s2, t=0.5):
    # handle the Nan case
    if pd.isna(s1) and pd.isna(s2):
        return 1
    elif pd.isna(s1) or pd.isna(s2):
        return 0
    # If both are floats or ints, compare as integers (removing .0)
    if isinstance(s1, (float, int)) and isinstance(s2, (float, int)):
        s1_str = str(int(s1))
        s2_str = str(int(s2))
    elif isinstance(s1, float):
        s1_str = str(int(s1))
        s2_str = str(s2)
    elif isinstance(s2, float):
        s1_str = str(s1)
        s2_str = str(int(s2))
    else:
        s1_str = str(s1)
        s2_str = str(s2)
    NL = levenshtein_distance(s1_str, s2_str) / max(len(s1_str), len(s2_str)) if max(len(s1_str), len(s2_str)) > 0 else 0
    similarity = 1 - NL if NL < t else 0
    return similarity


def evaluate_metadata_levenshtein(model_excel_path, true_csv_path, print_results=True):
    """
    Compare model results with true results using average normalized Levenshtein similarity (column-wise).
    Prints average ANLS per column.
    """
    # Match the model and true data by exam number
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

    # using matched columns
    matched_model_df = pd.DataFrame(matched_model_rows)
    matched_true_df = pd.DataFrame(matched_true_rows)

    # Column-wise Levenshtein (average per column)
    col_similarities = {}
    if print_results :
        print("\nAverage ANLS per column (metadata):")
    for col in matched_true_df.columns:
        if col not in matched_model_df.columns:
            print(f"  {col}: column missing in model results")
            col_similarities[col] = None
            continue
        m_vals = matched_model_df[col]
        t_vals = matched_true_df[col]

        similarities = [normalized_levenshtein_similarity(normalize_string(m), normalize_string(t)) for m, t in zip(m_vals, t_vals)]
        avg_col_sim = sum(similarities) / len(similarities) if similarities else None
        if print_results :
            print(f"  {col}: {avg_col_sim:.3f}")
        col_similarities[col] = avg_col_sim
    return col_similarities

def evaluate_mutations_levenshtein(model_path, true_path, print_results=True):
    """
    Compare model mutation results with true results using Levenshtein distance (column-wise).
    Prints ANLS distance per column.
    """
    model_df = pd.read_excel(model_path)
    true_df = pd.read_csv(true_path)
    model_df.dropna(subset=["Mutation"],inplace=True)  # Drop rows where "Mutation" is NaN
    true_df.dropna(subset=["Mutation"],inplace=True)  

    # Ensure columns are in the same order and names
    model_df = model_df[true_df.columns.intersection(model_df.columns)]
    true_df = true_df[model_df.columns]

    # Group by exam number
    exam_col = true_df.columns[0]
    model_grouped = model_df.groupby(exam_col)
    true_grouped = true_df.groupby(exam_col)
    
    # Find all exam numbers that are present in both model and true data
    all_exam_numbers = set(model_grouped.groups.keys()) & set(true_grouped.groups.keys())
    if not all_exam_numbers:
        print("No matching exam numbers found for Levenshtein evaluation.")
        return None

    # Collect all rows for matched exam numbers
    matched_model_rows = []
    matched_true_rows = []
    counter_hallucinations = 0
    for exam in sorted(all_exam_numbers):
        model_rows = model_grouped.get_group(exam)
        true_rows = true_grouped.get_group(exam)
        counter_hallucinations += abs(len(model_rows) - len(true_rows))
        # If there are multiple rows per exam, align by index
        min_len = min(len(model_rows), len(true_rows))
        for i in range(min_len):
            matched_model_rows.append(model_rows.iloc[i])
            matched_true_rows.append(true_rows.iloc[i])

    if not matched_model_rows or not matched_true_rows:
        print("No matching rows found for Levenshtein evaluation.")
        return None

    matched_model_df = pd.DataFrame(matched_model_rows)
    matched_true_df = pd.DataFrame(matched_true_rows)

    # Column-wise Levenshtein (average per column)
    col_similarities = {}
    if print_results :
        print("\nAverage ANLS per column (mutations):")
    for col in matched_true_df.columns:
        if col not in matched_model_df.columns:
            print(f"  {col}: column missing in model results")
            col_similarities[col] = None
            continue
        m_vals = matched_model_df[col]
        t_vals = matched_true_df[col]

        similarities = [normalized_levenshtein_similarity(normalize_string(m), normalize_string(t)) for m, t in zip(m_vals, t_vals)]
        avg_col_sim = (sum(similarities) / len(similarities)) * (1 - counter_hallucinations/max(len(model_df),len(true_df))) if similarities else None
        # avg_col_sim = (sum(similarities) / len(similarities))*(1 - (abs(len(model_df)-len(true_df))/max(len(model_df),len(true_df)))) if similarities else None
        if print_results:
            print(f"  {col}: {avg_col_sim:.3f}")
        col_similarities[col] = avg_col_sim #here should multiply by (1- abs(num_mutations - 24)/max(24, num_mutations)) if num_mutations != 0 else 0
    return col_similarities

def evaluate_one_file(exam_number, model_meta_path, model_mut_path, true_meta_path, true_mut_path):
    """
    Evaluate both metadata and mutation extraction for a single file.
    """
    #search for the exam number in the true data
    true_meta_df = pd.read_csv(true_meta_path)
    true_mut_df = pd.read_csv(true_mut_path)

    if exam_number not in true_meta_df[true_meta_df.columns[0]].values:
        print(f"Exam number {exam_number} not found in true metadata.")
        return
    if exam_number not in true_mut_df[true_mut_df.columns[0]].values:
        print(f"Exam number {exam_number} not found in true mutations.")
        return
    #extract the rows for the exam number
    true_meta_row = true_meta_df[true_meta_df[true_meta_df.columns[0]] == exam_number]
    true_mut_rows = true_mut_df[true_mut_df[true_mut_df.columns[0]] == exam_number]
    #search for the exam number in the model data
    model_meta_df = pd.read_excel(model_meta_path)
    model_mut_df = pd.read_excel(model_mut_path)

    if exam_number not in model_meta_df[model_meta_df.columns[0]].values:
        print(f"Exam number {exam_number} not found in model metadata.")
        return
    if exam_number not in model_mut_df[model_mut_df.columns[0]].values:
        print(f"Exam number {exam_number} not found in model mutations.")
        return
    #extract the rows for the exam number
    model_meta_row = model_meta_df[model_meta_df[model_meta_df.columns[0]] == exam_number]
    model_mut_rows = model_mut_df[model_mut_df[model_mut_df.columns[0]] == exam_number]
 
    # Evaluate metadata
    print(f"\nMetadata for exam {exam_number}:")
    print(f"    Model:\n{model_meta_row}\n   True:\n{true_meta_row}")
    # Evaluate mutations
    print(f"\nMutations for exam {exam_number}:")
    print(f"    Model:\n{model_mut_rows}\n   True:\n{true_mut_rows}")
    

def calculate_time_stats(time_data_path):
    """
    Calculate and print statistics from a list of time durations.
    """
    df = pd.read_excel(time_data_path)
    # calculate average, standard deviation, min, max for columns 'time_meta_data' and 'Time_Mutation_data'
    if 'Time_Metadata' in df.columns:
        avg_meta = df['Time_Metadata'].mean()
        std_meta = df['Time_Metadata'].std()
        min_meta = df['Time_Metadata'].min()
        max_meta = df['Time_Metadata'].max()
        print(f"    Metadata processing times - Avg: {avg_meta:.2f}s, Std: {std_meta:.2f}s, Min: {min_meta:.2f}s, Max: {max_meta:.2f}s")
    if 'Time_Mutation' in df.columns:
        avg_mut = df['Time_Mutation'].mean()
        std_mut = df['Time_Mutation'].std()
        min_mut = df['Time_Mutation'].min()
        max_mut = df['Time_Mutation'].max()
        print(f"    Mutation processing times - Avg: {avg_mut:.2f}s, Std: {std_mut:.2f}s, Min: {min_mut:.2f}s, Max: {max_mut:.2f}s")

if __name__ == "__main__":

    # model_excel_path = 'data/verified_metadata.xlsx'
    # true_csv_path_meta = 'data/verified_data/verified_metadata.csv'
    # true_csv_path_mut = 'data/verified_data/verified_mutations_without_none.csv'
    true_csv_path_meta = 'data/verified_data/verified_metadata_clp_ost_chp_ex.csv'
    true_csv_path_mut = 'data/verified_data/verified_mutations_clp_ost_chp_ex.csv'
    print_res = True

    # model_excel_path_meta = 'out/hand_pdf_parser_metadata.xlsx'
    # model_excel_path_mut = 'out/hand_pdf_parser_mutation.xlsx'
    # print("---- Evaluating rule based results ----")
    # evaluate_model_metadata(model_excel_path_meta, true_csv_path_meta)
    # evaluate_metadata_levenshtein(model_excel_path_meta, true_csv_path_meta)
    # evaluate_model_mutations(model_excel_path_mut, true_csv_path_mut)
    # evaluate_mutations_levenshtein(model_excel_path_mut, true_csv_path_mut)

    # model_excel_path_meta = 'out/metadata_camembert.xlsx'
    # print("---- Evaluating Camembert results ----")
    # evaluate_model_metadata(model_excel_path_meta, true_csv_path_meta)
    # evaluate_metadata_levenshtein(model_excel_path_meta, true_csv_path_meta)
    
    # ["gemma3_4B", "gemma3_1B", "llama32_1B", "llama32_3B", "qwen_3B" ]
    # ["gpt4o", "gpto3", "gemini", "gemma3_4B", "grok"] final
    # model = "gemma3_4B"  # Change this to the model you want to evaluate
    # prompt = "final4"
    # model_excel_path_meta = f'prompt_engineering/final_prompt_results/metadata_{model}_{prompt}.xlsx'
    # model_excel_path_mut = f'prompt_engineering/final_prompt_results/mutation_{model}_{prompt}.xlsx'

    short_model_name = "gemma3_4B_clp_ost_chp_ex"
    model_excel_path_meta = f'out/metadata_{short_model_name}.xlsx'
    model_excel_path_mut = f'out/mutation_{short_model_name}.xlsx'

    print("---- Evaluating gemma 3 4B results ----")
    evaluate_model_metadata(model_excel_path_meta, true_csv_path_meta)
    scores_leven_meta = evaluate_metadata_levenshtein(model_excel_path_meta, true_csv_path_meta, print_results=print_res)
    print(f"Average levenshtein similarity for metadata: {sum(scores_leven_meta.values()) / len(scores_leven_meta)}")

    evaluate_model_mutations(model_excel_path_mut, true_csv_path_mut)
    scores_leven_mut = evaluate_mutations_levenshtein(model_excel_path_mut, true_csv_path_mut, print_results=print_res)
    print(f"Average levenshtein similarity for mutations: {(sum(scores_leven_mut.values())/len(scores_leven_mut))}")

    #evaluate a specific exam number
    # evaluate_one_file('25EM00024', model_excel_path_meta, model_excel_path_mut, true_csv_path_meta, true_csv_path_mut)

    # Calculate time statistics
    time_data_path = f'out/times_{short_model_name}.xlsx'
    print(f'\nTime statistics for {short_model_name} model:')
    calculate_time_stats(time_data_path)