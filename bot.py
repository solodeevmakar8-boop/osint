import json
import math
import re
import urllib3
import requests
import telebot
from telebot import apihelper
from collections import defaultdict
from datetime import datetime, date

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============ НАСТРОЙКИ И ТОКЕНЫ ============
BOT_TOKEN = "8980477046:AAGqIGlTsDWd235ArbGyiC4LEWTLfD91Ef8"
BIGBASE_TOKEN = "5INtzlWpIFMgPHknBBKFz_0ulNrsqH_B"
API_BASE = "https://bigbase.top/api"

# Прокси (HTTP)
PROXY_URL = "http://Y6rq9r:vLkDQU@181.177.103.28:9251"
PROXIES = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

# Подключение прокси для TeleBot (решает ошибку ConnectTimeoutError)
apihelper.proxy = PROXIES

bot = telebot.TeleBot(BOT_TOKEN)

# ============ РЕГУЛЯРНЫЕ ВЫРАЖЕНИЯ ============
UP = r'А-ЯЁЇІЄҐ'
LO = r'а-яёїієґ'

RX = {
    'phone':    re.compile(r'(?:\+7|8)[\s\-\(\)]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}'),
    'email':    re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'),
    'telegram': re.compile(r'(?<![\w@])@[A-Za-z][A-Za-z0-9_]{4,31}\b'),
    'snils':    re.compile(r'\b\d{3}[\-\s]\d{3}[\-\s]\d{3}[\s\-]\d{2}\b'),
    'inn':      re.compile(r'\b\d{12}\b'),
    'passport': re.compile(r'\b\d{2}\s+\d{2}\s+\d{6}\b|\b\d{4}\s+\d{6}\b'),
    'date':     re.compile(r'\b\d{2}[\.\-/]\d{2}[\.\-/]\d{4}\b'),
    'url':      re.compile(r'https?://[^\s"\'<>\\]+'),
    'card': re.compile(
        r'\b(?:\d{4}[\s\-]?){3}\d{4}\b'
        r'|\b\d{4,6}[\*\s\-]{4,}\d{2,4}\b'
        r'|\b\d{16}\b'
        r'|\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b'
    ),
    'gosnomer': re.compile(r'\b[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}\b'),
    'vin':      re.compile(r'\b[A-HJ-NPR-Z0-9]{17}\b'),
    'ogrn':     re.compile(r'\b\d{13}\b|\b\d{15}\b'),
    'fio': re.compile(
        rf'\b[{UP}][{LO}\'’\-]{{2,}}(?:\s+[{UP}][{LO}\'’\-]{{2,}}){{1,2}}\b'
    ),
    'address': re.compile(
        rf'(?:'
            rf'(?:ул\.|улица|пр-?т|проспект|пер\.|переулок|шоссе|б-р|бульвар|'
            rf'наб\.|набережная|пл\.|площадь|проезд|аллея|тракт)\s+'
            rf'[{UP}{LO}0-9\-\. ]{{3,60}}'
            rf'|(?:г\.|город|м\.|місто)\s+[{UP}][{LO}\-]+'
            rf'|[{UP}][{LO}\-]+\s+(?:обл\.|область|край|респ\.|республика)'
        rf')',
        re.IGNORECASE
    ),
}

FIO_BLACKLIST = {
    'ооо', 'оао', 'зао', 'пао', 'ип', 'гуп', 'муп', 'нко', 'анпо', 'тоо',
    'ао', 'фгбу', 'фгуп', 'снт', 'тсж', 'жск', 'мкд',
    'город', 'городской', 'городская', 'городское',
    'нижний', 'верхний', 'новый', 'старый', 'большой', 'малый',
    'новости', 'новость', 'чат', 'беседа', 'группа', 'канал',
    'сообщество', 'паблик', 'подслушано', 'барахолка', 'объявления',
    'объявление', 'доска', 'market', 'shop', 'group', 'chat',
    'channel', 'news', 'community',
    'мой', 'моя', 'мои', 'наш', 'наша', 'наши', 'ваш', 'ваша', 'ваши',
    'этот', 'эта', 'эти', 'тот', 'та', 'те',
    'курьер', 'доставка', 'магазин', 'сервис', 'студия', 'агентство',
    'центр', 'клуб', 'форум', 'портал', 'салон', 'аптека', 'ресторан',
    'кафе', 'бар', 'книга', 'школа', 'лицей', 'гимназия',
    'work', 'job', 'city', 'town', 'region', 'area',
}

