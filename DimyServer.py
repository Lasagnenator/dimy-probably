import argparse
import threading
import backend
import log

def main(port):
    b = backend.Backend(port)
    t = threading.Thread(target=b.start, daemon=True)
    t.start()
    try:
        t.join()
    except KeyboardInterrupt:
        log.log("Stopping")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int, help="Server port to use")
    args = parser.parse_args()
    main(args.port)

"""
Server uses a second thread to allow for easy program quits.
"""
