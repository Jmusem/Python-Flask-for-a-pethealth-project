import requests
import base64
import datetime
import json
from flask import request

# M-Pesa API Credentials
CONSUMER_KEY = "Fqba1SNgArfzYF64qY2tzCUMsoNMYeW0TOrwGqhDoZ6bEqx0"
CONSUMER_SECRET = "ITmg99pbD0peUQ27PoMvQU6pFiwNg8OK7Pt86GvGgTRtU56WYIBawrABUPFiBbCb"
BUSINESS_SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
CALLBACK_URL = "https://your-ngrok-url.com/callback"  # Update with actual callback URL

# ✅ Generate M-Pesa Access Token
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    access_token = response.json().get("access_token")
    return access_token

# ✅ Send STK Push Request
def lipa_na_mpesa(phone_number, amount):
    access_token = get_access_token()
    if not access_token:
        return {"error": "Failed to get access token"}
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{BUSINESS_SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    payload = {
        "BusinessShortCode": BUSINESS_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": BUSINESS_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "PetHealth",
        "TransactionDesc": "Pet Health Payment"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# ✅ Handle M-Pesa Callback
def handle_mpesa_callback():
    data = request.get_json()
    print("M-Pesa Callback Data:", json.dumps(data, indent=4))
    
    if "Body" in data and "stkCallback" in data["Body"]:
        callback_data = data["Body"]["stkCallback"]
        if callback_data["ResultCode"] == 0:
            return {"message": "Payment successful"}
        else:
            return {"error": "Payment failed"}
    return {"error": "Invalid callback data"}
