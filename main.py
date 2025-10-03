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

db.close()

user_taken = []

pprint.pp(personeelsleden[person_idx])

totale_taak_duur = 0

# verzamel taken
for taak in onderhoudstaken:
    beroepstype = taak['beroepstype']
    bevoegdheid = taak['bevoegdheid']
    fysieke_belasting = taak['fysieke_belasting']

    if beroepstype == personeelsleden[person_idx]['beroepstype'] and to_level(bevoegdheid) <= to_level(personeelsleden[person_idx]['bevoegdheid']) and bereken_maximale_belasting(personeelslid=personeelsleden[person_idx]) >= fysieke_belasting:
        werktijd = personeelsleden[person_idx]['werktijd']
        remaining = werktijd - totale_taak_duur

        # Als we nog >30 min over hebben: plan normaal (alles dat past)
        if remaining > 30:
            if taak['duur'] <= remaining:
                user_taken.append(taak)
                totale_taak_duur += taak['duur']

        else:
            if 0 < taak['duur'] <= remaining:
                user_taken.append(taak)
                totale_taak_duur += taak['duur']
                break

def voeg_administratie_tijd_toe(taken: list) -> int:
    '''Berekent en voegt administratie toe aan de taken lijst'''
    tijd_per_taak = 2
    admin_tijd = 0
    for taak in taken:
        admin_tijd += tijd_per_taak

    taak = {
        "naam": "administratietijd",
        "duur": admin_tijd,
    }
    taken.append(taak)
    return admin_tijd

def voeg_pauzes_toe(taken: list, duur: int, spiltsen: bool) -> list:
    '''Voegt pauzes toe ongeveer in het midden wanneer de werktijd langer is dan 5.5 uur'''

    def calc_insert_index(base_list: list, target_min: float) -> int:
        cumul = 0
        prev_cumul = 0
        for idx, taak in enumerate(base_list):
            d = taak['duur']
            prev_cumul = cumul
            cumul += d
            if cumul >= target_min:
                dist_voor = target_min - prev_cumul
                dist_na   = cumul - target_min
                return idx if dist_voor <= dist_na else idx + 1
        return len(base_list)
    
    if duur <= 330:
        return taken

    if not spiltsen:
        midden = duur / 2
        insert_at = calc_insert_index(taken, midden)
        taken.insert(insert_at, {"naam": "pauze", "duur": 30})
        return taken
    else:
        # eerste 3e en tweede 3e van de dag
        targets = [duur / 3, 2 * duur / 3]

        base = taken
        idx1 = calc_insert_index(base, targets[0])
        idx2_base = calc_insert_index(base, targets[1])

        # eerste pauze
        taken.insert(idx1, {"naam": "pauze", "duur": 15})

        # tweede pauze | corrigeer index voor de verschuiving door de eerste
        idx2 = idx2_base + 1 if idx2_base >= idx1 else idx2_base
        taken.insert(idx2, {"naam": "pauze", "duur": 15})
        return taken

regen_kans = f"{RAIN_CHANCE}%"

def sorteer_taken_op_bevoegdheid(taken: list) -> list:
    taken.sort(key=lambda x: x['bevoegdheid'], reverse=True)
    return taken

user_taken = sorteer_taken_op_bevoegdheid(user_taken)
totale_taak_duur += voeg_administratie_tijd_toe(user_taken)
user_taken = voeg_pauzes_toe(user_taken, totale_taak_duur, personeelsleden[person_idx]['pauze_opsplitsen'])

# verzamel alle benodigde gegevens in een dictionary
dagtakenlijst = {
    "personeelsgegevens" : {
        "personeelslid": personeelsleden[person_idx]
    },
    "dagtaken": user_taken
    ,
    "weer": regen_kans,
    "totale_duur": totale_taak_duur
}

# uiteindelijk schrijven we de dictionary weg naar een JSON-bestand, die kan worden ingelezen door de acceptatieomgeving
with open(f"dagtakenlijst_personeelslid_{personeelsleden[person_idx]['naam']}.json", 'w') as json_bestand_uitvoer:
    json.dump(dagtakenlijst, json_bestand_uitvoer, indent=4)