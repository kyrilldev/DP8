# import modulen
from enum import IntEnum
from pathlib import Path
import json
import pprint
import random
from database_wrapper import Database
import requests as req


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
# RAIN_CHANCE = 55

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

def reserve_minuten_senior(werktijd_min: int) -> int:
    '''Reserveer 60 min elke 120 min vanaf het begin van de dienst.'''
    start = 120
    blokken = 0
    while start + 60 <= werktijd_min:
        blokken += 1
        start += 120
    return blokken * 60


# pprint.pp(personeelsleden[person_idx])
regen_kans = f"{RAIN_CHANCE}%"

def tempratuur_dag(unit: str = "C"):
    url = "http://api.weatherapi.com/v1/current.json"
    params = {"key": "e4a47bd82aca48e880b121521250310", "q": "Amsterdam", "aqi": "no"}
    try:
        r = req.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if "error" in data:
            raise ValueError(f"WeatherAPI error: {data['error'].get('message', 'unknown error')}")

        current = data.get("current", {})
        if unit.upper() == "F":
            temp = current.get("temp_f")
        else:
            temp = current.get("temp_c")

        if temp is None:
            raise ValueError("Temperature not found in API response.")

        return int(round(float(temp)))
    except (req.RequestException, ValueError) as e:
        raise RuntimeError(f"Failed to fetch temperature: {e}") from e

totale_taak_duur = 0

pers = personeelsleden[person_idx]
werktijd = pers['werktijd']

tempratuur = tempratuur_dag()

# senior?
is_senior = str(pers['bevoegdheid']).lower() == "senior"

reserve_totaal = reserve_minuten_senior(werktijd) if is_senior else 0

normaal_gepland = 0
reserve_gepland = 0

normaal_gepland = totale_taak_duur

for taak in onderhoudstaken:
    beroepstype = taak['beroepstype']
    bevoegdheid = taak['bevoegdheid']
    fysieke_belasting = taak['fysieke_belasting']
    d = taak['duur']
    prio = str(taak.get('prioriteit', 'laag')).lower()  # 'laag' of 'hoog'

    # regenregel voor Schilders buitenwerk
    if (pers['beroepstype'] == "Schilder" and beroepstype == "Schilder" and RAIN_CHANCE >= 50 and taak['is_buitenwerk'] is True):
        continue

    if (beroepstype == pers['beroepstype'] and to_level(bevoegdheid) <= to_level(pers['bevoegdheid']) and bereken_maximale_belasting(personeelslid=pers) >= fysieke_belasting):

        nonreserve_remaining = werktijd - reserve_totaal - normaal_gepland

        if nonreserve_remaining > 30:
            if d <= nonreserve_remaining:
                user_taken.append(taak)
                normaal_gepland += d
                totale_taak_duur += d
        else:
            # eindsprint | maximaal een korte taak die nog in de non reserve past
            if 0 < d <= nonreserve_remaining:
                user_taken.append(taak)
                normaal_gepland += d
                totale_taak_duur += d
                break  # precies een eind van de dag taak

        # daarna reserve opvullen met lage prioriteit
        if is_senior and prio == 'laag':
            reserve_remaining = reserve_totaal - reserve_gepland
            if d <= reserve_remaining:
                # markeer als tijdelijk/swapbaar door middel van opmerking
                taak_tmp = dict(taak)
                taak_tmp['tijdelijk'] = True
                taak_tmp['opmerking'] = "vult reserveruimte voor storingen"

                user_taken.append(taak_tmp)
                reserve_gepland += d
                totale_taak_duur += d


def voeg_administratie_tijd_toe(taken: list) -> int:
    '''Berekent en voegt administratie toe aan de taken lijst'''
    tijd_per_taak = 2
    admin_tijd = 0
    for taak in taken:
        if taak['omschrijving'] != "pauze":
            admin_tijd += tijd_per_taak

    taak = {
        "omschrijving": "administratietijd",
        "duur": admin_tijd,
    }
    taken.append(taak)
    return admin_tijd

def voeg_pauzes_toe(taken: list, duur: int, spiltsen: bool, taak_duur: int) -> list:
    '''Voegt pauzes toe'''

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
        taken.insert(insert_at, {"omschrijving": "pauze", "duur": 30})
        return taken
    elif tempratuur > 30:
        targets = [duur / 3, duur / 2 ,2 * duur / 3]
        base = taken
        idx1 = calc_insert_index(base, targets[0])
        idx2 = calc_insert_index(base, targets[1])
        idx3 = calc_insert_index(base, targets[2])

        # eerste pauze
        taken.insert(idx1, {"omschrijving": "pauze", "duur": 15})

        # tweede pauze
        idx2_corr = idx2 + 1 if idx2 >= idx1 else idx2
        taken.insert(idx2_corr, {"omschrijving": "pauze", "duur": 15, "reden": "temperatuur"})
        taak_duur += 15

        # derde pauze
        shift = sum(1 for ins in (idx1, idx2) if idx3 >= ins)
        idx3_corr = idx3 + shift + 1
        taken.insert(idx3_corr, {"omschrijving": "pauze", "duur": 15})
        return taken
    else:
        # eerste 3e en tweede 3e van de dag
        targets = [duur / 3, 2 * duur / 3]

        base = taken
        idx1 = calc_insert_index(base, targets[0])
        idx2_base = calc_insert_index(base, targets[1])

        # eerste pauze
        taken.insert(idx1, {"omschrijving": "pauze", "duur": 15})

        # tweede pauze | corrigeert index voor de verschuiving door de eerste
        idx2 = idx2_base + 1 if idx2_base >= idx1 else idx2_base
        taken.insert(idx2, {"omschrijving": "pauze", "duur": 15})
        return taken

def sorteer_taken_op_bevoegdheid(taken: list) -> list:
    taken.sort(key=lambda x: x['bevoegdheid'], reverse=True)
    return taken

user_taken = sorteer_taken_op_bevoegdheid(user_taken)
totale_taak_duur += voeg_administratie_tijd_toe(user_taken)
user_taken = voeg_pauzes_toe(user_taken, totale_taak_duur, personeelsleden[person_idx]['pauze_opsplitsen'], totale_taak_duur)

# verzamel alle benodigde gegevens in een dictionary
dagtakenlijst = {
    "personeelsgegevens" : {
        "personeelslid": personeelsleden[person_idx]
    },
    "dagtaken": user_taken
    ,
    "weer": regen_kans,
    "temperatuur": tempratuur,
    "totale_duur": totale_taak_duur
}

# uiteindelijk schrijven we de dictionary weg naar een JSON-bestand, die kan worden ingelezen door de acceptatieomgeving
with open(f"dagtakenlijst_personeelslid_{personeelsleden[person_idx]['naam']}.json", 'w') as json_bestand_uitvoer:
    json.dump(dagtakenlijst, json_bestand_uitvoer, indent=4)