PATRONYMIC_ENDINGS = (
    'ович', 'евич', 'ич', 'овна', 'евна', 'ична', 'инична', 'кызы', 'улы',
)
SURNAME_ENDINGS = (
    'ов', 'ев', 'ин', 'ын', 'ский', 'цкий', 'ая', 'яя', 'ий', 'ой',
    'ко', 'ук', 'юк', 'ич', 'ова', 'ева', 'ина', 'енко', 'чук',
)

LABEL_WORDS = {
    'народження', 'рождения', 'выдачи', 'проживания', 'регистрации',
    'жительства', 'пребывания', 'батькові', 'батька', 'рожден',
}

ADDR_KEYS = {
    'postal': {'postal_code', 'postcode', 'zip', 'zip_code', 'index', 'индекс',
               'почтовый_индекс', 'почтовый индекс', 'п. индекс'},
    'country': {'country', 'страна', 'country_name'},
    'region': {'region', 'region_name', 'область', 'обл', 'республика', 'респ',
               'край', 'subject', 'субъект', 'область_название'},
    'city': {'city', 'town', 'locality', 'город', 'г', 'населенный_пункт',
             'населённый_пункт', 'village', 'поселок', 'посёлок', 'пгт', 'місто'},
    'street': {'street', 'street_name', 'улица', 'ул', 'улица_название', 'вулиця'},
    'house': {'house', 'house_number', 'дом', 'д', 'дом_номер', 'корпус', 'корп',
              'строение', 'стр', 'буд', 'будівля'},
    'apartment': {'apartment', 'flat', 'apt', 'квартира', 'кв', 'room', 'комната',
                  'офис', 'office'},
    'full': {'address', 'full_address', 'fulladdress', 'address_line',
             'street_address', 'адрес', 'адрес_регистрации', 'адрес_проживания',
             'адрес_фактический', 'address_registration', 'address_residence'},
}

BIRTH_KEYS = {
    'birth_date', 'birthday', 'date_of_birth', 'dob', 'birth', 'birthdate',
    'birth_day', 'data_rozhdeniya', 'data_narodzhennya',
    'дата_рождения', 'дата рождения', 'др', 'дата_народження', 'день рождения',
}

TG_GROUP_LIST_KEYS = {
    'groups', 'group', 'chats', 'chat_list', 'communities',
    'группы', 'группа', 'чаты', 'сообщества',
    'channels', 'каналы', 'канал',
}
TG_GROUP_NAME_KEYS = {
    'name', 'title', 'group_name', 'chat_name', 'channel_name',
    'название', 'наименование', 'имя',
}
TG_GROUP_USERNAME_KEYS = {
    'username', 'user_name', 'link', 'url', 'tg_link', 'telegram',
    'имя пользователя', 'юзернейм', 'ссылка', 'юзер',
}

