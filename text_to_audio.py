"""German text-to-speech with a small window. Needs internet and: pip install edge-tts gTTS"""
import asyncio
import os
import threading
import time
import tkinter as tk
# import urllib.error
# import urllib.parse
# import urllib.request
from datetime import datetime
from pathlib import Path
# from tkinter import simpledialog
from tkinter import messagebox, ttk

import edge_tts
from gtts import gTTS

OUTPUT_DIR = Path(__file__).parent / "output"
LOG_DIR = Path(__file__).parent / "Log"
LOG_KEEP_DAYS = 30
DEFAULT_AUDIO_NAME = "audio"
DEFAULT_TEXT_NAME = "text"
MICROSOFT_TRIES = 10  # the Microsoft server often drops connections, so keep trying
# Yandex is switched off for now. To restore it, uncomment every Yandex line in this file
# # The key stays one folder above this project, so it is outside git
# KEY_FILE = Path(__file__).parent.parent / "yandex_api_key.txt"
# YANDEX_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
# YANDEX_VOICE = "lea"
# YANDEX_MAX_CHARS = 5000
VOICES = {
    "Katja (female)": "de-DE-KatjaNeural",
    "Amala (female)": "de-DE-AmalaNeural",
    "Conrad (male)": "de-DE-ConradNeural",
    "Killian (male)": "de-DE-KillianNeural",
    # "Lea (female, Yandex)": YANDEX_VOICE,
}
# Measured pause lengths in seconds: short, long, and whether the long dash makes a pause
VOICE_PAUSES = {
    "Katja (female)": ("0.2", "0.9", True),
    "Amala (female)": ("0.2", "0.9", False),
    "Conrad (male)": ("0.2", "1.0", True),
    "Killian (male)": ("0.15", "0.9", False),
}
TIPS = """Tips for {voice}
Short pause (about {short} s):  ,  ;  :  ...  or space + hyphen ( - ). Long dash –: {dash}
Long pause (about {long} s):  .  !  ?  or a new line (Enter)
Stress: "word" in quotes = light, word! = stronger (adds a long pause after it)
Avoid: *word* and _word_. CAPITALS have almost no effect.
Length: no official limit. Long text is split automatically into parts of 4096 bytes."""
# YANDEX_TIPS = """Tips for Lea (female, Yandex)
# Needs a Yandex API key: press Add Yandex API. Yandex is a paid service.
# Pauses: use normal punctuation. Pause lengths were not measured for this voice.
# Stress: the Yandex + mark works only for Russian, not for German.
# Length: up to 5000 characters per message."""
FIRST_TEXT = """Diese Herbstferien waren sehr schön.
In der ersten Woche habe ich mit meiner Familie Berlin besucht. Wir haben eine Berlin-Discount-Karte gekauft, also haben wir fast alles gemacht: Wir sind mit dem Touristikbus gefahren, haben viele Museen besucht, sind mit dem Schiff gefahren und haben den berühmten Fernsehturm am Alexanderplatz besucht und mehr. Diese Reise war wirklich toll!
In der zweiten Woche waren wir zu Hause, weil mein Mann arbeiten musste. Und am letzten Wochenende haben wir den Zoo in Osnabrück besucht."""


def log(message):
    """Add a line to today's log file. Never log the API key or the user's text."""
    now = datetime.now()
    try:
        LOG_DIR.mkdir(exist_ok=True)
        with open(LOG_DIR / f"{now:%Y-%m-%d}.log", "a", encoding="utf-8") as file:
            file.write(f"{now:%H:%M:%S} {message}\n")
    except OSError:
        pass  # a log problem must not stop the app


def delete_old_logs():
    """Delete log files that are older than LOG_KEEP_DAYS days."""
    oldest_allowed = time.time() - LOG_KEEP_DAYS * 24 * 60 * 60
    for file in LOG_DIR.glob("????-??-??.log"):
        try:
            if file.stat().st_mtime < oldest_allowed:
                file.unlink()
                log(f"Deleted old log file {file.name}")
        except OSError:
            pass


