import pandas as pd
from scipy.stats import ttest_rel
from tkinter import Tk, filedialog

def perform_paired_t_tests():
    # Open file dialog to select CSV file
    root = Tk()
    root.withdraw()  # Hide the root window
    csv_file = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])

    if not csv_file:
        raise ValueError("No file selected.")

    # Load the CSV file
    data = pd.read_csv(csv_file)

    # Ensure the necessary columns are present
    required_columns = ['Scenario', 'Total Damage', 'Participant']
    for col in required_columns:
        if col not in data.columns:
            raise ValueError(f"Missing required column: {col}")

    # Convert Total Damage to numeric
    data['Total Damage'] = pd.to_numeric(data['Total Damage'], errors='coerce')

    # Extract difficulty levels from the Scenario column
    difficulty_levels = ['E', 'M', 'H']

    # Perform paired t-tests for each difficulty level
    results = []
    for level in difficulty_levels:
        no_hap = data[data['Scenario'] == f"{level}, No"]['Total Damage']
        hap = data[data['Scenario'] == f"{level}, Hap"]['Total Damage']

        # Check if we have paired data
        if len(no_hap) != len(hap):
            raise ValueError(f"Unequal data for {level} level: No ({len(no_hap)}) vs Hap ({len(hap)})")

        t_stat, p_value = ttest_rel(no_hap, hap)
        results.append({
            'Difficulty': level,
            't-statistic': t_stat,
            'p-value': p_value
        })

    return results


# Run the analysis and print results in a nice format
results = perform_paired_t_tests()

# Convert results to a DataFrame for better formatting
results_df = pd.DataFrame(results)

# Print the results in a tabular format
print("\nPaired t-test Results:")
print(results_df.to_string(index=False, float_format="%.4f"))