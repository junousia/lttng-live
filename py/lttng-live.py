import threading
import logging
import subprocess
from time import sleep

OPEN_SESSIONS = {}
class StoppableThread(threading.Thread):
    """ Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, name):
        super(StoppableThread, self).__init__(name=name)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


def parse_sessions(input):
    ''' Return the session name from babeltrace output
    >>> parse_sessions(['net://localhost/host/myhostname/mysessionname (timer = 1000000, 5 stream(s), 0 client(s) connected)'])
    ['net://localhost/host/myhostname/mysessionname']
    >>> parse_sessions([ \
            'net://localhost/host/myhostname/mysessionname1 (timer = 1000000, 5 stream(s), 0 client(s) connected)', \
            'net://localhost/host/myhostname/mysessionname2 (timer = 1000000, 5 stream(s), 0 client(s) connected)' \
            ])
    ['net://localhost/host/myhostname/mysessionname1', 'net://localhost/host/myhostname/mysessionname2']
    '''
    sessions = []
    for line in input:
        sessions.append(line.split(' ', 1)[0])
    return sessions


class TraceWorker(StoppableThread):
    ''' Worker thread for processing traces from the pipe '''
    def run(self):
        t = threading.currentThread()
        session = OPEN_SESSIONS[t.name]
        trace_count = 0

        logging.debug("Worker started")

        while not self.stopped() and not session['process'].poll():
            if session['process'].stdout.readline():
                trace_count += 1;
            else:
                break
        logging.debug("Worker stopped, received: %d traces", trace_count)


class SessionPoller(StoppableThread):
    def run(self):
        logging.debug("Session polling starting")

        while not self.stopped():
            cmd = subprocess.Popen(['babeltrace', '-i', 'lttng-live', 'net://localhost'],
                               stdout=subprocess.PIPE)
            if cmd.wait():
                exit(cmd.returncode)

            parsed_sessions = parse_sessions(cmd.stdout)

            gen = (s for s in parsed_sessions if s not in OPEN_SESSIONS)

            for session in gen:
                logging.debug("New session: %s" % session)
                OPEN_SESSIONS[session] = {
                    'process' : subprocess.Popen(['babeltrace', '-i', 'lttng-live', session], stdout=subprocess.PIPE),
                    'thread' : TraceWorker(name=session)
                }
                OPEN_SESSIONS[session]['thread'].start()

            sleep(1.0)


def main():
    relayd = subprocess.Popen(["lttng-relayd"])
    try:
        d = SessionPoller(name="Session Poller")
        d.start()
        d.join()
    except:
        logging.debug("interrupt")
        d.stop()
        for key, s in OPEN_SESSIONS.iteritems():
            logging.debug("Stopping session %s" % key)
            s['thread'].stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(threadName)-10s] [%(levelname)s] %(message)s')
    main()