def voice_tips(voice):
    """Return the tips text for a voice name from the dropdown."""
    # if voice not in VOICE_PAUSES:
        # return YANDEX_TIPS
    short, long, dash = VOICE_PAUSES[voice]
    return TIPS.format(voice=voice, short=short, long=long, dash="short pause" if dash else "no pause")


# class YandexError(Exception):
    # """A Yandex problem with a message the user can act on."""


# def load_yandex_key():
    # return KEY_FILE.read_text(encoding="utf-8").strip() if KEY_FILE.exists() else ""


# def save_yandex_key(key):
    # KEY_FILE.write_text(key, encoding="utf-8")


# def yandex_audio(text, path):
    # """Save speech from Yandex SpeechKit to an mp3 file."""
    # body = urllib.parse.urlencode({"text": text, "lang": "de-DE", "voice": YANDEX_VOICE, "format": "mp3"})
    # headers = {"Authorization": f"Api-Key {load_yandex_key()}"}
    # request = urllib.request.Request(YANDEX_URL, data=body.encode(), headers=headers)
    # try:
        # with urllib.request.urlopen(request, timeout=60) as response:
            # path.write_bytes(response.read())
    # except urllib.error.HTTPError as e:
        # if e.code in (401, 403):
            # raise YandexError("Yandex did not accept the API key. Press Add Yandex API and check it.") from None
        # raise YandexError(f"Yandex returned error {e.code}. Please try again later.") from None