TYPE_CONFIG = {
    'vin':        {'base': 10.0, 'mult': 2.0, 'ru': 'VIN автомобиля'},
    'snils':      {'base': 10.0, 'mult': 2.0, 'ru': 'СНИЛС'},
    'inn':        {'base':  9.0, 'mult': 1.8, 'ru': 'ИНН'},
    'passport':   {'base':  9.0, 'mult': 1.8, 'ru': 'Паспорт РФ'},
    'card':       {'base':  9.0, 'mult': 1.8, 'ru': 'Банковская карта'},
    'phone':      {'base':  8.0, 'mult': 1.5, 'ru': 'Телефон'},
    'email':      {'base':  8.0, 'mult': 1.5, 'ru': 'Email'},
    'telegram':   {'base':  8.0, 'mult': 1.4, 'ru': 'Telegram'},
    'tg_group':   {'base':  7.0, 'mult': 1.3, 'ru': 'Группа/канал TG'},
    'gosnomer':   {'base':  7.0, 'mult': 1.3, 'ru': 'Госномер авто'},
    'ogrn':       {'base':  7.0, 'mult': 1.3, 'ru': 'ОГРН/ОГРНИП'},
    'birth_date': {'base':  7.0, 'mult': 1.3, 'ru': 'Дата рождения'},
    'date':       {'base':  6.0, 'mult': 1.2, 'ru': 'Дата'},
    'address':    {'base':  6.0, 'mult': 1.0, 'ru': 'Адрес'},
    'age':        {'base':  5.0, 'mult': 1.0, 'ru': 'Возраст'},
    'url':        {'base':  4.0, 'mult': 0.9, 'ru': 'Ссылка'},
    'fio':        {'base':  5.0, 'mult': 0.6, 'ru': 'ФИО'},
}

OPERATOR_PREFIXES = {
    '910': 'МТС', '911': 'МТС', '912': 'МТС', '913': 'МТС', '914': 'МТС',
    '915': 'МТС', '916': 'МТС', '917': 'МТС', '918': 'МТС', '919': 'МТС',
    '980': 'МТС', '981': 'МТС', '982': 'МТС', '983': 'МТС', '984': 'МТС',
    '985': 'МТС', '986': 'МТС', '987': 'МТС', '988': 'МТС', '989': 'МТС',
    '920': 'МегаФон', '921': 'МегаФон', '922': 'МегаФон', '923': 'МегаФон',
    '924': 'МегаФон', '925': 'МегаФон', '926': 'МегаФон', '927': 'МегаФон',
    '928': 'МегаФон', '929': 'МегаФон', '930': 'МегаФон', '931': 'МегаФон',
    '932': 'МегаФон', '933': 'МегаФон', '934': 'МегаФон', '936': 'МегаФон',
    '937': 'МегаФон', '938': 'МегаФон', '939': 'МегаФон',
    '903': 'Билайн', '905': 'Билайн', '906': 'Билайн', '909': 'Билайн',
    '960': 'Билайн', '961': 'Билайн', '962': 'Билайн', '963': 'Билайн',
    '964': 'Билайн', '965': 'Билайн', '966': 'Билайн', '967': 'Билайн',
    '968': 'Билайн',
    '900': 'Tele2', '901': 'Tele2', '902': 'Tele2', '904': 'Tele2',
    '908': 'Tele2', '950': 'Tele2', '951': 'Tele2', '952': 'Tele2',
    '953': 'Tele2', '958': 'Tele2', '977': 'Tele2', '991': 'Tele2',
    '992': 'Tele2', '993': 'Tele2', '994': 'Tele2', '995': 'Tele2',
    '999': 'Yota', '997': 'Yota', '998': 'Yota',
}

BANK_BINS = {
    '4276': 'Сбербанк', '4279': 'Сбербанк', '4817': 'Сбербанк', '5469': 'Сбербанк',
    '5484': 'Сбербанк', '5559': 'Сбербанк', '6762': 'Сбербанк', '6771': 'Сбербанк',
    '4377': 'Т-Банк', '5213': 'Т-Банк', '5536': 'Т-Банк', '2200': 'Т-Банк',
    '4272': 'ВТБ', '4003': 'ВТБ', '4893': 'ВТБ', '2202': 'ВТБ',
    '4154': 'Альфа-Банк', '4584': 'Альфа-Банк', '5486': 'Альфа-Банк', '2201': 'Альфа-Банк',
    '4231': 'Газпромбанк', '4890': 'Газпромбанк', '5398': 'Газпромбанк',
    '4627': 'Райффайзен', '5100': 'Райффайзен', '5555': 'Райффайзен',
    '4623': 'Россельхозбанк', '5505': 'Россельхозбанк', '6054': 'Россельхозбанк',
    '2204': 'Почта Банк',
}

