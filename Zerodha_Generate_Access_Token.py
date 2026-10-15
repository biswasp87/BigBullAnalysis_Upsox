
from kiteconnect import KiteConnect
import pyotp
import requests
from urllib.parse import urlparse, parse_qs
import re
import os
import sys
import json
import datetime
import time
from google.cloud import storage

def broker_login():
    """
    Function enables logging into broker api account.
    :return:
    Kite Object, in case the login was successful
    None, if the login fails
    """
    user_id = os.environ['ZERODHA_USER_ID']
    password = os.environ['ZERODHA_PASSWORD']
    totp_key = os.environ['ZERODHA_TOTP_KEY']
    api_key = os.environ['ZERODHA_API_KEY']
    app_secret = os.environ['ZERODHA_APP_SECRET']
    # Download Broker Login credentials from Broker app config file
    session = requests.Session()
    login_payload = {
        "user_id": user_id,
        "password": password,
    }
    response = session.post("https://kite.zerodha.com/api/login", login_payload)
    login_response = response.json()
    if login_response['status'] != 'success':
        print('Broker Login : Login failed with message : %s', login_response['message'])
        return None
    totp = pyotp.TOTP(totp_key).now()
    twofa_payload = {
        "user_id": user_id,
                          "request_id": login_response["data"]["request_id"],
        "twofa_value": totp,
        "twofa_type": "totp",
        "skip_session": True,
    }
    response = session.post("https://kite.zerodha.com/api/twofa", twofa_payload)
    totp_response = response.json()
    if totp_response['status'] != 'success':
        print('Broker Login : Login failed with message : %s', totp_response['message'])
        return None
    kite = KiteConnect(api_key=api_key)
    try:
        # Extracting query parameters from redirect URL
        response = session.get(kite.login_url())
        parse_result = urlparse(response.url)
        query_parms = parse_qs(parse_result.query)
    except Exception as e:
        # Extracting query parameters from error message in case of error
        pattern = r"request_token=[A-Za-z0-9]+"
        # Extracting request token
        query_parms = parse_qs(re.findall(pattern, e.__str__())[0])
    try:
        request_token = query_parms["request_token"][0]
        data = kite.generate_session(request_token=request_token, api_secret=app_secret)
        access_token = data["access_token"]
        print(access_token)
        # Save access token in the folder AccessToken
        os.makedirs(f"AccessToken", exist_ok=True)
        # Save access token to Google Cloud Storage
        save_to_gcs(access_token) # Call the Storage function with the access token value input
        with open(f"AccessToken/{datetime.datetime.now().date()}.json", "w") as f:
            json.dump(access_token, f)
        print("Access Token Saved")

        # Generate Session
        kite.set_access_token(access_token)
    except Exception as e:
        print('Broker Login 2 : Login failed. Check Credentials and try again')
        return None
    return kite

def save_to_gcs(access_token):
    """Saves the access token to a Google Cloud Storage bucket."""
    # Generate standard filename based on current date
    filename = f"{datetime.datetime.now().date()}.json"
    bucket_name = "bba_access_token"
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        # Defines the path inside the bucket
        blob = bucket.blob(f"zerodha/{filename}")

        token_data = json.dumps({"access_token": access_token}, indent=4)
        blob.upload_from_string(token_data, content_type="application/json")
        print(
            f"✅ Access Token saved to GCS bucket '{bucket_name}' at AccessToken/{filename}"
        )
    except Exception as e:
        print(f"❌ Failed to save to GCS: {e}")


if __name__ == "__main__":
    kite = broker_login()
    if kite is not None:
        print(kite.profile())
    else:
        print("Broker Login failed")
