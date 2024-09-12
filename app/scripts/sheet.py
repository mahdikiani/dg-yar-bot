import os
import json
from functools import lru_cache
from pathlib import Path

import gspread
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from gspread_dataframe import get_as_dataframe, set_with_dataframe

from server.config import Settings

@lru_cache
def get_sheet_data(spreadsheet_id="1sWOYcFiMFY0cxNBvK6Uc96exT7ZXhR5dpV6DnB1kcaQ"):
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://spreadsheets.google.com/feeds",
    ]
    # credentials = service_account.Credentials.from_service_account_file(
    #     base_dir / "secrets" / "snappshop-access.json", scopes=scopes
    # )
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(Settings.GOOGLE_SECRET), scopes=scopes
    )

    gc = gspread.authorize(credentials)

    wb = gc.open_by_key(spreadsheet_id)
    return wb


def g_credentials() -> service_account.Credentials:
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://spreadsheets.google.com/feeds",
    ]
    credentials = service_account.Credentials.from_service_account_file(
        Settings.base_dir / "scripts" / "dgyar-access.json", scopes=scopes
    )
    return credentials
    # credentials = service_account.Credentials.from_service_account_info(
    #     json.loads(Settings.GOOGLE_SECRET), scopes=scopes
    # )
    service = build("sheets", "v4", credentials=credentials)
    return service


def create_sheet():
    service = build("sheets", "v4", credentials=g_credentials())
    spreadsheet = {"properties": {"title": "Product Data"}}
    spreadsheet = (
        service.spreadsheets()
        .create(body=spreadsheet, fields="spreadsheetId")
        .execute()
    )

    spreadsheet_id = spreadsheet.get("spreadsheetId")

    print(f"Spreadsheet ID: {spreadsheet_id}")

    drive_service = build("drive", "v3", credentials=g_credentials())

    public_permissions = {
        "type": "anyone",  # Allows anyone with the link to access
        "role": "writer",  # or 'writer' if you want public edit access
    }
    drive_service.permissions().create(
        fileId=spreadsheet_id,
        body=public_permissions,
        fields="id",
    ).execute()

    permissions = {
        "type": "user",  # You can also set this to 'anyone' if you want public access
        "role": "writer",  # or 'reader'
        "emailAddress": "mahdikiany@gmail.com",
    }
    drive_service.permissions().create(
        fileId=spreadsheet_id,
        body=permissions,
        fields="id",
    ).execute()
    return spreadsheet

def df_to_gsheet(df, spreadsheet, worksheet_name="Sheet1"):
    client = gspread.authorize(g_credentials())
    spreadsheet_id = spreadsheet.get("spreadsheetId")
    spreadsheet = client.open_by_key(spreadsheet_id)

    # If the worksheet already exists, clear it, otherwise create a new one
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.clear()  # Clear the existing worksheet data
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=df.shape[0], cols=df.shape[1])

    # Convert the DataFrame to a list of lists for inserting into Google Sheets
    values = [df.columns.tolist()] + df.values.tolist()

    # Update the worksheet with the DataFrame data
    worksheet.update(values)


@lru_cache
def get_df(worksheet_name="Sheet1") -> pd.DataFrame:
    wb = get_sheet_data()
    sheet = wb.worksheet(worksheet_name)
    df = get_as_dataframe(sheet)
    return df


def update_sheet_row(index: int, new_data: dict, worksheet_name="Sheet1"):
    # Get the worksheet
    wb = get_sheet_data()
    sheet = wb.worksheet(worksheet_name)

    # Convert worksheet to dataframe
    df = get_as_dataframe(sheet)

    # Update the dataframe with new data
    for key, value in new_data.items():
        if key in df.columns:
            df.at[index, key] = value
        else:
            df[key] = pd.NA
            df.at[index, key] = value

    # Clear the worksheet and write the updated dataframe back
    sheet.clear()
    set_with_dataframe(sheet, df)

def get_sheet_url(sheet_id):
    if type(sheet_id) == dict:
        sheet_id = sheet_id.get("spreadsheetId")
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit?gid=0#gid=0"

if __name__ == "__main__":
    sheet = create_sheet()
    print(get_sheet_url(sheet.get("spreadsheetId")))

    data = {
        'Name': ['John', 'Jane', 'Tom'],
        'Age': [28, 22, 35],
        'City': ['New York', 'San Francisco', 'Los Angeles']
    }
    df = pd.DataFrame(data)
    
    df_to_gsheet(df, sheet)
