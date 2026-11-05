"""German text-to-speech app. Needs internet and: pip install -r requirements.txt"""
import asyncio
import os
import sys
import threading
import time
# import urllib.error
# import urllib.parse
# import urllib.request
from datetime import datetime
from pathlib import Path
# from tkinter import simpledialog
from tkinter import messagebox

import customtkinter as ctk
import edge_tts
from gtts import gTTS
from PIL import Image

# In the .exe, __file__ points to a temporary folder, so saved files go next to the .exe instead
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
ASSETS_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets"
OUTPUT_DIR = APP_DIR / "output"
LOG_DIR = APP_DIR / "Log"
LOG_KEEP_DAYS = 30
DEFAULT_AUDIO_NAME = "audio"
DEFAULT_TEXT_NAME = "text"
MICROSOFT_TRIES = 10  # the Microsoft server often drops connections, so keep trying
# Yandex is switched off for now. To restore it, uncomment every Yandex line in this file
# # The key stays one folder above this project, so it is outside git
# KEY_FILE = APP_DIR.parent / "yandex_api_key.txt"
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
# Colors are (light mode, dark mode)
BACKGROUND = ("#F3F5F7", "#14171C")
CARD = ("#FFFFFF", "#1E2229")
BORDER = ("#E2E6EB", "#2E343D")
FIELD = ("#F8FAFB", "#262B33")
TEXT = ("#1B2129", "#EDF0F3")
MUTED = ("#5F6B7A", "#9AA5B1")
ACCENT = ("#0F766E", "#0D9488")
ACCENT_HOVER = ("#115E59", "#0F766E")
SUCCESS = ("#0F766E", "#2DD4BF")
ERROR = ("#B42318", "#F97066")
# YANDEX_TIPS = [
    # ("Key", "Needs a Yandex API key: press Add Yandex API. Yandex is a paid service."),
    # ("Pauses", "Use normal punctuation. Pause lengths were not measured for this voice."),
    # ("Stress", "The Yandex + mark works only for Russian, not for German."),
    # ("Avoid", "Nothing known."),
    # ("Length", "Up to 5000 characters per message."),