def make_audio(text, voice, path):
    """Create an mp3 file. Return its path and the service that made it."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    # if voice == YANDEX_VOICE:
        # yandex_audio(text, path)
        # return path, "Yandex"
    for attempt in range(1, MICROSOFT_TRIES + 1):
        try:
            asyncio.run(edge_tts.Communicate(text, voice).save(str(path)))
            return path, "Microsoft"
        except Exception as e:
            log(f"Microsoft try {attempt} of {MICROSOFT_TRIES} failed: {type(e).__name__}")
            time.sleep(1)
    log("Microsoft failed, using Google")
    try:
        gTTS(text, lang="de").save(str(path))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path, "Google"


def main():
    delete_old_logs()
    log("App started")
    root = tk.Tk()
    root.title("German Text to Voice")
    root.geometry("560x540")
    last_file = None

    # Pack the bottom rows first, so the text box can never push them out of the window
    status = tk.Label(root, text="Enter German text and press Run.", anchor="w")
    status.pack(side="bottom", fill="x", padx=10, pady=8)

    controls = tk.Frame(root)
    controls.pack(side="bottom", fill="x", padx=10)
    ttk.Label(controls, text="Voice:").grid(row=0, column=0, sticky="w", pady=2)
    voice_box = ttk.Combobox(controls, values=list(VOICES), state="readonly", width=20)
    voice_box.current(0)
    voice_box.grid(row=0, column=1, sticky="w", padx=8, pady=2)
    ttk.Label(controls, text="Output audio name:").grid(row=1, column=0, sticky="w", pady=2)
    audio_name_box = ttk.Entry(controls, width=18)
    audio_name_box.insert(0, DEFAULT_AUDIO_NAME)
    audio_name_box.grid(row=1, column=1, sticky="w", padx=8, pady=2)
    ttk.Label(controls, text="Output text name:").grid(row=2, column=0, sticky="w", pady=2)
    text_name_box = ttk.Entry(controls, width=18)
    text_name_box.insert(0, DEFAULT_TEXT_NAME)
    text_name_box.grid(row=2, column=1, sticky="w", padx=8, pady=2)
    run_button = ttk.Button(controls, text="Run")
    run_button.grid(row=0, column=2, padx=8, pady=2)
    play_button = ttk.Button(controls, text="Play", state="disabled")
    play_button.grid(row=1, column=2, padx=8, pady=2)
    # yandex_button = ttk.Button(controls, text="Add Yandex API")
    # yandex_button.grid(row=2, column=2, padx=8, pady=2)

    tips = tk.Label(root, text=voice_tips(voice_box.get()), justify="left", anchor="w", wraplength=540)
    tips.pack(side="bottom", fill="x", padx=10)
    voice_box.bind("<<ComboboxSelected>>", lambda _: tips.config(text=voice_tips(voice_box.get())))

    text_box = tk.Text(root, wrap="word", font=("Segoe UI", 11), height=5)
    text_box.pack(fill="both", expand=True, padx=10, pady=10)
    text_box.insert("1.0", FIRST_TEXT)

    def finish(result, text_path, error):
        nonlocal last_file
        run_button.config(state="normal")
        if error:
            message = "Could not create audio. Check your internet and try again."
            if isinstance(error, PermissionError):
                message = "Could not overwrite the file. Close it in your player and try again."
            # status.config(text=str(error) if isinstance(error, YandexError) else message)
            status.config(text=message)
            return
        last_file, service = result
        play_button.config(state="normal")
        status.config(text=f"Saved: {last_file.name} and {text_path.name} in the output folder ({service} voice)")

    def work(text, voice, audio_path, text_path):
        log(f"Run: voice={voice}, characters={len(text)}, audio={audio_path.name}, text={text_path.name}")
        temp_path = audio_path.with_suffix(".tmp")  # the old audio stays safe if this run fails
        try:
            _, service = make_audio(text, voice, temp_path)
            temp_path.replace(audio_path)
            text_path.write_text(text, encoding="utf-8")
            result, error = (audio_path, service), None
            log(f"Saved {audio_path.name} and {text_path.name} ({service} voice)")
        except Exception as e:
            result, error = None, e
            temp_path.unlink(missing_ok=True)
            log(f"Run failed: {type(e).__name__}: {e}")
        root.after(0, finish, result, text_path, error)

    def output_path(name_box, suffix):
        """Return a file path from a name field, or None if the name can't be used."""
        name = name_box.get().strip().removesuffix(suffix)
        if not name or any(c in name for c in r'\/:*?"<>|'):
            status.config(text=r'Please enter a file name without \ / : * ? " < > |')
            return None
        return OUTPUT_DIR / f"{name}{suffix}"

    def overwrite_allowed(paths):
        """Ask before replacing existing files. Return True if it is OK to continue."""
        existing = [path.name for path in paths if path.exists()]
        if not existing:
            return True
        if len(existing) == 1:
            question = f"The output file {existing[0]} already exists. Do you want to overwrite it?"
        else:
            question = f"The output files {' and '.join(existing)} already exist. Do you want to overwrite them?"
        return messagebox.askyesno("Overwrite?", question, parent=root)

    def create():
        text = text_box.get("1.0", "end").strip()
        if not text:
            status.config(text="Please enter some text first.")
            return
        voice = VOICES[voice_box.get()]
        # if voice == YANDEX_VOICE and not load_yandex_key():
            # status.config(text="Please press Add Yandex API first.")
            # return
        # if voice == YANDEX_VOICE and len(text) > YANDEX_MAX_CHARS:
            # status.config(text=f"Yandex allows {YANDEX_MAX_CHARS} characters. Your text has {len(text)}.")
            # return
        audio_path = output_path(audio_name_box, ".mp3")
        text_path = audio_path and output_path(text_name_box, ".txt")
        if not text_path:
            return
        if not overwrite_allowed([audio_path, text_path]):
            status.config(text="Nothing was changed.")
            return
        run_button.config(state="disabled")
        status.config(text="Creating audio...")
        threading.Thread(target=work, args=(text, voice, audio_path, text_path), daemon=True).start()

    # def add_yandex_key():
        # key = simpledialog.askstring("Add Yandex API", "Paste your Yandex API key:", show="*", parent=root)
        # if key and key.strip():
            # save_yandex_key(key.strip())
            # log("Yandex API key saved")
            # status.config(text="Yandex API key saved on this computer only.")

    run_button.config(command=create)
    # yandex_button.config(command=add_yandex_key)
    play_button.config(command=lambda: os.startfile(last_file))
    root.mainloop()


if __name__ == "__main__":
    main()
