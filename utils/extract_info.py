import re
from datetime import datetime

#Its function to extract date,time and title from the text using LLM
#For now, here we are using regex for simplicity
def extract_info(text):
    text = text.lower()

    # ----- Extract time -----
    time_pattern = r"\b(\d{1,2}[:.]\d{2}\s*(am|pm)?)\b"
    time_match = re.search(time_pattern, text)
    task_time = time_match.group(1) if time_match else None

    # ----- Extract date -----
    date_pattern = r"\b(\d{2,4}-\d{1,2}-\d{1,2})\b"
    date_match = re.search(date_pattern, text)
    task_date = date_match.group(1) if date_match else None

    # If date missing → use today's date
    if not task_date:
        task_date = datetime.now().strftime("%Y-%m-%d")

    # If time missing → blank
    if not task_time:
        task_time = ""

    # Title → remove extracted date and time
    cleaned_title = text
    if date_match:
        cleaned_title = cleaned_title.replace(date_match.group(1), "")
    if time_match:
        cleaned_title = cleaned_title.replace(time_match.group(1), "")

    cleaned_title = cleaned_title.strip().capitalize()

    return cleaned_title, task_date, task_time