# ============ ХЕЛПЕРЫ ============
def extract_records(parsed_json) -> list:
    if isinstance(parsed_json, dict):
        for key in ('records', 'data', 'results', 'items'):
            if key in parsed_json and isinstance(parsed_json[key], list):
                return parsed_json[key]
        return [parsed_json]
    if isinstance(parsed_json, list):
        return parsed_json
    return [{"_raw": str(parsed_json)}]

def record_to_text(rec) -> str:
    if isinstance(rec, (dict, list)):
        return json.dumps(rec, ensure_ascii=False)
    return str(rec)

def is_label_value(val: str) -> bool:
    words = re.findall(r'[а-яёїієґ]+', val.lower())
    return any(w in LABEL_WORDS for w in words)

def collect_values_by_keys(obj, keys, out=None):
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in keys and isinstance(v, (str, int)) and str(v).strip():
                out.append(str(v).strip())
            elif isinstance(v, (dict, list)):
                collect_values_by_keys(v, keys, out)
    elif isinstance(obj, list):
        for it in obj:
            collect_values_by_keys(it, keys, out)
    return out

FIO_FULL_KEYS    = {'fio', 'фио', 'full_name', 'fullname', 'full-name', 'піб'}
FIO_SURNAME_KEYS = {'surname', 'last_name', 'lastname', 'фамилия', 'familia',
                    'prizvyshche', 'прізвище'}
FIO_NAME_KEYS    = {'first_name', 'firstname', 'given_name', 'имя', 'imya',
                    "ім'я", "ім’я", 'імʼя'}
FIO_MIDDLE_KEYS  = {'middle_name', 'middlename', 'patronymic', 'patronym',
                    'отчество', 'po_batkovi', 'po_batkove', 'по батькові'}

def looks_like_fio(val: str) -> bool:
    words = [w.lower() for w in val.split()]
    if len(words) < 2:
        return False
    if any(w in FIO_BLACKLIST for w in words):
        return False
    if len(words) >= 3:
        return any(w.endswith(PATRONYMIC_ENDINGS) for w in words)
    return any(w.endswith(SURNAME_ENDINGS) for w in words)

def assemble_fio(obj):
    results = []
    if isinstance(obj, dict):
        sn = nm = md = None
        for k, v in obj.items():
            if not isinstance(v, str):
                continue
            kl = k.lower()
            val = v.strip()
            if len(val) < 2:
                continue
            if kl in FIO_SURNAME_KEYS and sn is None:
                sn = val
            elif kl in FIO_NAME_KEYS and nm is None:
                nm = val
            elif kl in FIO_MIDDLE_KEYS and md is None:
                md = val
        if sn and nm:
            parts = [sn, nm] + ([md] if md else [])
            results.append(" ".join(parts))
        for v in obj.values():
            results.extend(assemble_fio(v))
    elif isinstance(obj, list):
        for it in obj:
            results.extend(assemble_fio(it))
    return results

def _first(values):
    return values[0].strip() if values else None

def _ensure_prefix(val, prefixes, prefix):
    v = val.strip()
    low = v.lower()
    for p in prefixes:
        if low.startswith(p):
            return v
    return f"{prefix} {v}"

