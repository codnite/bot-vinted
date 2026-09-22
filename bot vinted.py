from playwright.sync_api import sync_playwright
import requests
import re
import time
import os


# config

URL_RECHERCHE = "URL_VINTED"

WEBHOOK_URL = "WEBHOOK_DISCORD"

PRIX_MIN = 50
PRIX_MAX = 300

ETATS_ACCEPTES = [
    "Très bon état",
    "Neuf avec étiquette",
    "Neuf sans étiquette"
]

INTERVALLE = 120  # 120 secondes = 2 minutes

FICHIER_ANNONCES = "annonces_vues.txt"


# memory


def charger_annonces_vues():

    if not os.path.exists(FICHIER_ANNONCES):
        return set()

    with open(FICHIER_ANNONCES, "r", encoding="utf-8") as fichier:
        return set(
            ligne.strip()
            for ligne in fichier
            if ligne.strip()
        )


def sauvegarder_annonce(identifiant):

    with open(
        FICHIER_ANNONCES,
        "a",
        encoding="utf-8"
    ) as fichier:

        fichier.write(identifiant + "\n")


# discord part

def envoyer_discord(titre, marque, etat, prix, lien):

    message = {
        "content": (
            " **NOUVELLE ANNONCE INTÉRESSANTE**\n\n"
            f" **{titre}**\n"
            f" Marque : {marque}\n"
            f" État : {etat}\n"
            f" Prix : **{prix:.2f} €**\n\n"
            f" {lien}"
        )
    }

    response = requests.post(
        WEBHOOK_URL,
        json=message
    )

    if response.status_code == 204:
        print("Notification Discord envoyée")

    else:
        print(
            "Erreur Discord :",
            response.status_code,
            response.text
        )


# vinted part

def analyser_page(page, annonces_vues):

    print("\n🔎 Analyse de Vinted...")

    page.goto(
        URL_RECHERCHE,
        wait_until="domcontentloaded"
    )

    page.wait_for_timeout(5000)

    annonces = page.locator(
        'a[data-testid*="product-item-id"][href*="/items/"]'
    )

    nombre = annonces.count()

    print(
        f"{nombre} annonces trouvées"
    )

    for i in range(nombre):

        annonce = annonces.nth(i)

        informations = annonce.get_attribute("title")
        lien = annonce.get_attribute("href")

        if not informations or not lien:
            continue

        id_match = re.search(
            r'/items/(\d+)',
            lien
        )

        if not id_match:
            continue

        identifiant = id_match.group(1)


        prix_match = re.search(
            r'(\d+(?:[.,]\d+)?)\s*€',
            informations
        )

        if not prix_match:
            continue

        prix = float(
            prix_match.group(1).replace(",", ".")
        )


        marque_match = re.search(
            r'Marque:\s*(.*?),\s*État:',
            informations
        )

        if marque_match:
            marque = marque_match.group(1)
        else:
            marque = "Inconnue"


        etat_match = re.search(
            r'État:\s*(.*?),\s*\d',
            informations
        )

        if etat_match:
            etat = etat_match.group(1)
        else:
            etat = "Inconnu"


        if ", Marque:" in informations:
            titre = informations.split(
                ", Marque:"
            )[0]
        else:
            titre = informations


        if prix < PRIX_MIN:
            continue

        if prix > PRIX_MAX:
            continue

        if etat not in ETATS_ACCEPTES:
            continue


        if identifiant in annonces_vues:

            print(
                f"Déjà vue : {identifiant}"
            )

            continue


        print()
        print("NOUVELLE ANNONCE")
        print("ID :", identifiant)
        print("Titre :", titre)
        print("Marque :", marque)
        print("État :", etat)
        print("Prix :", prix)
        print("Lien :", lien)

        url_complete = (
            "https://www.vinted.fr"
            + lien
        )

        # Discord
        envoyer_discord(
            titre,
            marque,
            etat,
            prix,
            url_complete
        )

        # Mémoire
        annonces_vues.add(identifiant)

        sauvegarder_annonce(
            identifiant
        )




annonces_vues = charger_annonces_vues()

print(
    f"{len(annonces_vues)} annonces déjà enregistrées"
)


with sync_playwright() as p:

    navigateur = p.chromium.launch(
        headless=False
    )

    page = navigateur.new_page()

    while True:

        try:

            analyser_page(
                page,
                annonces_vues
            )

        except Exception as erreur:

            print(
                "Erreur:",
                erreur
            )

        print()
        print(
            f"Prochaine vérification dans "
            f"{INTERVALLE} secondes..."
        )

        time.sleep(INTERVALLE)