import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import sys
from os.path import dirname, abspath, join
sys.path.append(dirname(abspath(__file__)))

from .io.write import writeFiles

iodirname = "out"

class ioFolderHandler(FileSystemEventHandler):
    def on_modified(self, event):
        idir = join(dirname(abspath(__file__)), iodirname)
        if event.src_path == idir:
            print("Change at " + time.strftime("%Y-%m-%d %H:%M:%S"))
            writeFiles("in.txt", "out.txt", iodirname)

if __name__ == "__main__":
    event_handler = ioFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, path=join('.', iodirname), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()