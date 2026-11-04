"""German text-to-speech with a small window. Needs internet and: pip install edge-tts gTTS"""
import asyncio
import os
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import edge_tts
from gtts import gTTS

OUTPUT_DIR = Path(__file__).parent / "output"
DEFAULT_AUDIO_NAME = "audio"
DEFAULT_TEXT_NAME = "text"
MICROSOFT_TRIES = 10  # the Microsoft server often drops connections, so keep trying
VOICES = {
    "Katja (female)": "de-DE-KatjaNeural",
    "Amala (female)": "de-DE-AmalaNeural",
    "Conrad (male)": "de-DE-ConradNeural",
    "Killian (male)": "de-DE-KillianNeural",
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
FIRST_TEXT = """Diese Herbstferien waren sehr schön.
In der ersten Woche habe ich mit meiner Familie Berlin besucht. Wir haben eine Berlin-Discount-Karte gekauft, also haben wir fast alles gemacht: Wir sind mit dem Touristikbus gefahren, haben viele Museen besucht, sind mit dem Schiff gefahren und haben den berühmten Fernsehturm am Alexanderplatz besucht und mehr. Diese Reise war wirklich toll!
In der zweiten Woche waren wir zu Hause, weil mein Mann arbeiten musste. Und am letzten Wochenende haben wir den Zoo in Osnabrück besucht."""


def voice_tips(voice):
    """Return the tips text for a voice name from the dropdown."""
    short, long, dash = VOICE_PAUSES[voice]
    return TIPS.format(voice=voice, short=short, long=long, dash="short pause" if dash else "no pause")


def make_audio(text, voice, path):
    """Create an mp3 file. Return its path and the service that made it."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    for _ in range(MICROSOFT_TRIES):
        try:
            asyncio.run(edge_tts.Communicate(text, voice).save(str(path)))
            return path, "Microsoft"
        except Exception:
            time.sleep(1)
    try:
        gTTS(text, lang="de").save(str(path))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path, "Google"


def main():
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
    voice_box = ttk.Combobox(controls, values=list(VOICES), state="readonly", width=16)
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
            status.config(text="Could not create audio. Check your internet and try again.")
            return
        last_file, service = result
        play_button.config(state="normal")
        status.config(text=f"Saved: {last_file.name} and {text_path.name} in the output folder ({service} voice)")

    def work(text, voice, audio_path, text_path):
        try:
            result, error = make_audio(text, voice, audio_path), None
            text_path.write_text(text, encoding="utf-8")
        except Exception as e:
            result, error = None, e
        root.after(0, finish, result, text_path, error)

    def output_path(name_box, suffix):
        """Return a new file path from a name field, or None if the name can't be used."""
        name = name_box.get().strip().removesuffix(suffix)
        if not name or any(c in name for c in r'\/:*?"<>|'):
            status.config(text=r'Please enter a file name without \ / : * ? " < > |')
            return None
        path = OUTPUT_DIR / f"{name}{suffix}"
        if path.exists():
            status.config(text=f"{path.name} already exists. Please enter another file name.")
            return None
        return path

    def create():
        text = text_box.get("1.0", "end").strip()
        if not text:
            status.config(text="Please enter some text first.")
            return
        audio_path = output_path(audio_name_box, ".mp3")
        text_path = audio_path and output_path(text_name_box, ".txt")
        if not text_path:
            return
        run_button.config(state="disabled")
        status.config(text="Creating audio...")
        args = (text, VOICES[voice_box.get()], audio_path, text_path)
        threading.Thread(target=work, args=args, daemon=True).start()

    run_button.config(command=create)
    play_button.config(command=lambda: os.startfile(last_file))
    root.mainloop()


if __name__ == "__main__":
    main()
