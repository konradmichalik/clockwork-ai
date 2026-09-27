"""Pre-generate clockwork poems with a local Ollama model and keep only the best candidates.

Runs once a day before the clock starts. Writes OUT/YYYY-MM-DD/HH/HHMM.json (a list of
poems, read by clockwork as daily poems) plus OUT/report.json with every candidate and the
reason it was rejected.
"""

import argparse
import json
import random
import re
import sys
import time
import urllib.request
from datetime import date
from collections import Counter
from pathlib import Path

SYSTEM_PROMPT = (
    "Du bist eine poetische Uhr. Schreibe zur genannten Uhrzeit ein Gedicht aus genau zwei Zeilen "
    "mit höchstens 25 Wörtern. Die Uhrzeit steht genau einmal und genau so in Ziffern im Gedicht, "
    "wie sie genannt wird, zum Beispiel 07:42, und zwar nicht am Ende einer Zeile. Schreibe keine "
    "Zahlen als Wörter aus. Die beiden Zeilen reimen sich am Ende, ohne dasselbe Reimwort zu "
    "verwenden. Das Gedicht passt zur genannten Tageszeit und greift das genannte Motiv auf. "
    "Jahreszeit und Wetter sind Hintergrund, sie dürfen anklingen, müssen aber nicht genannt werden. "
    "Antworte nur mit den zwei Zeilen, ohne Markdown, ohne Anführungszeichen, ohne Erklärungen."
)
DAYTIMES = [
    (5, "Nacht"), (8, "früher Morgen"), (11, "Vormittag"), (14, "Mittag"),
    (17, "Nachmittag"), (20, "Abend"), (22, "später Abend"), (24, "Nacht"),
]
MOTIFS = [
    "Kaffee", "Bahnhof", "Katze", "Fahrrad", "Brief", "Garten", "Küche", "Brücke",
    "Buch", "Wind", "Meer", "Wald", "Stadt", "Kerze", "Nachbar", "Zug", "Markt", "Vogel",
    "Wolke", "Fenster", "Straße", "Tee", "Musik", "Hund", "Bäckerei", "Apfel",
    "Laterne", "Fluss", "Telefon", "Treppe", "Kind", "Blume", "Berg", "Hafen",
]
NUMBER_WORD = re.compile(
    r"\b(zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|\w*(zehn|zwanzig|dreißig|vierzig|fünfzig))\b",
    re.IGNORECASE,
)
# Longer poems shrink the font on the display. 110 characters keep it at the size most
# of the previous gpt-4o-mini poems had on the 7.5 inch display.
MAX_CHARS = 110
VOWELS = "aeiouäöüy"
# Umlauts and common spellings that rhyme in spoken German.
RHYME_NORMALIZE = str.maketrans({"ä": "e", "ö": "e", "ü": "i", "y": "i"})


# Dresden, only the city coordinates leave the network.
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast?latitude=51.05&longitude=13.74"
    "&hourly=weather_code,temperature_2m,is_day&timezone=Europe%2FBerlin&forecast_days=1"
)
SEASONS = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Frühling", 4: "Frühling", 5: "Frühling",
           6: "Sommer", 7: "Sommer", 8: "Sommer", 9: "Herbst", 10: "Herbst", 11: "Herbst"}
TEMPERATURES = [(5, "kalt"), (12, "kühl"), (20, "mild"), (27, "warm"), (99, "heiß")]
# WMO weather codes, upper bound of each range.
CONDITIONS = [(1, "sonnig"), (2, "heiter"), (3, "bewölkt"), (48, "neblig"), (67, "regnerisch"),
              (77, "verschneit"), (82, "regnerisch"), (86, "verschneit"), (99, "gewittrig")]


def describe(temperature, code, is_day):
    feel = next(label for limit, label in TEMPERATURES if temperature < limit)
    condition = next(label for limit, label in CONDITIONS if code <= limit)
    if not is_day and condition in ("sonnig", "heiter"):
        condition = "klar"
    return f"{feel} und {condition}"


def forecast():
    """Today's hourly weather in Dresden as words, e.g. ['kühl und neblig', ...], or [] when unreachable."""
    try:
        with urllib.request.urlopen(WEATHER_URL, timeout=10) as response:
            hourly = json.load(response)["hourly"]
        return [describe(*hour) for hour in zip(hourly["temperature_2m"], hourly["weather_code"], hourly["is_day"])]
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(f"[warn] Wetter nicht verfügbar, weiter ohne: {error}", file=sys.stderr)
        return []


def background(clock_time, hourly_weather):
    parts = [SEASONS[date.today().month]]
    hour = int(clock_time[:2])
    if hour < len(hourly_weather):
        parts.append(f"Wetter: {hourly_weather[hour]}")
    return ", ".join(parts)


def chat(host, model, messages):
    body = json.dumps({"model": model, "stream": False, "messages": messages}).encode()
    request = urllib.request.Request(f"{host}/api/chat", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)["message"]["content"]


def daytime(clock_time):
    hour = int(clock_time[:2])
    return next(label for limit, label in DAYTIMES if hour < limit)


def clean(raw):
    lines = [line.strip().strip('"„“') for line in raw.replace("*", "").splitlines()]
    return [line for line in lines if line]


