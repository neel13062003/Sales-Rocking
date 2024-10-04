import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st
import requests
from PIL import Image
import tempfile

# Convert Google Drive link to direct URL
def convert_google_drive_link_to_direct_url(link):
    if 'drive.google.com' in link:
        file_id = link.split('/')[-2]
        return f"https://drive.google.com/uc?id={file_id}"
    return link

# Google Sheets connection setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]


creds_dict = {
    "type": st.secrets["gcp_service_account"]["type"],
    "project_id": st.secrets["gcp_service_account"]["project_id"],
    "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
    "private_key": st.secrets["gcp_service_account"]["private_key"].replace('\\n', '\n'),  # Handle newline characters
    "client_email": st.secrets["gcp_service_account"]["client_email"],
    "client_id": st.secrets["gcp_service_account"]["client_id"],
    "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
    "token_uri": st.secrets["gcp_service_account"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
}

# creds = ServiceAccountCredentials.from_json_keyfile_name(r"../ENV/key.json", scope)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)


client = gspread.authorize(creds)

# Get data from Google Sheets
def get_sheet_data(spreadsheet_id, worksheet_index):
    sheet = client.open(spreadsheet_id)
    worksheet = sheet.worksheet(worksheet_index)
    data = worksheet.get_all_values()
    header_row = data[0]
    data_rows = data[1:]
    df = pd.DataFrame(data_rows, columns=header_row)
    return df

spreadsheet_id = 'service_sheet'
worksheet_index = 'Sheet1'
stored_df_test_service = get_sheet_data(spreadsheet_id, worksheet_index)

# Process DataFrame
stored_df_test_service['Days left'] = pd.to_numeric(stored_df_test_service['Days left'], errors='coerce')
stored_df_test_service = stored_df_test_service[stored_df_test_service['Status'] == "Live"]
stored_df_test_service["COMPANY TYPE"] = stored_df_test_service["COMPANY TYPE"].str.split(',').apply(lambda x: [i.strip() for i in x])
stored_df_test_service["SECTOR"] = stored_df_test_service["SECTOR"].str.split(',').apply(lambda x: [i.strip() for i in x])
stored_df_test_service["Scheme"] = stored_df_test_service["Scheme"].str.strip()

# Unique values for dropdowns
unique_values = pd.Series([item for sublist in stored_df_test_service["COMPANY TYPE"] for item in sublist]).unique().tolist()
unique_values_sector = pd.Series([item for sublist in stored_df_test_service["SECTOR"] for item in sublist]).unique().tolist()
criteria3_options = stored_df_test_service.Scheme.values.tolist()

# Filter DataFrame
def filter_dataframe(selected_value, sector):
    filtered_df = stored_df_test_service[["SR. NO.", "Scheme", "Benefits", "SECTOR", "COMPANY TYPE", "Deadline", "Days left"]]
    if selected_value != 'ALL':
        filtered_df = filtered_df[(filtered_df["COMPANY TYPE"].apply(lambda x: selected_value in x)) | 
                                  (filtered_df["COMPANY TYPE"].apply(lambda x: 'ALL' in x))]
    if sector != 'All Sector':
        filtered_df = filtered_df[(filtered_df["SECTOR"].apply(lambda x: sector in x)) | 
                                  (filtered_df["SECTOR"].apply(lambda x: 'All Sector' in x))]
    return filtered_df.sort_values(by='Days left', ascending=True)

# Search Scheme
def search_scheme(keyword):
    search_result_df = stored_df_test_service[stored_df_test_service['Scheme'] == keyword]
    if not search_result_df.empty:
        pamphlet_link = search_result_df.iloc[0]['Pamphlet link']
        direct_link = convert_google_drive_link_to_direct_url(pamphlet_link)
    else:
        search_result_df = pd.DataFrame()
        direct_link = None
    return search_result_df, direct_link

# Streamlit app layout
st.title("Service Scheme Filter and Search")

# Filters
selected_value = st.selectbox("Company Type", options=['ALL'] + unique_values, index=0)
sector = st.selectbox("Sector", options=['All Sector'] + unique_values_sector, index=0)

# Display filtered data
filtered_df = filter_dataframe(selected_value, sector)
st.write("Filtered DataFrame:")
st.dataframe(filtered_df)

# Search functionality
search_keyword = st.selectbox("Search Scheme", options=criteria3_options)
if st.button("Search"):
    search_result, image_url = search_scheme(search_keyword)
    if not search_result.empty:
        st.write("Search Results:")
        st.dataframe(search_result)
        if image_url:
            st.write("Pamphlet Image:")
            image = Image.open(requests.get(image_url, stream=True).raw)
            st.image(image)
    else:
        st.write("No results found.")
