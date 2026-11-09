import time
import os
import subprocess
import sys
from mutagen import File

CLEAR_COMMAND = "cls" if os.name == "nt" else "clear"

def clear_console():
    """Clears the console screen."""
    subprocess.run([CLEAR_COMMAND], shell=True)

def check_if_file_is_valid(file_path: str) -> bool:
    """Checks if the given file is an audio file and has lyrics in it.

    Args:
        file_path (str): absolute path to the audio file

    Returns:
        bool: True if file is valid for playing and showing lyrics, else False
    """
    if not os.path.isfile(file_path):
        print(f"Error: The file '{file_path}' does not exist.")
        return False
    if not file_path.endswith(('.mp3', '.wav', '.flac')):
        print(f"Error: The file '{file_path}' is not a supported audio format.")
        return False

    # check if the file has lyrics, for simplicity, let's assume we have a function that checks for lyrics
    if not has_lyrics(file_path):
        print(f"Error: The file '{file_path}' does not contain lyrics.")
        return False

    return True

def has_lyrics(file_path: str) -> bool:
    """Return True if matching LRC lyrics or non-empty embedded lyrics exist."""
    lrc_path = os.path.splitext(file_path)[0] + ".lrc"
    if os.path.isfile(lrc_path):
        return True

    try:
        audio = File(file_path)
    except (ImportError, OSError, ValueError):
        return False

    if audio is None or not audio.tags:
        return False

    for key, value in audio.tags.items():
        tag_name = str(key).casefold()
        if "lyric" not in tag_name and not tag_name.startswith(("uslt", "sylt")):
            continue

        text = getattr(value, "text", value)
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        if isinstance(text, str) and text.strip():
            return True
        if isinstance(text, (list, tuple)):
            for item in text:
                item_text = getattr(item, "text", item)
                if isinstance(item_text, bytes):
                    item_text = item_text.decode("utf-8", errors="ignore")
                if isinstance(item_text, str) and item_text.strip():
                    return True

    return False