def last_word(line):
    words = re.findall(r"[\wäöüß']+", line.lower())
    return words[-1] if words else ""


def rhyme_core(word):
    """Last vowel group plus everything after it: 'sacht' -> 'acht', 'Traum' -> 'aum'."""
    word = word.rstrip("'").translate(RHYME_NORMALIZE)
    # Silent lengthening h: 'Uhr' rhymes with 'Flur'.
    word = re.sub(rf"([{VOWELS}])h(?=[^{VOWELS}]|$)", r"\1", word)
    # Final devoicing: 'Kleid' rhymes with 'bereit'.
    word = re.sub(r"[dbg]$", lambda m: {"d": "t", "b": "p", "g": "k"}[m.group(0)], word)
    # Unstressed endings like -en or -e carry no rhyme: 'klingen' must not rhyme with 'neigen'.
    pattern = rf"[{VOWELS}]+[^{VOWELS}]*(e[nrlms]?t?)?$"
    match = re.search(pattern, word) if re.search(r"e[nrlms]?t?$", word) else None
    match = match or re.search(rf"[{VOWELS}]+[^{VOWELS}]*$", word)
    return re.sub(r"(.)\1", r"\1", match.group(0)) if match else word


def rejection(lines, clock_time):
    if len(lines) != 2:
        return f"{len(lines)} Zeilen"
    text = " ".join(lines)
    if text.count(clock_time) != 1:
        return "Uhrzeit fehlt" if clock_time not in text else "Uhrzeit doppelt"
    if NUMBER_WORD.search(text):
        return "Zahl ausgeschrieben"
    if len("\n".join(lines)) > MAX_CHARS:
        return "zu lang"
    first, second = last_word(lines[0]), last_word(lines[1])
    if any(char.isdigit() for char in first + second):
        return "Uhrzeit am Zeilenende"
    if first == second:
        return "gleiches Reimwort"
    if rhyme_core(first) != rhyme_core(second):
        return f"kein Reim ({first}/{second})"
    return None


def content_words(poem):
    return set(re.findall(r"[a-zäöüß]{4,}", poem.lower()))


def repetition_score(poem, usage):
    """Lower is better: how often the poem's words were already used in accepted poems."""
    return sum(usage[word] for word in content_words(poem))


def candidate(args, clock_time, context):
    motif = random.choice(MOTIFS)
    prompt = f"{clock_time}, {daytime(clock_time)}, {context}, Motiv: {motif}"
    lines = clean(chat(args.host, args.model, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]))
    return {"prompt": prompt, "poem": "\n".join(lines), "rejected": rejection(lines, clock_time)}


def all_times(step, first_hour, last_hour):
    minutes = range(first_hour * 60, (last_hour + 1) * 60, step)
    return [f"{minute // 60:02d}:{minute % 60:02d}" for minute in minutes]


def write_storage(out, clock_time, poems):
    hour_dir = out / date.today().isoformat() / clock_time[:2]
    hour_dir.mkdir(parents=True, exist_ok=True)
    path = hour_dir / f"{clock_time.replace(':', '')}.json"
    path.write_text(json.dumps(poems, indent=4, ensure_ascii=False))


def generate(args):
    args.out.mkdir(parents=True, exist_ok=True)
    hourly_weather = forecast()
    print("Wetter:", ", ".join(f"{h:02d} {w}" for h, w in enumerate(hourly_weather)) or "keins")
    usage = Counter()
    report = []
    for clock_time in all_times(args.step, args.first_hour, args.last_hour):
        started = time.time()
        candidates = []
        for _ in range(args.candidates):
            try:
                candidates.append(candidate(args, clock_time, background(clock_time, hourly_weather)))
            except OSError as error:
                print(f"[error] {clock_time}: {error}", file=sys.stderr)

        valid = [c["poem"] for c in candidates if c["rejected"] is None]
        chosen = sorted(valid, key=lambda poem: repetition_score(poem, usage))[:args.keep]
        for poem in chosen:
            usage.update(content_words(poem))
        if chosen:
            write_storage(args.out, clock_time, chosen)

        report.append({"time": clock_time, "chosen": chosen, "candidates": candidates})
        print(f"{clock_time} {len(valid)}/{len(candidates)} gültig, {time.time() - started:.0f}s", flush=True)

    (args.out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    covered = sum(1 for entry in report if entry["chosen"])
    print(f"\nAbgedeckt: {covered}/{len(report)} Uhrzeiten")
    print("Häufigste Wörter:", ", ".join(f"{w} ({n})" for w, n in usage.most_common(10)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="http://macmini.local:11434")
    parser.add_argument("--model", default="gemma3:12b")
    parser.add_argument("--candidates", type=int, default=5)
    parser.add_argument("--keep", type=int, default=2, help="poems stored per time")
    parser.add_argument("--first-hour", type=int, default=6, help="clockwork shows poems from 06:00")
    parser.add_argument("--last-hour", type=int, default=22, help="inclusive, 22 means up to 22:55 like the cron job")
    parser.add_argument("--step", type=int, default=5, help="minutes between times, clockwork shows a new poem every 5")
    parser.add_argument("--out", type=Path, default=Path("var/daily"))
    generate(parser.parse_args())


if __name__ == "__main__":
    main()
