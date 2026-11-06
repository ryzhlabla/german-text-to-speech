"""German text-to-speech app. Needs internet and: pip install -r requirements.txt"""
import asyncio
import ctypes
import json
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
import requests
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
# Telegram settings stay one folder above this project, so they are outside git
TELEGRAM_FILE = APP_DIR.parent / "telegram_settings.json"
TELEGRAM_URL = "https://api.telegram.org"
TELEGRAM_TRIES = 3
CAPTION_WORDS = 5
TELEGRAM_HINT = "Click to send. Right-click to change Telegram settings."
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


def mci(command):
    """Send a command to the audio player built into Windows and return its answer."""
    answer = ctypes.create_unicode_buffer(128)
    error = ctypes.windll.winmm.mciSendStringW(command, answer, 128, None)
    if error:
        raise OSError(f"Windows audio error {error}")
    return answer.value


class TelegramError(Exception):
    """A Telegram problem with a message the user can act on."""

    def __init__(self, message, settings_problem=False):
        super().__init__(message)
        self.settings_problem = settings_problem


def load_telegram_settings():
    """Return the saved bot token and chat, or None if there is no token yet."""
    try:
        settings = json.loads(TELEGRAM_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return settings if settings.get("token") else None


def save_telegram_settings(settings):
    TELEGRAM_FILE.write_text(json.dumps(settings), encoding="utf-8")


def telegram_caption(text):
    """Return the first words of the text, followed by three dots."""
    return " ".join(text.split()[:CAPTION_WORDS]).rstrip(".,;:!?-–…") + "..."


def telegram_chat(chat):
    """Accept @name, name, a t.me link or a number, and return what Telegram expects."""
    chat = chat.strip().removeprefix("https://t.me/").removeprefix("t.me/")
    if not chat or chat.startswith("@") or chat.lstrip("-").isdigit():
        return chat
    return f"@{chat}"


def telegram_request(settings, method, **kwargs):
    """Call the Telegram Bot API. The URL holds the token, so never log or show request errors."""
    url = f"{TELEGRAM_URL}/bot{settings['token']}/{method}"
    for attempt in range(1, TELEGRAM_TRIES + 1):
        try:
            response = requests.post(url, timeout=60, **kwargs)
            break
        except requests.RequestException as e:
            log(f"Telegram try {attempt} of {TELEGRAM_TRIES} failed: {type(e).__name__}")
            time.sleep(1)
    else:
        raise TelegramError("Could not reach Telegram. Check your internet and try again.")
    try:
        answer = response.json()
    except ValueError:
        answer = {}
    if answer.get("ok"):
        return answer["result"]
    code, description = response.status_code, str(answer.get("description", ""))
    log(f"Telegram error {code}: {description}")
    if code in (401, 404):
        raise TelegramError("Telegram did not accept the bot token. Please check it.", settings_problem=True)
    if code == 403 or "chat" in description.lower():
        raise TelegramError("Telegram could not use this chat. Check it, and that the bot is a member.", settings_problem=True)
    raise TelegramError(f"Telegram returned error {code}. Please try again later.")


def find_telegram_chat(settings):
    """Return the latest chat that wrote to the bot."""
    for update in reversed(telegram_request(settings, "getUpdates")):
        message = update.get("message") or update.get("channel_post") or update.get("my_chat_member")
        if message:
            return message["chat"]["id"]
    raise TelegramError("Send any message to your bot in Telegram, then press the Telegram button again.")


def send_to_telegram(settings, audio_path, caption):
    """Send the audio file with a short caption."""
    if not settings["chat"]:
        settings["chat"] = find_telegram_chat(settings)
        save_telegram_settings(settings)
    data = {"chat_id": settings["chat"], "caption": caption}
    files = {"audio": (audio_path.name, audio_path.read_bytes(), "audio/mpeg")}
    telegram_request(settings, "sendAudio", data=data, files=files)


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
    last_text = ""
    playing = False
    current_status = ("", MUTED)

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
    field_title(settings, "Output text name").grid(row=0, column=2, sticky="w", padx=6, pady=(8, 0))
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
    text_name_box = name_field(2, DEFAULT_TEXT_NAME, 6)
    folder_image = ctk.CTkImage(
        Image.open(ASSETS_DIR / "folder_light.png"), Image.open(ASSETS_DIR / "folder_dark.png"), size=(20, 20)
    )
    folder_button = ctk.CTkButton(
        settings, text="", image=folder_image, width=36, height=36, corner_radius=10, fg_color=FIELD,
        hover_color=BORDER, border_width=2, border_color=BORDER,
    )
    folder_button.grid(row=1, column=3, padx=(6, 14), pady=(0, 14))

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
    telegram_image = ctk.CTkImage(Image.open(ASSETS_DIR / "telegram.png"), size=(28, 28))
    telegram_button = ctk.CTkButton(
        actions, text="", image=telegram_image, width=46, height=46, corner_radius=12, fg_color="transparent",
        hover_color=BORDER, border_width=1, border_color=BORDER,
    )
    telegram_button.grid(row=0, column=2, padx=(10, 0))
    # yandex_button = ctk.CTkButton(actions, text="Add Yandex API", font=font(14), height=46, corner_radius=12)
    # yandex_button.grid(row=0, column=3, padx=(10, 0))

    progress = ctk.CTkProgressBar(root, mode="indeterminate", height=4, progress_color=ACCENT, fg_color=BORDER)
    progress.grid(row=5, column=0, sticky="ew", padx=20, pady=(10, 0))
    progress.grid_remove()
    status_label = ctk.CTkLabel(root, font=font(13), anchor="w", justify="left", wraplength=610, height=22)
    status_label.grid(row=6, column=0, sticky="ew", padx=22, pady=(8, 14))

    def status(text, color=MUTED):
        nonlocal current_status
        current_status = (text, color)
        status_label.configure(text=text, text_color=color)

    def busy(active):
        run_button.configure(state="disabled" if active else "normal", text="Creating audio..." if active else "Run")
        play_button.configure(state="normal" if last_file and not active else "disabled")
        telegram_button.configure(state="disabled" if active else "normal")
        if active:
            progress.grid()
            progress.start()
        else:
            progress.stop()
            progress.grid_remove()

    show_tips(voice_box.get())
    status("Enter German text and press Run.")

    def ask_telegram_settings(old):
        """Show a small window for the bot token and chat. Return the saved settings or None."""
        dialog = ctk.CTkToplevel(root, fg_color=BACKGROUND)
        dialog.title("Telegram settings")
        dialog.geometry("480x330")
        dialog.resizable(False, False)
        dialog.transient(root)
        dialog.grid_columnconfigure(0, weight=1)
        saved = []

        def entry_row(row, title, hint, value, **options):
            field_title(dialog, title).grid(row=row, column=0, columnspan=2, sticky="w", padx=20, pady=(14, 0))
            box = ctk.CTkEntry(dialog, font=font(14), height=36, corner_radius=10, fg_color=FIELD, text_color=TEXT, border_color=BORDER, **options)
            box.insert(0, value)
            box.grid(row=row + 1, column=0, columnspan=2, sticky="ew", padx=20)
            ctk.CTkLabel(dialog, text=hint, font=font(12), text_color=MUTED, anchor="w", justify="left", wraplength=440).grid(
                row=row + 2, column=0, columnspan=2, sticky="w", padx=20, pady=(2, 0)
            )
            return box

        old = old or {"token": "", "chat": ""}
        token_box = entry_row(0, "Bot token", "Create a bot with @BotFather in Telegram and paste its token here.", old["token"], show="*")
        chat_box = entry_row(
            3, "Channel or chat", "Channel: add the bot as an admin and enter @channelname.\n"
            "Your own chat: leave this empty and send your bot any message first.", str(old["chat"]),
        )

        def save():
            token = token_box.get().strip()
            if token:
                saved.append({"token": token, "chat": telegram_chat(chat_box.get())})
                dialog.destroy()

        ctk.CTkButton(
            dialog, text="Cancel", font=font(14), height=38, corner_radius=10, fg_color="transparent", hover_color=BORDER,
            border_width=1, border_color=BORDER, text_color=TEXT, command=dialog.destroy,
        ).grid(row=6, column=0, sticky="e", padx=(20, 10), pady=(16, 16))
        ctk.CTkButton(
            dialog, text="Save", font=font(14, "bold"), height=38, corner_radius=10, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="white", command=save,
        ).grid(row=6, column=1, sticky="e", padx=(0, 20), pady=(16, 16))

        def focus_dialog():
            if dialog.winfo_exists():
                dialog.lift()
                dialog.focus_force()
                token_box.focus()
                dialog.grab_set()

        dialog.after(150, focus_dialog)
        root.wait_window(dialog)
        if not saved:
            return None
        save_telegram_settings(saved[0])
        log("Telegram settings saved")
        return saved[0]

    def telegram_done(audio_path, error):
        run_button.configure(state="normal")
        telegram_button.configure(state="normal")
        if not error:
            status(f"Sent {audio_path.name} to Telegram.", SUCCESS)
            return
        status(str(error), ERROR)
        if error.settings_problem and ask_telegram_settings(load_telegram_settings()):
            status("Telegram settings saved. Press the Telegram button again.")

    def telegram_work(settings, audio_path, caption):
        try:
            send_to_telegram(settings, audio_path, caption)
            log(f"Sent {audio_path.name} to Telegram")
            error = None
        except TelegramError as e:
            error = e
        except Exception as e:
            log(f"Telegram failed: {type(e).__name__}")
            error = TelegramError("Could not send the audio to Telegram.")
        root.after(0, telegram_done, audio_path, error)

    def show_telegram_hint(_):
        # Closing a window can also trigger this, so check that the mouse is really on the button
        under_mouse = root.winfo_containing(*root.winfo_pointerxy())
        if telegram_button.cget("state") == "normal" and str(under_mouse).startswith(str(telegram_button)):
            status_label.configure(text=TELEGRAM_HINT, text_color=MUTED)

    def hide_telegram_hint(_):
        text, color = current_status
        status_label.configure(text=text, text_color=color)

    def change_telegram_settings(_):
        if telegram_button.cget("state") == "normal":
            telegram_button.configure(state="disabled")
            saved = ask_telegram_settings(load_telegram_settings())
            telegram_button.configure(state="normal")
            if saved:
                status("Telegram settings saved.", SUCCESS)

    def telegram_click():
        if not last_file or not last_file.exists():
            status("Press Run first to create the audio.", ERROR)
            return
        settings = load_telegram_settings() or ask_telegram_settings(None)
        if not settings:
            status("Nothing was sent.")
            return
        run_button.configure(state="disabled")
        telegram_button.configure(state="disabled")
        status("Sending to Telegram...")
        args = (settings, last_file, telegram_caption(last_text))
        threading.Thread(target=telegram_work, args=args, daemon=True).start()

    def open_output_folder():
        try:
            OUTPUT_DIR.mkdir(exist_ok=True)
            os.startfile(OUTPUT_DIR)
        except OSError as e:
            log(f"Could not open the output folder: {e}")
            status("Could not open the output folder.", ERROR)

    def stop_audio():
        nonlocal playing
        if playing:
            playing = False
            play_button.configure(text="Play")
            mci("close voice")  # this also frees the file, so it can be overwritten

    def check_audio():
        """Switch the button back to Play when the audio reaches its end."""
        if playing:
            if mci("status voice mode") == "stopped":
                stop_audio()
            else:
                root.after(200, check_audio)

    def toggle_audio():
        nonlocal playing
        if playing:
            stop_audio()
            return
        try:
            mci(f'open "{last_file}" type mpegvideo alias voice')
            mci("play voice")
        except OSError as e:
            log(f"Play failed: {e}")
            status("Could not play the audio file.", ERROR)
            try:
                mci("close voice")
            except OSError:
                pass  # the file was never opened
            return
        playing = True
        play_button.configure(text="Stop")
        check_audio()

    def finish(result, text_path, error):
        nonlocal last_file, last_text
        busy(False)
        if error:
            message = "Could not create audio. Check your internet and try again."
            if isinstance(error, PermissionError):
                message = "Could not overwrite the file. Close it in your player and try again."
            # message = str(error) if isinstance(error, YandexError) else message
            status(message, ERROR)
            return
        last_file, service = result
        last_text = text_path.read_text(encoding="utf-8")
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
        stop_audio()
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
    play_button.configure(command=toggle_audio)
    folder_button.configure(command=open_output_folder)
    telegram_button.configure(command=telegram_click)
    telegram_button.bind("<Button-3>", change_telegram_settings)
    telegram_button.bind("<Enter>", show_telegram_hint)
    telegram_button.bind("<Leave>", hide_telegram_hint)
    root.mainloop()


if __name__ == "__main__":
    main()
