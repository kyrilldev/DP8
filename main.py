from enum import IntEnum
import json
import os
import requests as req
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
    '''Zet IntEnum om naar string'''
    if isinstance(v, Bevoegdheid):
        return v
    return MAP[str(v).strip().lower()]

def get_source_type():
    '''Vraagt aan de gebruiker welke data source gebruikt moet worden'''
    src = input("json or database?")
    if src == "json":
        print("chosen json")
        return src
    elif src == "database":
        print("chosen database")
        return src
    else:
        return get_source_type()
source = get_source_type()

db = Database(host="localhost", gebruiker="root", wachtwoord="Lily8-Pancake7", database="attractiepark")

personeelsleden = []
onderhoudstaken = []

db.connect()

if source == "json":
    #get stuff from json files
    files = ["personeelsgegevens_personeelslid_1.json",
             "personeelsgegevens_personeelslid_2.json", 
             "personeelsgegevens_personeelslid_3.json", 
             "personeelsgegevens_personeelslid_4.json"]
  
    for file in files:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, file)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            personeelsleden.extend(data)
        else:
            personeelsleden.append(data)
else:
    PERSONEELS_QUERY = "SELECT * FROM personeelslid"
    personeelsleden = db.execute_query(PERSONEELS_QUERY)

TAAK_QUERY = "SELECT * FROM onderhoudstaak"
onderhoudstaken = db.execute_query(TAAK_QUERY)

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

user_taken = []

def reserve_minuten_senior(werktijd_min: int) -> int:
    '''Reserveer 60 min elke 120 min vanaf het begin van de dienst.'''
    start = 120
    blokken = 0
    while start + 60 <= werktijd_min:
        blokken += 1
        start += 120
    return blokken * 60


def regenkans_dag():
    '''Get request voor de regenkans vandaag'''
    url = "http://api.weatherapi.com/v1/forecast.json"
    params = {"key": "e4a47bd82aca48e880b121521250310", "q": "Amsterdam", "aqi": "no"}
    try:
        r = req.get(url, params=params, timeout=10)
        r.raise_for_status()
        dt = r.json()

        if "error" in dt:
            raise ValueError(f"WeatherAPI error: {dt['error'].get('message', 'unknown error')}")

        current = dt.get("forecast", {})

        if current is None:
            raise ValueError("Temperature not found in API response.")

        forecast_day = current.get("forecastday", [{}])[0]
        forecast = forecast_day.get("day", {})

        if "daily_will_it_rain" in forecast:
            return int(forecast["daily_will_it_rain"])

    except (req.RequestException, ValueError) as e:
        raise RuntimeError(f"Failed to fetch temperature: {e}") from e

regen_kans = RAIN_CHANCE = regenkans_dag()

def tempratuur_dag(unit: str = "C"):
    '''Get request voor de tempratuur vandaag'''
    url = "http://api.weatherapi.com/v1/current.json"
    params = {"key": "e4a47bd82aca48e880b121521250310", "q": "Amsterdam", "aqi": "no"}
    try:
        r = req.get(url, params=params, timeout=10)
        r.raise_for_status()
        dt = r.json()

        if "error" in dt:
            raise ValueError(f"WeatherAPI error: {dt['error'].get('message', 'unknown error')}")

        current = dt.get("current", {})
        if unit.upper() == "F":
            temp = current.get("temp_f")
        else:
            temp = current.get("temp_c")

        if temp is None:
            raise ValueError("Temperature not found in API response.")

        return int(round(float(temp)))
    except (req.RequestException, ValueError) as e:
        raise RuntimeError(f"Failed to fetch temperature: {e}") from e

STORING_INTERVAL_MIN = 120
STORING_BLOK_MIN     = 60
volgende_storing_na  = STORING_INTERVAL_MIN

totale_taak_duur = 0

