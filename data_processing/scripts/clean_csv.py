import re

def clean(input_datei):




        # Open the file in read mode and read all lines
        with open(input_datei, mode='r', encoding='utf-8') as infile:
            lines = infile.readlines()

        # Function to replace commas with periods only in numeric values
        def replace_commas_in_numbers(line):
            # Regex to find numeric values with commas as decimal separator
            return re.sub(r'(\d),(\d)', r'\1.\2', line)

        # Replace commas with periods in each line
        lines_ersetzt = [replace_commas_in_numbers(line) for line in lines]

        # Overwrite the same file with the modified content
        with open(input_datei, mode='w', encoding='utf-8') as outfile:
            outfile.writelines(lines_ersetzt)

        print(f"The file '{input_datei}' has been successfully updated.")


