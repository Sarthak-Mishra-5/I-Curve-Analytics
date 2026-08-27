import requests 
import pandas as pd

from config import get_auth_headers

# Define the API endpoint
url = "https://qh-api.corp.hertshtengroup.com/api/v2/ohlc"
OHLC_API_RATE_LIMIT_PER_MINUTE = 10
OHLC_API_MAX_ROWS_PER_REQUEST = 10000

outrights = {
    # SOFR
    "SR3 Jun26": "SRAM26",
    "SR3 Sep26": "SRAU26",
    "SR3 Dec26": "SRAZ26",
    "SR3 Mar27": "SRAH27",
    "SR3 Jun27": "SRAM27",
    "SR3 Sep27": "SRAU27",
    "SR3 Dec27": "SRAZ27",
    "SR3 Mar28": "SRAH28",
    "SR3 Jun28": "SRAM28",
    "SR3 Sep28": "SRAU28",
    "SR3 Dec28": "SRAZ28",
    "SR3 Mar29": "SRAH29",
    "SR3 Jun29": "SRAM29",
    "SR3 Sep29": "SRAU29",
    "SR3 Dec29": "SRAZ29",
    "SR3 Mar30": "SRAH30",
    "SR3 Jun30": "SRAM30",
    "SR3 Sep30": "SRAU30",
    "SR3 Dec30": "SRAZ30",

    # SONIA
    "SO3 Jun26": "SONM26",
    "SO3 Sep26": "SONU26",
    "SO3 Dec26": "SONZ26",
    "SO3 Mar27": "SONH27",
    "SO3 Jun27": "SONM27",
    "SO3 Sep27": "SONU27",
    "SO3 Dec27": "SONZ27",
    "SO3 Mar28": "SONH28",
    "SO3 Jun28": "SONM28",
    "SO3 Sep28": "SONU28",
    "SO3 Dec28": "SONZ28",
    "SO3 Mar29": "SONH29",
    "SO3 Jun29": "SONM29",
    "SO3 Sep29": "SONU29",
    "SO3 Dec29": "SONZ29",
    "SO3 Mar30": "SONH30",
    "SO3 Jun30": "SONM30",
    "SO3 Sep30": "SONU30",
    "SO3 Dec30": "SONZ30",

    # EURIBOR
    "I Sep26": "ERU26",
    "I Dec26": "ERZ26",
    "I Mar27": "ERH27",
    "I Jun27": "ERM27",
    "I Sep27": "ERU27",
    "I Dec27": "ERZ27",
    "I Mar28": "ERH28",
    "I Jun28": "ERM28",
    "I Sep28": "ERU28",
    "I Dec28": "ERZ28",
    "I Mar29": "ERH29",
    "I Jun29": "ERM29",
    "I Sep29": "ERU29",
    "I Dec29": "ERZ29",
    "I Mar30": "ERH30",
    "I Jun30": "ERM30",
    "I Sep30": "ERU30",
    "I Dec30": "ERZ30",

    # SARON
    "SA3 Jun26": "FSRM26",
    "SA3 Sep26": "FSRU26",
    "SA3 Dec26": "FSRZ26",
    "SA3 Mar27": "FSRH27",
    "SA3 Jun27": "FSRM27",
    "SA3 Sep27": "FSRU27",
    "SA3 Dec27": "FSRZ27",
    "SA3 Mar28": "FSRH28",
    "SA3 Jun28": "FSRM28",
    "SA3 Sep28": "FSRU28",
    "SA3 Dec28": "FSRZ28",
    "SA3 Mar29": "FSRH29",
    "SA3 Jun29": "FSRM29",
    "SA3 Sep29": "FSRU29",
    "SA3 Dec29": "FSRZ29",
    "SA3 Mar30": "FSRH30",
    "SA3 Jun30": "FSRM30",
    "SA3 Sep30": "FSRU30",
    "SA3 Dec30": "FSRZ30",
}

# Set the request parameters.
# Leave optional parameters as None when they are not needed.
params = {
    "instruments": "SRAU27,SONU27,ERU27,FSRU27",   # Comma-separated QH Codes (up to 50)
    "hg_instrument_ids": None,   # Comma-separated HG instrument IDs (up to 50)
    "interval": "5M",           # Required: 1M, 5M, 1H, or 1D
    "count": "2500",               # Candles per instrument (default: 50)
    "end": None,                # End timestamp (Unix seconds)
    "start": None,              # Start timestamp (Unix seconds)
    "extraFields": "buyvolume,sellvolume",       # "buyvolume", "sellvolume", or both
}

# Do not send parameters that have not been set.
params = {key: value for key, value in params.items() if value is not None}

headers = get_auth_headers()

# Make the request
response = requests.get(url,
                        headers=headers,
                        params=params,
                        verify=False,)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    data = response.json()
    #fetch_data=data.get("SRAH25_03Dec24")
    #columns=fetch_data.get("columns")
    #Data= fetch_data.get("DATA")
    #print(pd.DataFrame(Data,columns=columns))
    print("Data Retrieved:", data)
else:
        # Debugging the request and response
    print("Request URL:", response.url)
    print("Response Status Code:", response.status_code)
    print("Response Text:", response.text)