pers = {
    "naam": personeelsleden[person_idx]['naam'],    
    "werktijd": personeelsleden[person_idx]['werktijd'],    
    "beroepstype": personeelsleden[person_idx]['beroepstype'],    
    "bevoegdheid": personeelsleden[person_idx]['bevoegdheid'],    
    "specialist_in_attracties": personeelsleden[person_idx]['specialist_in_attracties'],    
    "pauze_opsplitsen": personeelsleden[person_idx]['pauze_opsplitsen'],    
    "max_fysieke_belasting": bereken_maximale_belasting(personeelsleden[person_idx]),    
}
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

    if (beroepstype == pers['beroepstype'] and to_level(bevoegdheid) <= to_level(pers['bevoegdheid']) and bereken_maximale_belasting(personeelsleden[person_idx]) >= fysieke_belasting):

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

        while is_senior and reserve_gepland < reserve_totaal and normaal_gepland >= volgende_storing_na:
            reserve_remaining = reserve_totaal - reserve_gepland
            if reserve_remaining <= 0:
                break

            target = STORING_BLOK_MIN if STORING_BLOK_MIN <= reserve_remaining else reserve_remaining

            alternatieven = []
            alternatieven_duur = 0

            # voorkeur: 30 min taken eerst
            kandidaten = sorted(
                onderhoudstaken,
                key=lambda t: (abs(int(t.get('duur',0)) - 30), int(t.get('duur',0)))
            )

            for alt in kandidaten:
                if str(alt.get('prioriteit','laag')).lower() != 'laag':
                    continue
                if alt.get('beroepstype') != pers['beroepstype']:
                    continue
                # bevoegdheid niet hoger dan eigen
                if to_level(alt.get('bevoegdheid')) > to_level(pers['bevoegdheid']):
                    continue
                if int(alt.get('fysieke_belasting',0)) > int(pers['max_fysieke_belasting']):
                    continue
                if (pers['beroepstype'] == "Schilder" and RAIN_CHANCE >= 50 and bool(alt.get('is_buitenwerk'))):
                    continue

                # taak duur vergelijken
                d_alt = int(alt.get('duur', 0))
                if d_alt <= 0:
                    continue
                if alternatieven_duur + d_alt <= target:
                    alternatieven.append(alt)
                    alternatieven_duur += d_alt
                if alternatieven_duur >= target or len(alternatieven) >= 3:
                    break

            # volgende storing berekenen
            if not alternatieven or alternatieven_duur <= 0:
                volgende_storing_na += STORING_INTERVAL_MIN
                break

            storingsblok = {
                "type": "storingen",
                "alternatieve_onderhoudstaken": [
                    {
                        "omschrijving": a.get("omschrijving"),
                        "duur": int(a.get("duur",0)),
                        "prioriteit": str(a.get("prioriteit","laag")).capitalize(),
                        "beroepstype": a.get("beroepstype"),
                        "bevoegdheid": a.get("bevoegdheid"),
                        "fysieke_belasting": a.get("fysieke_belasting"),
                        "attractie": a.get("attractie"),
                        "is_buitenwerk": a.get("is_buitenwerk")
                    } for a in alternatieven
                ]
            }

            user_taken.append(storingsblok)

            reserve_gepland  += alternatieven_duur
            totale_taak_duur += alternatieven_duur

            volgende_storing_na += STORING_INTERVAL_MIN




def voeg_administratie_tijd_toe(taken: list) -> int:
    '''Berekent en voegt administratie toe aan de taken lijst'''
    tijd_per_taak = 2
    admin_tijd = 0
    aantal_taken = 0

    for taak in taken:
        if taak.get('type') == 'storingen':
            alternatieven = taak.get('alternatieve_onderhoudstaken') or []
            cnt = sum(1 for a in alternatieven
                      if str(a.get('omschrijving', '')).lower() not in ('pauze', 'administratietijd'))
            if cnt > 0:
                admin_tijd += cnt * tijd_per_taak
                aantal_taken += cnt
            continue

        oms = taak.get('omschrijving')
        if not oms:
            continue
        if str(oms).lower() in ('pauze', 'administratietijd'):
            continue

        admin_tijd += tijd_per_taak
        aantal_taken += 1

    # 3) Admin-taak toevoegen
    taak = {
        "omschrijving": "administratietijd",
        "aantal_taken": aantal_taken,
        "duur": admin_tijd,
    }
    taken.append(taak)
    return admin_tijd


def voeg_pauzes_toe(taken: list, duur: int, spiltsen: bool, taak_duur: int) -> list:
    '''Voegt pauzes toe aan taken lijsten'''

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
    '''Sorteert taken op bevoegdheid'''
    def _req_level(taak: dict) -> int:
        # Storingen-blok
        if taak.get("type") == "storingen":
            alts = taak.get("alternatieve_onderhoudstaken") or []
            if not alts:
                return -1
            levels = [to_level(a.get("bevoegdheid")) for a in alts]
            return max((lv for lv in levels if lv is not None), default=-1)
        # Normale taak
        return to_level(taak.get("bevoegdheid"))

    taken.sort(key=_req_level, reverse=True)
    return taken


user_taken = sorteer_taken_op_bevoegdheid(user_taken)
totale_taak_duur += voeg_administratie_tijd_toe(user_taken)
user_taken = voeg_pauzes_toe(user_taken, totale_taak_duur, personeelsleden[person_idx]['pauze_opsplitsen'], totale_taak_duur)

# verzamel alle benodigde gegevens in een dictionary
dagtakenlijst = {
    "personeelsgegevens" : pers,
    "weergegevens": {"tempratuur": tempratuur, "regenkans": regen_kans},
    "dagtaken": user_taken
    ,
    "totale_duur": totale_taak_duur
}

# uiteindelijk schrijven we de dictionary weg naar een JSON-bestand, die kan worden ingelezen door de acceptatieomgeving
with open(f"dagtakenlijst_personeelslid_{personeelsleden[person_idx]['naam']}.json", 'w', encoding='utf-8') as json_bestand_uitvoer:
    json.dump(dagtakenlijst, json_bestand_uitvoer, indent=4)