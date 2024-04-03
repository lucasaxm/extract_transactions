import sys
import fitz  # PyMuPDF
import pandas as pd
import re
import csv
import matplotlib.pyplot as plt

# Function to consolidate similar establishments
def consolidate_establishments(name):
    name = name.lower()
    first_word = name.split()[0]
    if first_word in ['supermago', 'bourbon', 'supermagoporto', 'zaffari']:
        return 'mercado'
    elif name.startswith('ifd') or first_word == 'ifood':
        return 'ifood'
    elif name.startswith('mercadolivre'):
        return 'mercadolivre'
    elif ('poa jardim b' in name) or ('grupolan' in name):
        return 'gasolina'
    elif name.startswith('raia') or first_word == 'raia':
        return 'farmacia'
    return name.lower().split()[0]

def extract_and_filter_transactions(pdf_paths):
    transactions = []
    installments_seen = {}

    # Regex pattern for transactions
    pattern = re.compile(r'(\d{2}/\d{2})\s+([^\r\n(]+?)(?:\s*(\d{2}/\d{2}))?\s+(\d+,\d{2})\r?\n', re.DOTALL)
    
    for pdf_path in pdf_paths:
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text("text")
            for date, establishment, installment_info, amount in pattern.findall(text):
                establishment_clean = ' '.join(establishment.split('\n')).strip()

                # Check if the establishment field ends with a dash which indicates a negative amount
                if establishment_clean.endswith('-'):
                    establishment_clean = establishment_clean[:-1].strip()
                    amount = f'-{amount}'

                key = re.sub(r'\s+\d{2}/\d{2}$', '', establishment_clean)

                if installment_info:
                    current_installment = int(installment_info.split('/')[0])
                    if key in installments_seen and current_installment >= installments_seen[key]:
                        continue
                    installments_seen[key] = current_installment

                transactions.append([date, key, amount])
        doc.close()
    print(f"Installments:\n{installments_seen}")
    return transactions

if __name__ == "__main__":
    # Accept multiple PDF files as command-line arguments
    pdf_file_paths = sys.argv[1:]  # Skip the script name itself

    # Check if at least one PDF file is provided
    if not pdf_file_paths:
        print("Usage: python extract_transactions.py file1.pdf file2.pdf ...")
        sys.exit(1)

    csv_output_path = pdf_file_paths[0].replace(".pdf", ".csv")
    jpg_output_path = pdf_file_paths[0].replace(".pdf", ".jpg")

    # Extract and filter the transactions
    transactions = extract_and_filter_transactions(pdf_file_paths)

    # Write the transactions to a CSV file
    with open(csv_output_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['data', 'estabelecimento', 'valor'])
        writer.writerows(transactions)

    print(f"Transactions have been extracted and saved to {csv_output_path}")

    transactions = pd.read_csv(csv_output_path)

    transactions['valor'] = transactions['valor'].str.replace(',', '.').astype(float)

    # Apply the function to the 'estabelecimento' column
    transactions['estabelecimento'] = transactions['estabelecimento'].apply(consolidate_establishments)

    # Group by 'estabelecimento' and sum the 'valor'
    grouped_transactions = transactions.groupby('estabelecimento')['valor'].sum().reset_index()

    # Sort by 'valor' to find the top spendings
    top_spendings = grouped_transactions.sort_values(by='valor', ascending=False).head(10)

    print(top_spendings)

    # Creating the bar plot with value labels
    plt.figure(figsize=(10, 6))
    bars = plt.barh(top_spendings['estabelecimento'], top_spendings['valor'], color='skyblue')
    plt.xlabel('Valor em Reais (R$)')
    plt.ylabel('Estabelecimento')
    plt.title('Top 10 Maiores Gastos Consolidados')

    # Invert y-axis to display the largest value on top
    plt.gca().invert_yaxis()

    # Adding the value labels to each bar
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 10, bar.get_y() + bar.get_height()/2, 
                f'R$ {width:.2f}', 
                va='center')

    plt.savefig(jpg_output_path)
