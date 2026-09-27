# clockwork/ai

![clockwork intro](img/intro.jpg)

>
> This project is inspired by creative mind Matt Web and his beautiful [Poem/1](https://poem.town/) clock. 
>

Simple DIY clock project to generate AI poems by current time using a raspberry pi zero + e-ink display.

![clockwork demo](img/demo.jpg)

- [General](#general)
    * [Daily poems](#daily-poems)
    * [Reuse](#reuse)
    * [Lock](#lock)
- [Installation](#installation)
    * [Hardware](#hardware)
    * [Preparation](#preparation)
    * [Prerequirements](#prerequirements)
    * [Software](#software)
    * [Permanent setup](#permanent-setup)
- [Configuration](#configuration)
    * [Local model](#local-model)
    * [Hardware support](#hardware-support)
    * [Prompt](#prompt)
    * [Validation](#validation)
    * [Show time](#show-time)
    * [Display rotation](#display-rotation)
    * [Coincidence](#coincidence)
    * [Font](#font)
    * [Debug](#debug)
- [Development](#development)
- [Project log](#project-log)
  * [Concept](#concept)
  * [Prototype](#prototype)
- [Disclaimer](#disclaimer)

## General

Currently forced for german language, but can be adjusted for custom usage, see [Configuration](#Configuration). 

### Features

- generate an AI poem about the current time and display them on an e-ink display
- display custom messages on the e-ink display
- clear the e-ink display

### Demo

See a live demo here: https://jackd248.github.io/clockwork-ai/.

### Commands

General command line functionalities of the python app:

- `python3 clockwork` - generates ai poem of current time
- `python3 clockwork 09:41` - generates ai poem of a requested time
- `python3 clockwork clear` - clear display
- `python3 clockwork demo` - demo poems to display
- `python3 clockwork display <text>` - display custom text
- `python3 clockwork ask <question>` - ask custom question to ai and display answer

The `--dry-run` option prevent the display process on the e-ink display and generates images instead under `var/debug/`.

### Daily poems

`tools/batch.py` pre-generates the poems for a whole day with a local model via [Ollama](https://ollama.com), for example once at night on a stronger machine than the Pi. Each request gets the daytime, the season, the hourly weather forecast for Dresden from [Open-Meteo](https://open-meteo.com) and a random motif as background. Several candidates per time are checked for two lines, the time in digits, a rhyme and a maximum length, so the font on the display does not shrink too much. The best ones are written to `var/daily/YYYY-MM-DD/HH/HHMM.json`.

```bash
python3 tools/batch.py --host http://localhost:11434 --model gemma3:12b --out var/daily
```

Copy the result to `var/daily/` on the Pi, e.g. with `rsync`. If a poem for today exists, clockwork shows it without calling the api. Days other than today are ignored. The script needs no dependencies beyond Python 3.9.

### Reuse

The fs component stores the received poems to json files, e.g. `var/storage/12/1245.json`. If the environment variable `CLOCKWORK_REUSE` is set to true, the algorithm randomly uses stored poems instead of calling the api to reuse them. 

If the api is not reachable, the script shows a stored poem if available for some kind of offline usage. 

### Lock

The file lock prevents the multiple execution of the python script, because this can result in display issues. 

## Installation

### Hardware

- raspberry pi zero wh
- [waveshare 2.13inch e-Paper](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT) or [waveshare 7.5inch e-Paper](https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT)


<img src="img/insight.jpg" alt="clockwork prototype" width="400"/>

### Preparation

- based on the waveshare [tutorial](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual)
  - see initialization and installation instructions for the raspberry and the needed libraries


### Prerequirements

- get an api key from openai: https://platform.openai.com/api-keys

### Software

```bash
# get python app
git clone https://github.com/jackd248/clockwork-ai.git
cd clockwork-ai
# install python requirements
pip3 install -r requirements.txt
# prepare settings
cp .env.dist .env
# run demo
python3 clockwork demo
```

You need to store your openai api key as environment variable within the `.env` file:

```dotenv
OPENAI_API_KEY='xxx'
```

Run the clockwork script to generate a poem:

```bash
python3 clockwork
```

### Permanent setup

Set up a periodic cronjob to update the poem e.g. every minute:

```bash
crontab -e
```

```cronexp
* * * * * python3 /path/to/clockwork/dir clockwork
```

Or set up a cronjob to update the poem on daytime:

```cronexp
* 06-23 * * * python3 /path/to/clockwork/dir clockwork
10 23 * * * python3 /path/to/clockwork/dir clockwork clear
```

> Note that you should clear the e-ink screen to avoid display issues.


> I would suggest to clear the screen if the display is not used for a longer time, e.g. at night.


## Configuration

All further configuration options are available within your `.env` file.

The 3.5 model is stored as default model for the openai api because it's the cheapest one so far. If you want to use another model, adjust the `OPENAI_API_MODEL` environment variable. See https://platform.openai.com/docs/models.

### Local model

The api client works with every OpenAI compatible server. To use a local model via [Ollama](https://ollama.com) instead of openai, point `OPENAI_BASE_URL` to it. Ollama ignores the api key, but it must not be empty:

```dotenv
OPENAI_BASE_URL="http://192.168.178.140:11434/v1"
OPENAI_API_KEY="ollama"
OPENAI_API_MODEL="gemma3:12b"
```

### Hardware support

Currently, the both displays are supported:

- 2.13inch e-Paper: `epd2in13`
- 7.5inch e-Paper: `epd7in5`

Change the `CLOCKWORK_DISPLAY` environment variable to the used hardware component.

### Prompt

You can adjust the default openai prompt to adjust the poem results or the desired language if you edit the environment variable `OPENAI_CLOCKWORK_SYSTEM_PROMPT` within your `.env` file:
```dotenv
OPENAI_CLOCKWORK_PROMPT="You are a clock that shows the time in a two-line poem."
```

### Validation

To improve the poem results by the ai, you can validate the response from the api again by the ai enabling the environment variable `CLOCKWORK_VALIDATE`. Therefore, a second request is sent to openai with the initial conversation messages and additional the `OPENAI_CLOCKWORK_VALIDATION_PROMPT`. 

### Show time

If you want to compare current time with the generated poem, activate the `CLOCKWORK_SHOW_TIME` environment variable to display the time in the bottom right corner.

### Display rotation

Use the `CLOCKWORK_ROTATE` environment variable to define the degree of rotation, e.g. 180.

### Font

Download a custom TrueType font (e.g. at https://fonts2u.com/), save them within the `font` directory and adjust the `CLOCKWORK_FONT` environment variable to adjust the displayed font.

### Coincidence

To influence the random function for choosing between api request and storage, set and increase the `CLOCKWORK_RANDOM_FACTOR` environment variable with an integer. Normally, it's 1 (api) to 1 (storage) as ratio. To increase the usage of the storage increase the env var, e.g. to 8 for 1 (api) to 8 (storage). Daily poems always take precedence.

### Debug

Use the environment variable `CLOCKWORK_DEBUG` to enable file log for more debug information under e.g. `var/log/app_2024-02-23.log`. 

Also, a little dot is displayed in the upper right corner if a poem is reused instead of calling the openai api.

## Development

Use [docker](https://www.docker.com/) and [docker-compose](https://docs.docker.com/compose/) for a development context to work on the app.

Build docker container:

```bash
docker compose up --build
```

Run python app within dev service:

```bash
docker-compose run dev
$ python3 clockwork demo --dry-run
$ python3 clockwork display "Test" --dry-run
```

Use pylint to improve code quality:
```bash
docker-compose run dev
$ pylint clockwork
```

## Project log

### Concept

This graphic shows the request chain for generating the AI poem by the chatgpt api:

<img src="img/concept.png" alt="clockwork concept" width="400"/>

### Prototype

The following pictures show the iterations of the prototype.

*Version 1:* simple prototype with a raspberry pi zero and the 2.13inch e-Paper display

<img src="img/version1.jpg" alt="version1" width="400"/>

*Version 2:* using a pwnagotchi case

<img src="img/version2.jpg" alt="version2" width="400"/>

*Version 3:* using a bigger 7.5inch e-Paper display and simple ikea picture frame

<img src="img/version3.jpg" alt="version3" width="400"/>

## Disclaimer

The waveshare libraries are part of the [e-Paper](https://github.com/waveshareteam/e-Paper) repository. 