import pandas as pd
import streamlit as st
import requests
from io import BytesIO

# Function to load the main Excel file from GitHub using requests
@st.cache_data
def load_sku_database():
    # URL for the raw Excel file hosted on GitHub
    file_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRWRnc-4mxvJiCXQOVwgOIeoTSmX7OS37_J5OcYLMLRpEFURbOBUdo78WFCLUosWNwtXHm1rRvg3PkG/pubhtml"
    
    # Download the file using requests
    response = requests.get(file_url)
    
    if response.status_code == 200:
        # Read the content of the file into a BytesIO object
        file_content = BytesIO(response.content)
        # Load the Excel file from the BytesIO object
        xls = pd.ExcelFile(file_content, engine='openpyxl')
    else:
        raise Exception(f"Failed to download file. Status code: {response.status_code}")

    sku_lookup = {}
    all_descriptions = []
    
    # Iterate over all sheets in the Excel file
    for sheet in xls.sheet_names:
        try:
            # Read the 'SKU' and 'Description' columns
            df = pd.read_excel(xls, sheet_name=sheet, usecols=lambda x: x.lower() in ['sku', 'description'], engine='openpyxl')
            df = df.dropna(subset=['SKU', 'Description'])  # Remove rows with missing data
            sku_lookup.update(dict(zip(df['SKU'].astype(str), df['Description'].astype(str))))  # Update SKU lookup dictionary
            all_descriptions.append(df['Description'].astype(str))  # Collect descriptions for reverse search
        except Exception as e:
            st.error(f"Error reading sheet {sheet}: {e}")
            continue
    
    description_df = pd.concat(all_descriptions, ignore_index=True)
    return sku_lookup, description_df

def main():
    st.title("SKU Lookup App")
    st.write("Enter a punch or die SKU to get its description, upload a list of SKUs, or search descriptions by shape or dimension.")

    # Load SKU data from GitHub
    with st.spinner("Loading SKU data..."):
        sku_lookup, description_df = load_sku_database()

    # Single SKU lookup
    st.subheader("Single SKU Lookup")
    sku_input = st.text_input("Enter SKU:")
    if sku_input:
        description = sku_lookup.get(sku_input.strip(), "SKU not found.")
        st.markdown(f"**Description:** {description}")

    # Batch SKU lookup
    st.subheader("Batch SKU Lookup")
    batch_file = st.file_uploader("Upload Excel file with SKUs", type=["xlsx"], key="batch")

    if batch_file:
        try:
            batch_df = pd.read_excel(batch_file, engine='openpyxl')  # Specify engine for local files too

            sku_col = next((col for col in batch_df.columns if col.lower() == 'sku'), None)
            if sku_col is None:
                st.error("No 'SKU' column found in uploaded file.")
            else:
                batch_df['Description'] = batch_df[sku_col].astype(str).map(lambda x: sku_lookup.get(x.strip(), "SKU not found."))
                st.success("Batch lookup complete.")
                st.dataframe(batch_df)

                # Option to download the results
                st.download_button(
                    label="Download Results as Excel",
                    data=batch_df.to_excel(index=False, engine='openpyxl'),
                    file_name="sku_lookup_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"Error processing file: {e}")

    # Reverse lookup
    st.subheader("Reverse Lookup: Search Descriptions")
    search_term = st.text_input("Enter keyword or dimension (e.g., '1/2', 'Hex', 'Rectangle punch'):", key="reverse")
    if search_term:
        results = description_df[description_df.str.contains(search_term, case=False, na=False)]
        if not results.empty:
            st.write(f"Found {len(results)} matching descriptions:")
            st.dataframe(results.reset_index(drop=True))
        else:
            st.write("No matching descriptions found.")

if __name__ == '__main__':
    main()
