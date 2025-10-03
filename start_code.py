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

pprint.pp(personeelsleden[0])

# verzamel taken
for taak in onderhoudstaken:
    beroepstype = taak['beroepstype']
    bevoegdheid = taak['bevoegdheid']
    fysieke_belasting = taak['fysieke_belasting']

    if beroepstype == personeelsleden[0]['beroepstype'] and bevoegdheid <= personeelsleden[0]['bevoegdheid'] and bereken_maximale_belasting(personeelslid=personeelsleden[0]) >= fysieke_belasting:
        user_taken.append(taak)
        print(beroepstype)
        print(bevoegdheid)
        print(fysieke_belasting)

# bereken taak duur
totale_duur = 0
for taak in user_taken:
    totale_duur += taak['duur']



# verzamel alle benodigde gegevens in een dictionary
dagtakenlijst = {
    "personeelsgegevens" : {
        "naam": personeelsleden[0] # voorbeeld van hoe je bij een eigenschap komt
        # STAP 1: vul aan met andere benodigde eigenschappen
    },
    "dagtaken": user_taken # STAP 2: hier komt een lijst met alle dagtaken
    ,
    "totale_duur": totale_duur # STAP 3: aanpassen naar daadwerkelijke totale duur
}

# uiteindelijk schrijven we de dictionary weg naar een JSON-bestand, die kan worden ingelezen door de acceptatieomgeving
with open('dagtakenlijst_personeelslid_x.json', 'w') as json_bestand_uitvoer:
    json.dump(dagtakenlijst, json_bestand_uitvoer, indent=4)