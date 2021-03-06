"""
Used by Worker to spawn a new process.
"""

__author__ = "Olivier Derpierre"
__copyright__ = "Copyright 2009, Mikros Image"

import logging
import os
import sys
import subprocess
import resource
from octopus.worker import settings

LOGGER = logging.getLogger("main.process")
CLOSE_FDS = (os.name != 'nt')


def setlimits():
    # the use of os.setsid is necessary to create a processgroup properly for the commandwatcher
    # it creates a new session in which the cmdwatcher is the leader of the new process group
    os.setsid()

    # set the limit of open files for ddd
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    try:
        if settings.LIMIT_OPEN_FILES < hard:
            resource.setrlimit(resource.RLIMIT_NOFILE, (settings.LIMIT_OPEN_FILES, hard))
    except Exception, e:
        LOGGER.error("Setting ressource limit failed: RLIMT_NOFILE [%r,%r] --> [%r,%r]" % (soft, hard, settings.LIMIT_OPEN_FILES, hard))
        raise e


def spawnRezManagedCommandWatcher(pidfile, logfile, args, watcherPackages, env):
    """
    | Uses rez module to start a process with a proper rez env.

    :param pidfile: full path to the comand pid file (usally /var/run/puli/cw<command_id>.pid)
    :param logfile: file object to store process log content
    :param args: arguments passed to the CommandWatcher script
    :param watcherPackages: A list of packages that will be resolved when creating Rez context
    :param env: a dict holding key/value pairs that will be merged into the current env and used in subprocess

    :return: a CommandWatcherProcess object holding command watcher process handle
    """
    try:
        from rez.resources import clear_caches
        from rez.resolved_context import ResolvedContext
        from rez.resolver import ResolverStatus
    except ImportError as e:
        LOGGER.error("Unable to load rez package in a rez managed environment.")
        raise e

    try:
        if watcherPackages is None:
            LOGGER.warning("No package specified for this command, it might not find the runner for this command.")
            watcherPackagesList = []
        elif type(watcherPackages) in [str, unicode]:
            watcherPackagesList = watcherPackages.split()
        else:
            watcherPackagesList = watcherPackages

        clear_caches()
        context = ResolvedContext(watcherPackagesList)
        success = (context.status == ResolverStatus.solved)
        if not success:
            context.print_info(buf=sys.stderr)
            raise

        # normalize environment
        envN = os.environ.copy()
        for key in env:
            envN[str(key)] = str(env[key])

        proc = context.execute_shell(
            command=args,
            shell='bash',
            stdin=False,
            stdout=logfile,
            stderr=subprocess.STDOUT,
            block=False,
            parent_environ=envN
        )

        LOGGER.info("Starting subprocess, log: %r, args: %r" % (logfile.name, args))
    except Exception as e:
        LOGGER.error("Impossible to start process: %s" % e)
        raise e

    file(pidfile, "w").write(str(proc.pid))
    return CommandWatcherProcess(proc, pidfile, proc.pid)


def spawnCommandWatcher(pidfile, logfile, args, env):
    """
    | Create a subprocess with "CommandWatcher" script. It will receive the commands arguments and everything
    | needed to execute the command process (logfile, runner name...)
    | The subprocess received the current environment merged with given env dict.

    :param pidfile: full path to the comand pid file (usally /var/run/puli/cw<command_id>.pid)
    :param logfile: a file handler to wich log will be redirected
    :param args: arguments passed to the CommandWatcher script
    :param env: a dict holding key/value pairs that will be merged into the current env and used in subprocess

    :return: A CommandWatcherProcess class holding relevants infos of the new process
    """
    devnull = file(os.devnull, "r")

    # normalize environment
    envN = os.environ.copy()
    for key in env:
        envN[str(key)] = str(env[key])


    LOGGER.info("Starting subprocess, log: %r, args: %r" % (logfile.name, args))
    try:
        # pid = subprocess.Popen(args, bufsize=-1, stdin=devnull, stdout=logfile,
        #                    stderr=subprocess.STDOUT, close_fds=CLOSE_FDS,
        #                    preexec_fn=setlimits, env=envN).pid
        process = subprocess.Popen(
            args, bufsize=-1, stdin=devnull, stdout=logfile,
            stderr=logfile, close_fds=CLOSE_FDS,
            preexec_fn=setlimits, env=envN)

    except Exception, e:
        LOGGER.error("Impossible to start subprocess: %r" % e)
        raise e

    file(pidfile, "w").write(str(process.pid))
    return CommandWatcherProcess(process, pidfile, process.pid)


class CommandWatcherProcess(object):
    def __init__(self, process, pidfile, pid):
        self.process = process
        self.pidfile = pidfile
        self.pid = pid

    def kill(self):
        """Kill the process."""
        if os.name != 'nt':

            # WARNING: SEVERAL PROBLEMS HERE
            # the kill is not properly done, SIGTERM might not be sufficient, killpg is done on pid instead of pgid
            # this code never works ! It gives the impression to work because there is "ensureNoMoreRender" in worker

            # try:
            #     LOGGER.warning("Killing process %s (pid=%s)" % (self.process, self.pid))
            #     self.process.kill()
            # except Exception as err:
            #     LOGGER.warning("Error when killing process" % err)
            #
            # import time
            # time.sleep(2.0)
            # LOGGER.warning("After kill...")
            # return

            from signal import SIGTERM
            from signal import SIGKILL
            from errno import ESRCH

            # PHASE 1 ===> THIS IS STUPID: kills the whole group including the worker !
            # try:
            #     # do not kill the process, kill the whole process group!
            #     LOGGER.info("Phase 1: Trying to kill process group %s" % str(self.pid))
            #     os.killpg(os.getpgid(self.pid), SIGTERM)
            #     return
            # except OSError, e:
            #     LOGGER.warning("A problem occured: %s" % e)
            #     # If the process is dead already, let it rest in peace.
            #     # Else, we have a problem, so reraise.
            #     if e.args[0] != ESRCH:
            #         LOGGER.error("Phase 1: process error (%s)" % e)
            #         raise

            # PHASE 2
            try:
                # the commandwatcher did not have time to setpgid yet, let's just kill the process
                # FIXME there still is room for a race condition there
                LOGGER.info("Try to nicely terminate the process %s" % str(self.pid))
                os.kill(self.pid, SIGTERM)
            except OSError, e:
                # If the process is dead already, let it rest in peace.
                # Else, we have a problem, so reraise.
                if e.args[0] != ESRCH:
                    LOGGER.error("Phase 2: process error (%s)" % e)
                    raise

            # PHASE 3 ==> SAME AS PHASE 1
            # try:
            #     # attempt to fix a race condition:
            #     # if we kill the watcher but the watcher had the time to
            #     # create processgroup and start another process in between
            #     # phases 1 and 2, then attempt to kill the processgroup.
            #     LOGGER.info("Phase 3: Try to fix race condition by killing the process group again %s" % str(self.pid))
            #     os.killpg(self.pid, SIGTERM)
            # except OSError, e:
            #     # If the process is dead already, let it rest in peace.
            #     # Else, we have a problem, so reraise.
            #     if e.args[0] != ESRCH:
            #         LOGGER.error("Phase 3: process error (%s)" % e)
            #         raise
        else:
            os.popen("taskkill /PID  %d" % self.pid)
