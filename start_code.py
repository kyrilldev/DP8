# import modulen
from pathlib import Path
import json
import pprint
from database_wrapper import Database
import random
from enum import Enum


class bevoegdheid(Enum):
    '''Helps simplify selecting tasks'''
    STAGIAIRE = "Stagiaire",
    JUNIOR = "Junior",
    MEDIOR = "Medior",
    SENIOR = "Senior"

# initialisatie

RAIN_CHANCE = random.randint(0,100)

# parameters voor connectie met de database
db = Database(host="localhost", gebruiker="root", wachtwoord="Lily8-Pancake7", database="attractiepark")


# main

# Haal de eigenschappen op van een personeelslid
# altijd verbinding openen om query's uit te voeren
db.connect()

# pas deze query aan om het juiste personeelslid te selecteren
select_query = "SELECT * FROM personeelslid"
personeelsleden = db.execute_query(select_query)

# altijd verbinding sluiten met de database als je klaar bent
db.close()

def ask_for_person_index() -> int:
    '''asks for a person in the system and validates input'''
    names = []
    for persoon in personeelsleden:
        names.append(persoon['naam'])
        print(persoon['naam'])
    
    lowercase_list = [item.lower() for item in names]

    while True:
        selection = input("who are you?\n")
        print(selection)
        if type(selection) == str and len(selection) < 45 and selection.lower() in lowercase_list:
            break
        else:
            print("Input not valid, please try again!")

    return lowercase_list.index(selection)

person_idx = ask_for_person_index()

def bereken_maximale_belasting(personeelslid) -> int:
    '''berekend de maximale belasting van een personeelslid'''
    leeftijd: int = personeelslid['leeftijd']
    verlaagde_fysieke_belasting: int  = personeelslid['verlaagde_fysieke_belasting']

    if verlaagde_fysieke_belasting == 0:
        if leeftijd <= 24:
            return 25
        if leeftijd >= 25 and leeftijd <= 50:
            return 40
        if leeftijd > 51:
            return 20
    else:
        return verlaagde_fysieke_belasting
    
db.connect()

query = "SELECT * FROM onderhoudstaak"
onderhoudstaken = db.execute_query(query)
# pprint.pp(onderhoudstaken)
db.close()

user_taken = []

pprint.pp(personeelsleden[person_idx])

# verzamel taken
for taak in onderhoudstaken:
    beroepstype = taak['beroepstype']
    bevoegdheid = taak['bevoegdheid']
    fysieke_belasting = taak['fysieke_belasting']

    if beroepstype == personeelsleden[person_idx]['beroepstype'] and bevoegdheid <= personeelsleden[person_idx]['bevoegdheid'] and bereken_maximale_belasting(personeelslid=personeelsleden[person_idx]) >= fysieke_belasting:
        user_taken.append(taak)
        # print(beroepstype)
        # print(bevoegdheid)
        # print(fysieke_belasting)

# bereken taak duur
totale_duur = 0
for taak in user_taken:
    totale_duur += taak['duur']

regen_kans = f"{RAIN_CHANCE}%"

# verzamel alle benodigde gegevens in een dictionary
dagtakenlijst = {
    "personeelsgegevens" : {
        "naam": personeelsleden[person_idx]
    },
    "dagtaken": user_taken
    ,
    "weer": regen_kans,
    "totale_duur": totale_duur
}

# uiteindelijk schrijven we de dictionary weg naar een JSON-bestand, die kan worden ingelezen door de acceptatieomgeving
with open(f"dagtakenlijst_personeelslid_{personeelsleden[person_idx]['naam']}.json", 'w') as json_bestand_uitvoer:
    json.dump(dagtakenlijst, json_bestand_uitvoer, indent=4)