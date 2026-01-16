"""
This script processes input Excel spreadsheet data and reorganizes it into a different structure
for easier analysis. It specifically handles headers divided into three parts and then
reformats the data accordingly.

Usage:
    python script_name.py --input_file input.xlsx --output_file output.xlsx

- Author: Paul Munn, Genomics Innovation Hub, Cornell University

- Version history:
- 09/14/2024: Original version
"""

import pandas as pd
import argparse


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Process keller CPET data and reformat.")
    parser.add_argument('--input_file', type=str,
                        default="2024-07-09 KELLER MAPMECFS Total sample_CPETonly_modified.xlsx",
                        help="Input Excel spreadsheet file name")
    parser.add_argument('--output_file', type=str, default="keller_data_table.xlsx",
                        help="Output Excel spreadsheet file name")
    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_args()
    print(f"Input file: {args.input_file}")
    print(f"Output file: {args.output_file}")

    # Read the input Excel file into a dataframe
    df = pd.read_excel(args.input_file)

    # Initialize a list to store the reformatted data
    data = []

    # Iterate over each row in the dataframe
    for _, row in df.iterrows():
        pub_id = row['pub id']

        # Split columns excluding 'enid_id' and 'pub id'
        for col in df.columns[2:]:
            parts = col.split('_')
            field_name = '_'.join(parts[:-2])
            Annot_1 = parts[-2]
            Timepoint = parts[-1]

            # Create a structured row for each combination
            data.append({
                "pub id": pub_id,
                "Timepoint": Timepoint,
                "Annot-1": Annot_1,
                field_name: row[col]
            })

    # Convert the list of dictionaries into a dataframe
    data_df = pd.DataFrame(data)

    # Pivot the dataframe to the desired format and fill NaNs with 'na'
    final_df = data_df.pivot_table(index=["pub id", "Timepoint", "Annot-1"],
                                   columns='field_name',
                                   values=list(set(data_df.columns) - {'pub id', 'Timepoint', 'Annot-1'}),
                                   aggfunc='first').reset_index().fillna('na')

    # Flatten the headers and reset columns
    final_df.columns = [col if isinstance(col, str) else col[1] for col in final_df.columns]

    # Save the final dataframe to an Excel file
    final_df.to_excel(args.output_file, index=False)


if __name__ == "__main__":
    main()
