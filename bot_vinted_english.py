from playwright.sync_api import sync_playwright
import requests
import re
import time
import os


# config

SEARCH_URL = "URL_VINTED"

WEBHOOK_URL = "WEBHOOK_DISCORD"

MIN_PRICE = 50
MAX_PRICE = 300

ACCEPTED_CONDITIONS = [
    "Very good",
    "New with tag",
    "New without tag"
]

INTERVAL = 120

ADS_FILE = "seen_ads.txt"


# memory


def load_seen_ads():

    if not os.path.exists(ADS_FILE):
        return set()

    with open(ADS_FILE, "r", encoding="utf-8") as file:
        return set(
            line.strip()
            for line in file
            if line.strip()
        )


def save_ad(ad_id):

    with open(
        ADS_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(ad_id + "\n")


# discord part


def send_discord(title, brand, condition, price, link):

    message = {
        "content": (
            " **NEW INTERESTING AD**\n\n"
            f" **{title}**\n"
            f" Brand : {brand}\n"
            f" Condition : {condition}\n"
            f" Price : **{price:.2f} €**\n\n"
            f" {link}"
        )
    }

    response = requests.post(
        WEBHOOK_URL,
        json=message
    )

    if response.status_code == 204:
        print("Discord notification sent")

    else:
        print(
            "Discord error:",
            response.status_code,
            response.text
        )


    # vinted part


def analyze_page(page, seen_ads):

    print("\n🔎 Analyzing Vinted...")

    page.goto(
        SEARCH_URL,
        wait_until="domcontentloaded"
    )

    page.wait_for_timeout(5000)

    ads = page.locator(
        'a[data-testid*="product-item-id"][href*="/items/"]'
    )

    count = ads.count()

    print(
        f"{count} ads found"
    )

    for i in range(count):

        ad = ads.nth(i)

        info = ad.get_attribute("title")
        link = ad.get_attribute("href")

        if not info or not link:
            continue

        id_match = re.search(
            r'/items/(\d+)',
            link
        )

        if not id_match:
            continue

        ad_id = id_match.group(1)

        price_match = re.search(
            r'(\d+(?:[.,]\d+)?)\s*€',
            info
        )

        if not price_match:
            continue

        price = float(
            price_match.group(1).replace(",", ".")
        )

        brand_match = re.search(
            r'Marque:\s*(.*?),\s*État:',
            info
        )

        if brand_match:
            brand = brand_match.group(1)
        else:
            brand = "Unknown"

        condition_match = re.search(
            r'État:\s*(.*?),\s*\d',
            info
        )

        if condition_match:
            condition = condition_match.group(1)
        else:
            condition = "Unknown"

        if ", Marque:" in info:
            title = info.split(
                ", Marque:"
            )[0]
        else:
            title = info

        if price < MIN_PRICE:
            continue

        if price > MAX_PRICE:
            continue

        if condition not in ACCEPTED_CONDITIONS:
            continue

        if ad_id in seen_ads:

            print(
                f"Already seen: {ad_id}"
            )

            continue

        print()
        print("NEW AD")
        print("ID :", ad_id)
        print("Title :", title)
        print("Brand :", brand)
        print("Condition :", condition)
        print("Price :", price)
        print("Link :", link)

        full_url = (
            "https://www.vinted.fr"
            + link
        )

        # Discord
        send_discord(
            title,
            brand,
            condition,
            price,
            full_url
        )

        seen_ads.add(ad_id)

        save_ad(
            ad_id
        )


seen_ads = load_seen_ads()

print(
    f"{len(seen_ads)} ads already saved"
)


with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False
    )

    page = browser.new_page()

    while True:

        try:

            analyze_page(
                page,
                seen_ads
            )

        except Exception as error:

            print(
                "Error:",
                error
            )

        print()
        print(
            f"Next check in "
            f"{INTERVAL} seconds..."
        )

        time.sleep(INTERVAL)