def build_full_address(rec) -> list:
    results = []
    for full in collect_values_by_keys(rec, ADDR_KEYS['full']):
        s = full.strip()
        if len(s) >= 15 and not is_label_value(s):
            results.append(s)

    postal    = _first(collect_values_by_keys(rec, ADDR_KEYS['postal']))
    country   = _first(collect_values_by_keys(rec, ADDR_KEYS['country']))
    region    = _first(collect_values_by_keys(rec, ADDR_KEYS['region']))
    city      = _first(collect_values_by_keys(rec, ADDR_KEYS['city']))
    street    = _first(collect_values_by_keys(rec, ADDR_KEYS['street']))
    house     = _first(collect_values_by_keys(rec, ADDR_KEYS['house']))
    apartment = _first(collect_values_by_keys(rec, ADDR_KEYS['apartment']))

    parts_count = sum(bool(x) for x in [postal, region, city, street, house])
    if parts_count < 2:
        return results

    parts = []
    if postal:    parts.append(postal)
    if country:   parts.append(country)
    if region:    parts.append(_ensure_prefix(region, ('обл', 'респ', 'край', 'г.', 'м.'), 'обл.'))
    if city:      parts.append(_ensure_prefix(city, ('г.', 'город', 'м.', 'пгт', 'с.', 'п.'), 'г.'))
    if street:
        parts.append(_ensure_prefix(
            street,
            ('ул', 'пр', 'пер', 'шос', 'б-р', 'бул', 'наб', 'пл', 'проезд', 'аллея', 'тракт'),
            'ул.'
        ))
    if house:     parts.append(_ensure_prefix(house, ('д.', 'дом', 'стр', 'корп', 'буд'), 'д.'))
    if apartment: parts.append(_ensure_prefix(apartment, ('кв.', 'квартира', 'оф', 'ком'), 'кв.'))

    combined = re.sub(r'\s+', ' ', " ".join(p for p in parts if p).strip())
    if len(combined) >= 15:
        results.append(combined)
    return results