def choose_song() -> str | None:
    """
    Allows the user to select a directory and choose an audio file.
    Supports arrow-key navigation when running in an interactive terminal.

    Returns:
        str | None: Absolute path to the selected audio file, or None.
    """
    import os
    import sys
    from pathlib import Path

    AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac"}

    def get_audio_files(folder: Path) -> list[Path] | None:
        """Returns audio files or None if the directory is inaccessible."""
        try:
            return sorted(
                (file for file in folder.iterdir()
                    if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS),
                key=lambda file: file.name.casefold()
            )
        except (OSError, ValueError):
            return None

    def select_with_arrows(files: list[Path]) -> int | None:
        """
        Returns the selected index.
        Returns None if arrow navigation is unavailable.
        Returns -1 if the user cancels.
        """
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return None
        if os.name != "nt" and os.environ.get("TERM", "").lower() == "dumb":
            return None

        def draw_menu(selected: int) -> None:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write("Available songs (↑/↓, Enter to select, Esc to cancel):\n\n")
            for idx, file in enumerate(files):
                marker = ">" if idx == selected else " "
                sys.stdout.write(f"{marker} {idx + 1}. {file.name}\n")
            sys.stdout.flush()

        if os.name == "nt":
            try:
                import msvcrt

                def read_key() -> str:
                    key = msvcrt.getwch()
                    if key in ("\x00", "\xe0"):
                        return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
                    if key in ("\r", "\n"):
                        return "enter"
                    if key in ("\x1b", "\x03"):
                        return "cancel"
                    return ""

                selected = 0
                while True:
                    draw_menu(selected)
                    key = read_key()
                    if key == "up":
                        selected = (selected - 1) % len(files)
                    elif key == "down":
                        selected = (selected + 1) % len(files)
                    elif key == "enter":
                        print()
                        return selected
                    elif key == "cancel":
                        print()
                        return -1

            except (ImportError, OSError, ValueError):
                return None
        else:
            try:
                import select
                import termios
                import tty

                fd = sys.stdin.fileno()
                original_terminal = termios.tcgetattr(fd)

                def read_key() -> str:
                    first = os.read(fd, 1)
                    if not first:
                        return "cancel"
                    if first == b"\x1b":
                        ready, _, _ = select.select([fd], [], [], 0.08)
                        if not ready:
                            return "cancel"
                        second = os.read(fd, 1)
                        if second in (b"[", b"O"):
                            ready, _, _ = select.select([fd], [], [], 0.08)
                            if ready:
                                third = os.read(fd, 1)
                                return {b"A": "up", b"B": "down"}.get(third, "")
                        return "cancel"
                    if first in (b"\r", b"\n"):
                        return "enter"
                    if first in (b"\x03", b"\x04"):
                        return "cancel"
                    return ""

                try:
                    tty.setraw(fd)
                    selected = 0
                    while True:
                        draw_menu(selected)
                        key = read_key()
                        if key == "up":
                            selected = (selected - 1) % len(files)
                        elif key == "down":
                            selected = (selected + 1) % len(files)
                        elif key == "enter":
                            print()
                            return selected
                        elif key == "cancel":
                            print()
                            return -1
                finally:
                    try:
                        termios.tcsetattr(fd, termios.TCSADRAIN, original_terminal)
                    except OSError:
                        pass

            except (ImportError, OSError, ValueError):
                return None

    # Select directory before searching.
    try:
        directory_input = input(
            "Enter the directory containing your songs [songs]: "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return None

    directory = Path(directory_input).expanduser() if directory_input else Path("songs")
    audio_files = get_audio_files(directory)

    if audio_files is None:
        print(f"Error: '{directory}' is not an accessible directory.")
        return None
    if not audio_files:
        print(f"No audio files found in '{directory}'.")
        return None

    # Try interactive arrow-key selection.
    selected_index = select_with_arrows(audio_files)

    if selected_index == -1:
        return None
    if selected_index is not None:
        return str(audio_files[selected_index].resolve())

    # Numeric selection fallback.
    print("\nAvailable songs:")
    for idx, file in enumerate(audio_files, start=1):
        print(f"{idx}. {file.name}")

    print("\nSelect a song by its number:")
    while True:
        try:
            choice = input("Enter the number of the song you want to play: ").strip()
            selected_index = int(choice) - 1
        except ValueError:
            print("Invalid choice. Please try again.")
            continue
        except (EOFError, KeyboardInterrupt):
            return None

        if 0 <= selected_index < len(audio_files):
            return str(audio_files[selected_index].resolve())
        print("Invalid choice. Please try again.")

def extract_lyrics_from_file(file_path: str, debug: bool = False) -> str | None:
    """Extracts lyrics from the given audio file.

    Args:
        file_path (str): absolute path to the audio file
        debug (bool): Whether to print debug information

        
    Returns:
        str | None: The extracted lyrics or None if extraction fails.
    """
    if not check_if_file_is_valid(file_path):
        return None

    lrc_path = os.path.splitext(file_path)[0] + ".lrc"
    if os.path.isfile(lrc_path):
        try:
            with open(lrc_path, "r", encoding="utf-8") as lrc_file:
                return lrc_file.read()
        except (OSError, UnicodeDecodeError):
            print(f"Error reading lyrics file: {lrc_path}")
    else:
        try:
            audio = File(file_path)
            if audio is None or not audio.tags:
                return None
            else:
                for key, value in audio.tags.items():
                    if debug:
                        print(f"Checking tag: {key}, value: {value}, type: {type(value)}")
                    tag_name = str(key).casefold()
                    if "lyric" not in tag_name and not tag_name.startswith(("uslt", "sylt")):
                        continue

                    text = getattr(value, "text", value)
                    if isinstance(text, bytes):
                        text = text.decode("utf-8", errors="ignore")
                        if debug:
                            print(f"Decoded lyrics from bytes: {text}")
                    if isinstance(text, str) and text.strip():
                        if debug:
                            print(f"Extracted lyrics: {text.strip()}")
                        return text.strip()
                    if isinstance(text, (list, tuple)):
                        for item in text:
                            if debug:
                                print(f"Checking item in lyrics list: {item}, of type {type(item)}")
                            item_text = getattr(item, "text", item)
                            if debug:
                                print(f"Item text: {item_text}, of type {type(item_text)}")
                            if isinstance(item_text, bytes):
                                item_text = item_text.decode("utf-8", errors="ignore")
                                if debug:
                                    print(f"Decoded item text from bytes: {item_text}")
                            if isinstance(item_text, str) and item_text.strip():
                                if debug:
                                    print(f"Extracted lyrics from list: {item_text.strip()}")
                                return item_text.strip()
        except (ImportError, OSError, ValueError):
            print(f"Error extracting lyrics from audio file: {file_path}")
    
    return None

class Verse:
    def __init__(self, text: str):
        self.text = text
        self.time = None  # Placeholder for time, can be set later if needed
        if self.text.startswith("["):
            self.time = self.text[1:9]
            self.text = self.text[10:]  # Remove the time and brackets from the text

    def __str__(self):
        return f"{self.time} -> {self.text}" if self.time else self.text

    def __repr__(self):
        return f"Verse(time={self.time}, text={self.text})"

class Lyrics:
    def __init__(self, lyrics: str | list[Verse]):
        if isinstance(lyrics, str):
            self.verses = [Verse(line) for line in lyrics.splitlines() if line.strip()]
        else:
            self.verses = lyrics

class Color:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"

class Lyric():
    def __init__(self, text: str, char_pause: float, phrase_pause: float, new_line: bool = True, color: str = ""):
        self.text = text
        self.char_pause = char_pause
        self.phrase_pause = phrase_pause
        self.new_line = new_line
        self.color = color

class SongLyric():
    def __init__(self, lyrics: list[Lyric]):
        self.lyrics = lyrics

    def play(self):
        clear_console()
        for lyric in self.lyrics:
            if lyric.color:
                print(lyric.color, end="", flush=True)
                
            for char in lyric.text:
                print(char, flush=True, end="")
                time.sleep(lyric.char_pause)
                
            if lyric.color:
                print(Color.RESET, end="", flush=True)
                
            time.sleep(lyric.phrase_pause)
            if lyric.new_line:
                print()

def main():
    song_path = choose_song()
    if song_path is None:
        print("No song selected. Exiting.")
        return

    if not check_if_file_is_valid(song_path):
        print("Selected file is not valid for playing. Exiting.")
        return

    # Here you would implement the logic to play the audio file and display lyrics.
    # For now, we will just print the selected song path.
    print(f"Selected song: {song_path}")

    # print the lyrics of the selected song for debugging purposes
    lyrics = extract_lyrics_from_file(song_path)
    if lyrics:
        print("Extracted Lyrics:")
        print(lyrics)
        print("Creating object Lyrics from the extracted lyrics...")
        lyrics_object = Lyrics(lyrics)
        print("Created Lyrics object:")
        for verse in lyrics_object.verses:
            print(verse)
    else:
        print("Failed to extract lyrics.")

if __name__ == "__main__":
    clear_console()
    main()