# German Text to Speech

A small Windows app that turns German text into a voice message. Type your text, choose a voice, press **Run**, and it saves an mp3 file and a text file.

## Use

1. Double-click `German Text to Speech.exe`. It needs an internet connection, but no Python.
2. Type or paste your German text.
3. Choose a voice: Katja, Amala, Conrad or Killian.
4. Enter the output names. The defaults are `audio` and `text`.
5. Press **Run**, then **Play** to listen.

The app follows the light or dark mode of Windows.

Files are saved in the `output` folder next to the app, as `audio.mp3` and `text.txt`. If an output file already exists, the app asks before overwriting it. If a run fails, the old audio file is kept.

## Voices

The app uses free Microsoft voices through [edge-tts](https://github.com/rany2/edge-tts). It tries the Microsoft server up to 10 times. If that fails, it uses the Google voice through [gTTS](https://github.com/pndurette/gTTS), and the status line shows which service was used.

## Yandex voice (switched off)

The Yandex code is commented out in `text_to_audio.py` for now, so the **Add Yandex API** button and the voice **Lea** are not shown. The notes below apply when it is switched on again.

The voice **Lea** uses [Yandex SpeechKit](https://aistudio.yandex.ru/docs/en/speechkit/tts/voices), a paid service, and needs your own API key.

1. Press **Add Yandex API** and paste your key.
2. Choose **Lea (female, Yandex)** and press **Run**.

The key is saved in `yandex_api_key.txt`, one folder above this project, so it is not in git. If that folder is inside OneDrive, OneDrive also copies the file to the cloud. It is stored as plain text, so don't share that file. The app sends the key only to Yandex.

Yandex allows up to 5000 characters per message. If Yandex fails, the app shows an error and does not switch to another voice.

## Pauses and stress

These tips were measured with the Microsoft voices.

| You type | Effect |
|---|---|
| `,` `;` `:` `...` or space + hyphen (` - `) | Short pause, about 0.2 seconds |
| `.` `!` `?` or a new line | Long pause, about 0.9 seconds |
| `"word"` | Light stress |
| `word!` | Stronger stress, followed by a long pause |

- The long dash `–` makes a short pause for Katja and Conrad, but no pause for Amala and Killian.
- Avoid `*word*` and `_word_`. CAPITALS have almost no effect.
- Stress on a single letter or syllable is not supported.

## Text length

No official limit is documented. Long text is split automatically: into parts of 4096 bytes for Microsoft and 100 characters for Google. Very long texts may fail more often, because each part needs its own connection.

## Logs

The app writes one log file per day to the `Log` folder, for example `2026-11-05.log`. Files older than 30 days are deleted when the app starts. Logs contain voices, file names, text lengths and errors, but never your text or API key. The `Log` folder is not added to git.

## Development

Needs Python 3.12 with tkinter (included in the standard Windows installer). Create the virtual environment once:

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python -m pip install -r requirements-dev.txt
```

- Run from source: double-click `start.bat`.
- Build the app: double-click `build.bat`. It creates `German Text to Speech.exe` in this folder. The `.exe` is not added to git.
- Change the icon: edit `assets/make_icon.py` and run it, then build again.

## License

[MIT](LICENSE)
