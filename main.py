import time
import subprocess

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
        subprocess.run("clear")
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