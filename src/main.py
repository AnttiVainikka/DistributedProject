import sys

from main_gui import Application

def main():
    local = False
    if len(sys.argv) > 1 and sys.argv[1] == 'l':
        local = True

    songs = ["src/songs/[Copyright Free Romantic Music] - .mpga","src/songs/Orchestral Trailer Piano Music (No Copyright) .mpga"]
    app = Application(songs, local)
    app.start()

if __name__ == "__main__":
    main()
