# import re
# from datetime import datetime

# #Its function to extract date,time and title from the text using LLM
# #For now, here we are using regex for simplicity
# def extract_info(text):
#     text = text.lower()

#     # ----- Extract time -----
#     time_pattern = r"\b(\d{1,2}[:.]\d{2}\s*(am|pm)?)\b"
#     time_match = re.search(time_pattern, text)
#     task_time = time_match.group(1) if time_match else None

#     # ----- Extract date -----
#     date_pattern = r"\b(\d{2,4}-\d{1,2}-\d{1,2})\b"
#     date_match = re.search(date_pattern, text)
#     task_date = date_match.group(1) if date_match else None

#     # If date missing → use today's date
#     if not task_date:
#         task_date = datetime.now().strftime("%Y-%m-%d")

#     # If time missing → blank
#     if not task_time:
#         task_time = ""

#     # Title → remove extracted date and time
#     cleaned_title = text
#     if date_match:
#         cleaned_title = cleaned_title.replace(date_match.group(1), "")
#     if time_match:
#         cleaned_title = cleaned_title.replace(time_match.group(1), "")

#     cleaned_title = cleaned_title.strip().capitalize()

#     return cleaned_title, task_date, task_time

# ----------------- Update Above Function Zaid -----------------------------

import re
from datetime import datetime, timedelta


def get_natural_date(text):
    """Convert natural language date to YYYY-MM-DD format"""
    text = text.lower().strip()
    today = datetime.now().date()

    # Today / Tomorrow / Day after tomorrow
    if "day after tomorrow" in text:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")
    if "tomorrow" in text:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in text:
        return today.strftime("%Y-%m-%d")

    # Next weekday: "next monday", "next friday"
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    next_match = re.search(
        r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", text
    )
    if next_match:
        target_day = weekdays[next_match.group(1)]
        days_ahead = (target_day - today.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # This weekday: "this monday", "this friday"
    this_match = re.search(
        r"this\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", text
    )
    if this_match:
        target_day = weekdays[this_match.group(1)]
        days_ahead = (target_day - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # Just weekday name: "monday", "friday"
    for day_name, day_num in weekdays.items():
        if re.search(rf"\b{day_name}\b", text):
            days_ahead = (day_num - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # "in X days": "in 3 days", "in 2 days"
    in_days_match = re.search(r"in\s+(\d+)\s+days?", text)
    if in_days_match:
        return (today + timedelta(days=int(in_days_match.group(1)))).strftime(
            "%Y-%m-%d"
        )

    # "in X weeks": "in 2 weeks"
    in_weeks_match = re.search(r"in\s+(\d+)\s+weeks?", text)
    if in_weeks_match:
        return (today + timedelta(weeks=int(in_weeks_match.group(1)))).strftime(
            "%Y-%m-%d"
        )

    # Month name: "march 10", "april 5"
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    month_match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december"
        r"|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})",
        text,
    )
    if month_match:
        month_num = months[month_match.group(1)]
        day_num = int(month_match.group(2))
        year = today.year
        try:
            candidate = datetime(year, month_num, day_num).date()
            if candidate < today:
                candidate = datetime(year + 1, month_num, day_num).date()
            return candidate.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def clean_title(text, date_match_str=None, time_match_str=None):
    """Clean task title by removing trigger words, date, time references"""

    cleaned = text.lower()

    # Remove date string if found
    if date_match_str:
        cleaned = cleaned.replace(date_match_str.lower(), "")

    # Remove time string if found
    if time_match_str:
        cleaned = cleaned.replace(time_match_str.lower(), "")

    # Remove natural date phrases
    natural_date_phrases = [
        r"\bday after tomorrow\b",
        r"\btomorrow\b",
        r"\btoday\b",
        r"\bnext\s+\w+day\b",
        r"\bthis\s+\w+day\b",
        r"\bin\s+\d+\s+days?\b",
        r"\bin\s+\d+\s+weeks?\b",
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b(january|february|march|april|may|june|july|august|september"
        r"|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}\b",
    ]
    for phrase in natural_date_phrases:
        cleaned = re.sub(phrase, "", cleaned)

    # Remove time-related filler words
    time_fillers = [
        r"\bat\b",
        r"\bby\b",
        r"\baround\b",
    ]
    for filler in time_fillers:
        cleaned = re.sub(filler, "", cleaned)

    # Remove trigger/filler words
    filler_words = [
        r"\badd task\b",
        r"\badd to do\b",
        r"\badd todo\b",
        r"\badd to-do\b",
        r"\bremind me to\b",
        r"\bremind me\b",
        r"\bcreate task\b",
        r"\bnew task\b",
        r"\bschedule\b",
        r"\btodo\b",
        r"\bto-do\b",
        r"\btask\b",
        r"\breminder\b",
        r"\bplease\b",
        r"\bcan you\b",
        r"\bi need to\b",
        r"\bi have to\b",
        r"\bi want to\b",
        r"\bdon\'t forget to\b",
        r"\bdon\'t forget\b",
        r"\bmake sure to\b",
        r"\bmake sure\b",
        r"\bset a reminder\b",
        r"\bset reminder\b",
    ]
    for word in filler_words:
        cleaned = re.sub(word, "", cleaned)

    # Clean extra spaces and capitalize
    cleaned = re.sub(r"\s+", " ", cleaned).strip().capitalize()

    return cleaned


def extract_info(text):
    text_original = text
    text_lower = text.lower()

    # ----- Extract time -----
    time_pattern = r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b|\b(\d{2}:\d{2})\b"
    time_match = re.search(time_pattern, text_lower)
    task_time = None
    time_match_str = None

    if time_match:
        raw_time = (time_match.group(1) or time_match.group(2)).strip()
        time_match_str = raw_time

        try:
            if re.match(r"^\d{1,2}(am|pm)$", raw_time):
                task_time = datetime.strptime(raw_time, "%I%p").strftime("%I:%M %p")

            elif re.match(r"^\d{1,2}:\d{2}\s*(am|pm)$", raw_time.replace(" ", "")):
                clean = raw_time.replace(" ", "")
                task_time = datetime.strptime(clean, "%I:%M%p").strftime("%I:%M %p")

            elif re.match(r"^\d{2}:\d{2}$", raw_time):
                task_time = datetime.strptime(raw_time, "%H:%M").strftime("%I:%M %p")

        except ValueError:
            task_time = None

    # ----- Extract date -----
    # First try numeric format: 2026-03-05
    date_pattern = r"\b(\d{2,4}-\d{1,2}-\d{1,2})\b"
    date_match = re.search(date_pattern, text_lower)
    task_date = None
    date_match_str = None

    if date_match:
        task_date = date_match.group(1)
        date_match_str = date_match.group(1)
    else:
        # Try natural language date
        task_date = get_natural_date(text_lower)
        if task_date:
            # Find what natural phrase was used so we can remove it from title
            natural_phrases = [
                "day after tomorrow",
                "tomorrow",
                "today",
            ]
            for phrase in natural_phrases:
                if phrase in text_lower:
                    date_match_str = phrase
                    break

    # Fallback to today
    if not task_date:
        task_date = datetime.now().strftime("%Y-%m-%d")

    # ----- Clean Title -----
    title = clean_title(text_lower, date_match_str, time_match_str)

    return title, task_date, task_time