# ]
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
    """Return the tips for a voice name from the dropdown, as (title, text) rows."""
    # if voice not in VOICE_PAUSES:
        # return YANDEX_TIPS
    short, long, dash = VOICE_PAUSES[voice]
    return [
        ("Short pause", f"About {short} s:  ,  ;  :  ...  or space + hyphen ( - ). Long dash –: {'short pause' if dash else 'no pause'}"),
        ("Long pause", f"About {long} s:  .  !  ?  or a new line (Enter)"),
        ("Stress", '"word" in quotes = light, word! = stronger (adds a long pause after it)'),
        ("Avoid", "*word* and _word_. CAPITALS have almost no effect."),
        ("Length", "No official limit. Long text is split automatically into parts of 4096 bytes."),
    ]


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
    ctk.set_appearance_mode("system")
    root = ctk.CTk(fg_color=BACKGROUND)
    root.title("German Text to Speech")
    root.iconbitmap(str(ASSETS_DIR / "icon.ico"))
    root.geometry("660x800")
    root.minsize(660, 700)
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)  # only the text box grows with the window
    last_file = None

    def font(size, weight="normal"):
        return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)

    def card(row, expand=False):
        frame = ctk.CTkFrame(root, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14)
        frame.grid(row=row, column=0, sticky="nsew" if expand else "ew", padx=20, pady=(0, 12))
        return frame

    def field_title(parent, text):
        return ctk.CTkLabel(parent, text=text, font=font(12, "bold"), text_color=MUTED, anchor="w")

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 14))
    logo = ctk.CTkImage(Image.open(ASSETS_DIR / "icon.png"), size=(46, 46))
    ctk.CTkLabel(header, image=logo, text="").grid(row=0, column=0, rowspan=2, padx=(0, 12))
    ctk.CTkLabel(header, text="German Text to Speech", font=font(21, "bold"), text_color=TEXT, anchor="w", height=28).grid(
        row=0, column=1, sticky="w"
    )
    ctk.CTkLabel(header, text="Turn German text into a voice message", font=font(13), text_color=MUTED, anchor="w", height=20).grid(
        row=1, column=1, sticky="w"
    )

    text_card = card(1, expand=True)
    text_card.grid_columnconfigure(0, weight=1)
    text_card.grid_rowconfigure(1, weight=1)
    field_title(text_card, "YOUR TEXT").grid(row=0, column=0, sticky="w", padx=16, pady=(10, 2))
    text_box = ctk.CTkTextbox(text_card, wrap="word", font=font(15), fg_color=FIELD, text_color=TEXT, corner_radius=10, height=120)
    text_box.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
    text_box.insert("1.0", FIRST_TEXT)

    tips_card = card(2)
    tips_card.grid_columnconfigure(1, weight=1)
    tips_title = field_title(tips_card, "")
    tips_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 2))
    tip_values = []
    for row, (title, _) in enumerate(voice_tips(next(iter(VOICES))), start=1):
        last_pad = 10 if row == 5 else 1
        ctk.CTkLabel(tips_card, text=title, font=font(12, "bold"), text_color=TEXT, anchor="nw", height=18).grid(
            row=row, column=0, sticky="nw", padx=(16, 10), pady=(0, last_pad)
        )
        value = ctk.CTkLabel(tips_card, text="", font=font(12), text_color=MUTED, anchor="nw", justify="left", wraplength=500, height=18)
        value.grid(row=row, column=1, sticky="nw", padx=(0, 14), pady=(0, last_pad))
        tip_values.append(value)

    def show_tips(voice):
        tips_title.configure(text=f"TIPS FOR {voice.upper()}")
        for label, (_, text) in zip(tip_values, voice_tips(voice)):
            label.configure(text=text)

    settings = card(3)
    settings.grid_columnconfigure((0, 1, 2), weight=1, uniform="settings")
    field_title(settings, "Voice").grid(row=0, column=0, sticky="w", padx=(16, 6), pady=(8, 0))
    field_title(settings, "Output audio name").grid(row=0, column=1, sticky="w", padx=6, pady=(8, 0))
    field_title(settings, "Output text name").grid(row=0, column=2, sticky="w", padx=(6, 16), pady=(8, 0))
    voice_box = ctk.CTkOptionMenu(
        settings, values=list(VOICES), command=show_tips, font=font(14), dropdown_font=font(14), height=36, corner_radius=10,
        fg_color=FIELD, text_color=TEXT, button_color=FIELD, button_hover_color=BORDER,
        dropdown_fg_color=CARD, dropdown_text_color=TEXT, dropdown_hover_color=BORDER,
    )
    voice_box.grid(row=1, column=0, sticky="ew", padx=(14, 6), pady=(0, 14))

    def name_field(column, value, padx):
        box = ctk.CTkEntry(settings, font=font(14), height=36, corner_radius=10, fg_color=FIELD, text_color=TEXT, border_color=BORDER)
        box.insert(0, value)
        box.grid(row=1, column=column, sticky="ew", padx=padx, pady=(0, 14))
        return box

    audio_name_box = name_field(1, DEFAULT_AUDIO_NAME, 6)
    text_name_box = name_field(2, DEFAULT_TEXT_NAME, (6, 14))

    actions = ctk.CTkFrame(root, fg_color="transparent")
    actions.grid(row=4, column=0, sticky="ew", padx=20)
    actions.grid_columnconfigure(0, weight=1)
    run_button = ctk.CTkButton(
        actions, text="Run", font=font(16, "bold"), height=46, corner_radius=12, fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="white",
    )
    run_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))
    play_button = ctk.CTkButton(
        actions, text="Play", font=font(16), width=120, height=46, corner_radius=12, state="disabled", fg_color="transparent",
        hover_color=BORDER, border_width=1, border_color=BORDER, text_color=TEXT, text_color_disabled=MUTED,
    )
    play_button.grid(row=0, column=1)
    # yandex_button = ctk.CTkButton(actions, text="Add Yandex API", font=font(14), height=46, corner_radius=12)
    # yandex_button.grid(row=0, column=2, padx=(10, 0))

    progress = ctk.CTkProgressBar(root, mode="indeterminate", height=4, progress_color=ACCENT, fg_color=BORDER)
    progress.grid(row=5, column=0, sticky="ew", padx=20, pady=(10, 0))
    progress.grid_remove()
    status_label = ctk.CTkLabel(root, font=font(13), anchor="w", justify="left", wraplength=610, height=22)
    status_label.grid(row=6, column=0, sticky="ew", padx=22, pady=(8, 14))

    def status(text, color=MUTED):
        status_label.configure(text=text, text_color=color)

    def busy(active):
        run_button.configure(state="disabled" if active else "normal", text="Creating audio..." if active else "Run")
        if active:
            progress.grid()
            progress.start()
        else:
            progress.stop()
            progress.grid_remove()

    show_tips(voice_box.get())
    status("Enter German text and press Run.")

    def finish(result, text_path, error):
        nonlocal last_file
        busy(False)
        if error:
            message = "Could not create audio. Check your internet and try again."
            if isinstance(error, PermissionError):
                message = "Could not overwrite the file. Close it in your player and try again."
            # message = str(error) if isinstance(error, YandexError) else message
            status(message, ERROR)
            return
        last_file, service = result
        play_button.configure(state="normal")
        status(f"Saved: {last_file.name} and {text_path.name} in the output folder ({service} voice)", SUCCESS)

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
            status(r'Please enter a file name without \ / : * ? " < > |', ERROR)
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
            status("Please enter some text first.", ERROR)
            return
        voice = VOICES[voice_box.get()]
        # if voice == YANDEX_VOICE and not load_yandex_key():
            # status("Please press Add Yandex API first.", ERROR)
            # return
        # if voice == YANDEX_VOICE and len(text) > YANDEX_MAX_CHARS:
            # status(f"Yandex allows {YANDEX_MAX_CHARS} characters. Your text has {len(text)}.", ERROR)
            # return
        audio_path = output_path(audio_name_box, ".mp3")
        text_path = audio_path and output_path(text_name_box, ".txt")
        if not text_path:
            return
        if not overwrite_allowed([audio_path, text_path]):
            status("Nothing was changed.")
            return
        busy(True)
        status("Creating audio...")
        threading.Thread(target=work, args=(text, voice, audio_path, text_path), daemon=True).start()

    # def add_yandex_key():
        # key = simpledialog.askstring("Add Yandex API", "Paste your Yandex API key:", show="*", parent=root)
        # if key and key.strip():
            # save_yandex_key(key.strip())
            # log("Yandex API key saved")
            # status("Yandex API key saved on this computer only.", SUCCESS)

    run_button.configure(command=create)
    # yandex_button.configure(command=add_yandex_key)
    play_button.configure(command=lambda: os.startfile(last_file))
    root.mainloop()


if __name__ == "__main__":
    main()
