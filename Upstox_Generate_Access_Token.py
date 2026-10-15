import datetime
import json
import os
import sys
from google.cloud import storage
from upstox_totp import UpstoxTOTP

#Hi

def save_to_local(access_token, filename):
    """Saves the access token to the local machine."""
    try:
        os.makedirs("AccessToken", exist_ok=True)
        filepath = os.path.join("AccessToken", filename)
        with open(filepath, "w") as f:
            json.dump({"access_token": access_token}, f, indent=4)
        print(f"✅ Access Token saved locally to {filepath}")
    except Exception as e:
        print(f"❌ Failed to save locally: {e}")


def save_to_gcs(access_token, filename, bucket_name):
    """Saves the access token to a Google Cloud Storage bucket."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        # Defines the path inside the bucket
        blob = bucket.blob(f"upstox/{filename}")

        token_data = json.dumps({"access_token": access_token}, indent=4)
        blob.upload_from_string(token_data, content_type="application/json")
        print(
            f"✅ Access Token saved to GCS bucket '{bucket_name}' at AccessToken/{filename}"
        )
    except Exception as e:
        print(f"❌ Failed to save to GCS: {e}")


def auto_login(storage_mode="local", gcs_bucket_name=None):
    """Starts headless login and saves the token based on storage_mode.

    Parameters:
    - storage_mode: 'local', 'gcs', or 'both'
    - gcs_bucket_name: Name of the Google Cloud Storage bucket (required if mode
      is 'gcs' or 'both')
    """
    print("Starting headless login...")
    # Automatically loads credentials from your .env file
    upx = UpstoxTOTP()

    try:
        response = upx.app_token.get_access_token()
        if response.success:
            print("✅ Success! Token generated.")
            access_token = response.data.access_token
            print(f"Access Token: {access_token}")

            # Generate standard filename based on current date
            filename = f"{datetime.datetime.now().date()}.json"

            # Handle storage options
            if storage_mode in ["local", "both"]:
                save_to_local(access_token, filename)

            if storage_mode in ["gcs", "both"]:
                if not gcs_bucket_name:
                    print(
                        "⚠️ GCS bucket name not provided. Skipping GCS upload."
                    )
                else:
                    save_to_gcs(access_token, filename, gcs_bucket_name)

            return access_token
        else:
            print(f"❌ Failed: {response.error}")

    except Exception as e:
        print(f"Error during login: {e}")


if __name__ == "__main__":
    # --- CONFIGURATION ---
    # Options: "local" | "gcs" | "both"
    STORAGE_MODE = "both"
    # Replace with your actual GCS bucket name if using "gcs" or "both"
    GCS_BUCKET_NAME = "bba_access_token"
    # ---------------------

    token = auto_login(storage_mode=STORAGE_MODE, gcs_bucket_name=GCS_BUCKET_NAME)