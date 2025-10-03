# import modulen
from enum import IntEnum
from pathlib import Path
import json
import pprint
import random
from database_wrapper import Database


class Bevoegdheid(IntEnum):
    STAGIAIR = 0
    JUNIOR    = 1
    MEDIOR    = 2
    SENIOR    = 3

MAP = {
    "stagiair": Bevoegdheid.STAGIAIR,
    "junior":    Bevoegdheid.JUNIOR,
    "medior":    Bevoegdheid.MEDIOR,
    "senior":    Bevoegdheid.SENIOR,
}

def to_level(v) -> Bevoegdheid:
    """Converts IntEnum to String from MAP"""
    if isinstance(v, Bevoegdheid):
        return v
    return MAP[str(v).strip().lower()]

RAIN_CHANCE = random.randint(0,100)

db = Database(host="localhost", gebruiker="root", wachtwoord="Lily8-Pancake7", database="attractiepark")
db.connect()

select_query = "SELECT * FROM personeelslid"
personeelsleden = db.execute_query(select_query)

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

    # bevoegdheid shit werkt niet perfect
    if beroepstype == personeelsleden[person_idx]['beroepstype'] and to_level(bevoegdheid) <= to_level(personeelsleden[person_idx]['bevoegdheid']) and bereken_maximale_belasting(personeelslid=personeelsleden[person_idx]) >= fysieke_belasting:
        user_taken.append(taak)

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