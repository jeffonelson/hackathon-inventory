import io
import json
import logging
import os
import time

import pandas as pd
import streamlit as st
from PIL import Image

import config
import object_detection
import gcs_utils
import price_estimation
from google.cloud import bigquery

PROJECT_ID = config.PROJECT_ID
DATASET_ID = config.DATASET_ID
TABLE_ID = config.TABLE_ID

st.set_page_config(page_title="Video Inventory App", page_icon=":camera:", layout="wide")

st.title("Your Friendly Inventory Application")
st.markdown("Upload images or video to generate an inventory.")

if "inventory_df" not in st.session_state:
    st.session_state.inventory_df = pd.DataFrame(columns=['item', 'brand', 'model', 'quantity', 'description', 'timestamp'])

def process_media(uploaded_file, media_type):
    try:
        file_bytes = uploaded_file.read()
        file_extension = os.path.splitext(uploaded_file.name)[1]
        if media_type == "video":
            mime_type = "video/mp4" # Can update for different video mime_types
            spinner_message = "Uploading video to Google Cloud Storage..."
        elif media_type == "image":
            if file_extension:
                mime_type = f"image/{file_extension[1:]}"
            else:
                mime_type = "application/octet-stream"  # Default if no extension
                st.warning("File has no extension, using default MIME type.") # warn user
            spinner_message = "Uploading image to Google Cloud Storage..."
        else:
            return "Invalid media type", None, None

        with st.spinner(spinner_message):  # Use dynamic spinner message
            gcs_result, gcs_uri = gcs_utils.upload_file_to_gcs(
                file_bytes, uploaded_file.name
            )

        if "Error" in gcs_result:
            st.error(gcs_result)  # Display the specific GCS error
            logging.error(f"GCS Upload Error: {gcs_result}") #log error
            return None, None, None


        st.success(f"{media_type.capitalize()} uploaded successfully!")

        if gcs_uri: #check if upload is succesful

            with st.spinner(f"Analyzing {media_type} with Gemini..."):
                gemini_response = object_detection.analyze_media_with_gemini(gcs_uri, mime_type)



            if gemini_response:
                st.success("Object detection completed!")
                return gcs_result, gcs_uri, gemini_response # Return response and URI
            else:
                st.error("Gemini analysis failed. Please check the logs for details.")
                logging.error("Gemini analysis failed")
                return None, None, None # Return None if Gemini fails

        return None, None, None  # Return None if something went wrong



    except Exception as e:
        logging.exception(f"Error in process_media: {e}")
        st.error(f"An error occurred during media processing: {e}")
        return None, None, None

def write_to_bigquery(df):
    """Writes a Pandas DataFrame to BigQuery."""
    try:
        # Construct the full BigQuery table ID
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

        # Create a BigQuery client
        client = bigquery.Client()

        # Write the df to BigQuery
        job_config = bigquery.LoadJobConfig(
            autodetect=True,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()  # Wait for the job to complete

        st.success("Data written to database successfully!")

    except Exception as e:
        st.error(f"Error writing to BigQuery: {e}")
        logging.exception("Error writing to BigQuery")


col1, col2 = st.columns([1, 2])

with col1:
    media_type = st.radio("Choose media type:", ["image", "video"])
    uploaded_file = st.file_uploader(f"Choose a {media_type}...", type=["mp4", "mov", "avi"] if media_type == "video" else ["jpg", "png", "jpeg"])
    if uploaded_file is not None: # Moved media display inside col1
        if media_type == "image":
            st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
        elif media_type == "video":
            st.video(uploaded_file, format="video/mp4")  # or the detected format

with col2:
    if uploaded_file is not None:
        gcs_result, gcs_uri, gemini_response = process_media(uploaded_file, media_type)

        if gcs_result and gcs_uri and gemini_response:  
            try:
                gemini_data = json.loads(gemini_response)
                if isinstance(gemini_data, list) and all(isinstance(item, dict) for item in gemini_data):
                    df = pd.DataFrame(gemini_data)

                    # Add URI to the DataFrame
                    df['uri'] = gcs_uri
                    
                    # Reorder fields
                    df = df[['item', 'brand', 'quantity', 'timestamp', 'description', 'uri']]
                    
                    # Fill in unknown Brands with space as Nulls throwing errors
                    df['brand'] = df['brand'].fillna(' ')

                    # Price estimation moved outside the loop
                    with st.spinner('Estimating prices...'):
                        prices = [price_estimation.get_estimated_price(item, brand, description) or 0 for item, brand, description in zip(df['item'], df['brand'], df['description'])]
                    st.success("Price estimates completed!")
                    
                    df['price'] = prices
                    df = df[['item', 'brand', 'quantity', 'price', 'timestamp', 'description', 'uri']]
                    pd.options.display.float_format = '{:.2f}'.format


                    # Write the dataframe to BQ
                    write_to_bigquery(df) 

                    st.dataframe(df.style.set_properties(**{'width':'300px', 'text-align':'left'}))

                else:
                    st.error("Invalid Gemini response format. The JSON must be a list of dictionaries.")
            except json.JSONDecodeError as e:
                st.error(f"Error decoding Gemini response (invalid JSON): {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
    else:
        st.info("Use the menu on the left to upload a video!")
        st.image("https://cashflowinventory.com/blog/wp-content/uploads/2023/02/inventory-analysis.webp", use_column_width=True)