def parse_date(s):
    for fmt in ('%d.%m.%Y', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

def compute_age(birth_str):
    b = parse_date(birth_str)
    if not b:
        return None
    today = date.today()
    if b > today:
        return None
    years = today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    if years < 0 or years > 120:
        return None
    return years

def plural_years(n):
    n = abs(n)
    if 11 <= n % 100 <= 14:
        return 'лет'
    d = n % 10
    if d == 1: return 'год'
    if 2 <= d <= 4: return 'года'
    return 'лет'

def extract_tg_groups(obj, out=None):
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = k.lower()
            if kl in TG_GROUP_LIST_KEYS and isinstance(v, list):
                for item in v:
                    if not isinstance(item, dict):
                        continue
                    name = None
                    username = None
                    for ik, iv in item.items():
                        if not isinstance(iv, str):
                            continue
                        ikl = ik.lower()
                        vv = iv.strip()
                        if not vv:
                            continue
                        if name is None and ikl in TG_GROUP_NAME_KEYS:
                            name = vv
                        elif username is None and ikl in TG_GROUP_USERNAME_KEYS:
                            username = vv
                    if name or username:
                        if name and username:
                            out.append(f"{name} ({username})")
                        elif name:
                            out.append(name)
                        else:
                            out.append(username)
            if isinstance(v, (dict, list)):
                extract_tg_groups(v, out)
    elif isinstance(obj, list):
        for it in obj:
            extract_tg_groups(it, out)
    return out

def detect_operator(phone):
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits[0] in '78':
        return OPERATOR_PREFIXES.get(digits[1:4])
    return None

def detect_bank(card):
    if not card:
        return None
    digits = re.sub(r'\D', '', card)
    if len(digits) < 6:
        return None
    return BANK_BINS.get(digits[:4])

def extract_city(address):
    if not address:
        return None
    m = re.search(r'(?:г\.|город)\s+([А-ЯЁЇІЄҐ][а-яёїієґ\-]+)', address)
    if m:
        return m.group(1)
    m = re.search(r'\b([А-ЯЁЇІЄҐ][а-яёїієґ\-]{3,})\s+(?:обл|край|респ)', address)
    if m:
        return m.group(1)
    return None

# ============ АНАЛИЗ И СКОРИНГ ============
def analyze_with_confidence(parsed_json) -> dict:
    records = extract_records(parsed_json)
    total_sources = max(1, len(records))
    found = defaultdict(lambda: defaultdict(set))

    for idx, rec in enumerate(records):
        text = record_to_text(rec)

        for cat, rx in RX.items():
            for m in rx.findall(text):
                val = m.strip()
                if not val:
                    continue
                if cat == 'fio' and not looks_like_fio(val):
                    continue
                if cat == 'address' and (is_label_value(val) or len(val) < 15):
                    continue
                if cat == 'card':
                    digits = re.sub(r'\D', '', val)
                    if len(digits) < 12:
                        continue
                found[cat][val].add(idx)

        for v in collect_values_by_keys(rec, FIO_FULL_KEYS):
            if looks_like_fio(v):
                found['fio'][v].add(idx)
        for v in assemble_fio(rec):
            if looks_like_fio(v):
                found['fio'][v].add(idx)

        for v in build_full_address(rec):
            found['address'][v].add(idx)

        for v in collect_values_by_keys(rec, BIRTH_KEYS):
            for m in RX['date'].findall(v):
                found['birth_date'][m].add(idx)

        for g in extract_tg_groups(rec):
            found['tg_group'][g].add(idx)

    if not found['birth_date'] and found['date']:
        candidates = []
        for d_str, srcs in found['date'].items():
            dd = parse_date(d_str)
            if dd and 1930 <= dd.year <= 2010:
                candidates.append((d_str, dd.year, srcs))
        if candidates:
            earliest = min(candidates, key=lambda x: x[1])
            found['birth_date'][earliest[0]] |= earliest[2]

    for bd, srcs in found['birth_date'].items():
        age = compute_age(bd)
        if age is not None:
            found['age'][f"{age} {plural_years(age)}"] |= srcs

    fio_map = found['fio']
    if fio_map:
        vals = sorted(fio_map.keys(), key=len, reverse=True)
        keep = []
        for v in vals:
            merged = False
            for k in keep:
                if v != k and v in k:
                    fio_map[k] |= fio_map[v]
                    merged = True
                    break
            if not merged:
                keep.append(v)
        for v in list(fio_map.keys()):
            if v not in keep:
                del fio_map[v]

    addr_map = found['address']
    if addr_map:
        vals = sorted(addr_map.keys(), key=len, reverse=True)
        keep = []
        for v in vals:
            merged = False
            for k in keep:
                if v != k and v in k:
                    addr_map[k] |= addr_map[v]
                    merged = True
                    break
            if not merged:
                keep.append(v)
        for v in list(addr_map.keys()):
            if v not in keep:
                del addr_map[v]

    scored = {}
    for cat, values in found.items():
        cfg = TYPE_CONFIG.get(cat, {'base': 3.0, 'mult': 1.0})
        items = []
        for val, sources in values.items():
            src_count = len(sources)
            score = cfg['base'] * cfg['mult'] * math.log2(1 + src_count) * 10

            if cat == 'address':
                score *= min(2.5, 1.0 + len(val) / 40.0)
            elif cat == 'card' and '*' not in val:
                score *= 1.8
            elif cat == 'fio':
                words = len(val.split())
                if words >= 3:
                    score *= 1.4
                elif words == 2:
                    score *= 0.9
            elif cat == 'age':
                score *= 0.9
            elif cat == 'tg_group':
                if '(' in val:
                    score *= 1.15

            items.append((val, round(score, 1), src_count))
        items.sort(key=lambda x: x[1], reverse=True)
        scored[cat] = items

    all_scores = [it[1] for lst in scored.values() for it in lst]
    avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

    confirmed = []
    for cat, items in scored.items():
        for val, score, src in items:
            if src > 1:
                confirmed.append((cat, val, score, src))
    confirmed.sort(key=lambda x: x[2], reverse=True)

    return {
        'total_records': total_sources,
        'scored': scored,
        'confirmed': confirmed,
        'avg_score': avg_score,
    }

# ============ ВЫВОД В TELEGRAM ============
def bar(score, max_score=200.0, width=12):
    filled = int(min(1.0, score / max_score) * width)
    return "█" * filled + "░" * (width - filled)

def format_scored_section(title, items, empty_note="не найдено"):
    res = f"\n┌─ {title}\n"
    if not items:
        res += f"│ ({empty_note})\n"
        return res
    for val, score, src in items:
        tag = f"×{src} ист." if src > 1 else "×1 ист."
        res += f"│ [{score:>5.1f}] {bar(score)} {val} ({tag})\n"
    return res

def generate_report(scored_data, query):
    s = scored_data['scored']
    text = "<code>"
    text += "========================================\n"
    text += f"  ОТЧЁТ ПО ЗАПРОСУ: {query}\n"
    text += "========================================\n"

    text += "\n▼ ОСНОВНЫЕ ЛИЧНЫЕ ДАННЫЕ\n"
    text += format_scored_section("ФИО", s.get('fio', []))
    text += format_scored_section("Дата рождения", s.get('birth_date', []))
    text += format_scored_section("Возраст", s.get('age', []))
    text += format_scored_section("Даты (прочие)", s.get('date', []))

    text += "\n▼ ГОСУДАРСТВЕННЫЕ ДОКУМЕНТЫ\n"
    text += format_scored_section("Паспорт РФ", s.get('passport', []))
    text += format_scored_section("СНИЛС", s.get('snils', []))
    text += format_scored_section("ИНН", s.get('inn', []))
    text += format_scored_section("ОГРН / ОГРНИП", s.get('ogrn', []))

    text += "\n▼ КОНТАКТНЫЕ ДАННЫЕ\n"
    text += format_scored_section("Телефоны", s.get('phone', []))
    text += format_scored_section("Email", s.get('email', []))

    text += "\n▼ ЦИФРОВОЙ СЛЕД / СОЦСЕТИ\n"
    text += format_scored_section("Telegram (личные)", s.get('telegram', []))
    text += format_scored_section("Группы / каналы Telegram", s.get('tg_group', []))
    text += format_scored_section("Ссылки", s.get('url', []))

    text += "\n▼ АДРЕСА\n"
    text += format_scored_section("Адреса", s.get('address', []))

    text += "\n▼ ФИНАНСОВЫЕ ДАННЫЕ\n"
    text += format_scored_section("Карты", s.get('card', []))

    text += "\n▼ ИМУЩЕСТВО И ТРАНСПОРТ\n"
    text += format_scored_section("Госномера", s.get('gosnomer', []))
    text += format_scored_section("VIN", s.get('vin', []))
    text += "</code>"
    return text

def generate_final_summary_and_card(scored_data):
    scored = scored_data['scored']
    text = "<code>"
    text += "========================================\n"
    text += "  🏁 ИТОГ\n"
    text += "========================================\n"

    if not scored:
        text += "  (ничего не найдено)\n========================================\n</code>"
        return text

    LABELS = {
        'fio':        'фио', 'birth_date': 'др', 'age':        'возраст',
        'date':       'дата', 'phone':      'номер', 'email':      'email',
        'telegram':   'telegram', 'tg_group':   'группы', 'inn':        'инн',
        'snils':      'снилс', 'passport':   'паспорт', 'address':    'адрес',
        'gosnomer':   'госномер', 'vin':        'vin', 'card':       'карта',
        'ogrn':       'огрн', 'url':        'ссылка',
    }
    order = ['фио', 'др', 'возраст', 'номер', 'email', 'telegram',
             'инн', 'снилс', 'паспорт', 'адрес', 'госномер', 'vin',
             'карта', 'огрн', 'ссылка', 'дата']

    grouped = {}
    for cat, items in scored.items():
        if items:
            best_val, best_score, best_src = items[0]
            label = LABELS.get(cat, cat)
            grouped[label] = (best_val, best_src)

    for label in order:
        if label in grouped:
            val, src = grouped[label]
            if label == 'др' and 'возраст' in grouped:
                age_str = grouped['возраст'][0]
                text += f"  {label}: {val}  ({age_str})\n"
            elif label == 'возраст':
                if 'др' in grouped:
                    continue
                text += f"  {label}: {val}\n"
            else:
                text += f"  {label}: {val}\n"

    tg_groups = scored.get('tg_group', [])
    if tg_groups:
        text += "----------------------------------------\n"
        text += f"  группы/каналы ({len(tg_groups)}):\n"
        for val, score, src in tg_groups:
            text += f"    • {val}\n"

    all_items = [it for lst in scored.values() for it in lst]
    total = len(all_items)
    if total:
        multi_src = sum(1 for it in all_items if it[2] > 1)
        ratio = multi_src / total
        avg = sum(it[1] for it in all_items) / total
        confidence = min(100.0, (avg / 150.0) * 60 + ratio * 100 * 0.4)
        confidence = round(confidence, 1)
    else:
        confidence = 0.0

    if confidence >= 75: mark = "🟢"
    elif confidence >= 50: mark = "🟡"
    elif confidence >= 25: mark = "🟠"
    else: mark = "🔴"

    text += "----------------------------------------\n"
    text += f"  уверенность: {confidence}%  {mark}\n"
    text += "========================================\n"

    # Карточка
    def top(cat):
        lst = scored.get(cat, [])
        return lst[0][0] if lst else None

    phone   = top('phone')
    fio     = top('fio')
    bdate   = top('birth_date')
    age_str = top('age')
    email   = top('email')
    address = top('address')
    card    = top('card')
    tg      = top('telegram')
    url     = top('url')

    city = extract_city(address) if address else None
    vk = url.replace('https://', '').replace('http://', '') if url and 'vk.com' in url else None
    operator = detect_operator(phone)
    bank = detect_bank(card)

    age_num = None
    if age_str:
        m = re.match(r'(\d+)', age_str)
        if m: age_num = m.group(1)

    text += "\n----------------------------------------\n"
    text += "  🪪  К А Р Т О Ч К А   О Б Ъ Е К Т А\n"
    text += "----------------------------------------\n"

    rows = [
        ("Номер",    phone), ("ФИО",      fio), ("Возраст",  age_num),
        ("Оператор", operator), ("Город",    city), ("Адрес",    address),
        ("Email",    email), ("Telegram", tg), ("VK",       vk),
        ("Карта",    card), ("Банк",      bank),
    ]

    for label, val in rows:
        if val:
            text += f"  {label:<10}: {val}\n"

    text += "----------------------------------------\n"
    text += "</code>"
    return text

# ============ BIGBASE REQUEST С ПРОКСИ ============
def bb_request(endpoint, payload):
    url = f"{API_BASE}/{endpoint}"
    headers = {"Authorization": BIGBASE_TOKEN, "Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, proxies=PROXIES, timeout=40)
    r.raise_for_status()
    return r.text

def parse_safe(raw):
    try:
        return json.loads(raw)
    except Exception:
        return {"_raw": raw}

# ============ ОБРАБОТЧИКИ ТЕЛЕГРАМ ============
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message, 
        "Здрaвcтвуйтe, вeдитe зaпр0c: тeлeф0н, тг, фи0, cни1c и т.д.\n\n"
         
        
        
    )

@bot.message_handler(func=lambda message: True)
def process_search(message):
    query = message.text.strip()
    if not query:
        return

    status_msg = bot.reply_to(message, "0жuдайте")

    try:
        raw = bb_request("search", {"search": query, "page": 0})
        bot.edit_message_text("Дaнныe_0бpaбaтывaютcя...", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        parsed = parse_safe(raw)
        scored = analyze_with_confidence(parsed)

        report_text = generate_report(scored, query)
        summary_text = generate_final_summary_and_card(scored)

        bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)

        # Разделение больших текстовых сообщений
        if len(report_text) > 4000:
            for x in range(0, len(report_text), 4000):
                bot.send_message(message.chat.id, report_text[x:x+4000], parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, report_text, parse_mode="HTML")

        bot.send_message(message.chat.id, summary_text, parse_mode="HTML")

    except Exception as e:
        bot.edit_message_text(f"Произошла ошибка при обработке запроса: {e}", chat_id=message.chat.id, message_id=status_msg.message_id)

if __name__ == "__main__":
    print("Бот успешно запущен и готов к работе.")
    bot.infinity_polling(timeout=30, long_polling_timeout=10)