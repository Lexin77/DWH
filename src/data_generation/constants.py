from datetime import date, datetime

START_BIRTHDAY_DATE = "1950-01-01"
END_BIRTHDAY_DATE = "2012-10-22"

OPENING_DATE = datetime.fromisoformat("2006-01-01")
LAST_WORKING_DATE = datetime.fromisoformat("2026-10-28")

GENDERS = ["male", "female"]

DAYS_IN_YEAR = 365

RUSSIAN_TIMEZONES = [
    "Europe/Kaliningrad",
    "Europe/Moscow",
    "Europe/Samara",
    "Europe/Volgograd",
    "Europe/Astrakhan",
    "Europe/Saratov",
    "Europe/Ulyanovsk",
    "Asia/Yekaterinburg",
    "Asia/Omsk",
    "Asia/Novosibirsk",
    "Asia/Barnaul",
    "Asia/Tomsk",
    "Asia/Novokuznetsk",
    "Asia/Krasnoyarsk",
    "Asia/Irkutsk",
    "Asia/Chita",
    "Asia/Yakutsk",
    "Asia/Khandyga",
    "Asia/Anadyr",
    "Asia/Vladivostok",
    "Asia/Ust-Nera",
    "Asia/Magadan",
    "Asia/Sakhalin",
    "Asia/Srednekolymsk",
    "Asia/Kamchatka",
]

MIN_PRICE = 200
MAX_PRICE = 20000
MAX_PRICE_UPDATES = 100
MIN_PRICE_UPDATES = 2

ORDER_STATES = [
    ["canceled", "collecting_order"],
    ["canceled", "sent_to_shop"],
    ["canceled", "ready", "lost"],
    ["canceled", "waiting_pickup", "sent_via_delivery", "lost"],
    ["canceled", "completed"],
]
ORDER_STATES_PROB = [
    [0.05, 0.95],
    [0.1, 0.9],
    [0.1, 0.85, 0.05],
    [0.1, 0.6, 0.25, 0.05],
    [0.05, 0.95],
]
DEAD_END_STAGES = ["canceled", "lost", "completed"]

COMPETITORS = ["homeberies", "amarket", "aboba", "kamoda"]

DAILY_PREDICT_START_DATE = date.fromisoformat("2025-01-01")
MIN_DAILY_ORDERS = 0
MAX_DAILY_ORDERS = 100

AMPLIFY_COEF_MIN = 1.0
AMPLIFY_COEF_MAX = 1.5

DAILY_REVENUE_PREDICT_START_DATE = date.fromisoformat("2023-01-01")
MIN_DAILY_REVENUE = 100000
MAX_DAILY_REVENUE = 1000000

USER_CLUSTERS = ["low", "middle", "hight"]
