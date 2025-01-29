"""Provide simple one-show commands to set/get DS9 data.

Error messages will include color (red) unless

 - the NO_COLOR environment variable is set, following
   https://no-color.org/

 - the output is not a TTY (e.g. it is being piped to a file)

"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import sys

from ds9samp import add_color, ds9samp, list_ds9, VERSION


def parse(desc):
    """Common parser"""

    usage = "%(prog)s [options] command"
    parser = ArgumentParser(usage=usage, description=desc,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("command")
    parser.add_argument("-n", "--name", type=str,
                        dest="client",
                        help="Name of DS9 client in the SAMP hub")
    parser.add_argument("-t", "--timeout", type=int,
                        dest="timeout", default=10,
                        help="Timeout in seconds (integer, use 0 to disable)")
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--debug", action="store_true",
                        help="Provide debugging output")

    return parser.parse_args()


def debug(msg):
    """Print out the debug message."""
    print(f"# {msg}")


def handle_error(name):
    """Convert a traceback into a more-manageable error."""

    def decorator(fn):
        def new_fn(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                emsg = add_color(f"# ds9samp_{name} ({VERSION}):") + \
                    f" ERROR {exc}\n"
                sys.stderr.write(emsg)
                sys.exit(1)

            except KeyboardInterrupt:
                sys.stderr.write(add_color("# ds9samp_{name}:") +
                                 " Keyboard interrupt (control c)\n")
                sys.exit(1)

        new_fn.__doc__ = fn.__doc__
        new_fn.__name__ = fn.__name__
        new_fn.__dict__ = fn.__dict__
        new_fn.__module__ = fn.__module__
        return new_fn

    return decorator


@handle_error(name="get")
def main_get():
    """Call ds9.get <command>"""

    desc = """Send a single command to DS9 via SAMP and print out any response.

Examples:

    % ds9samp_get scale
    linear
    % ds9samp_get 'frame all'
    1 3
    % ds9samp_get 'frame frameno'
    3

"""
    args = parse(desc)
    with ds9samp(client=args.client) as ds9:
        if args.debug:
            debug(f"Connected: {ds9}")
            debug(f"Command: {args.command}")
            ds9.debug = True

        out = ds9.get(args.command, timeout=args.timeout)

    if out is None:
        if args.debug:
            debug("Command returned nothing.")
    else:
        print(out)


@handle_error(name="set")
def main_set():
    """Call ds9.set <command>

    If <command> begins with an @ then it is taken to be a
    file, containing multiple commands, one per line. Alternatively
    the new-lines can be included in the command.
    """

    desc = """Send one or more commands to DS9 via SAMP. If the command begins
with @ then it assumed to be a text file, with one command per line.

Commands can be read from stdin by specifying @-.

Any command errors will cause screen output but will not stop
running any remaining commands.

Examples:

    % ds9samp_set 'frame frameno 2'
    % ds9samp_set @commands
    % ds9samp_set 'frame delete all\nframe new'

"""
    args = parse(desc)

    if args.command.startswith("@"):
        # Special case "@-" to mean stdin
        if args.command == "@-":
            if args.debug:
                debug("Reading commands from stdin")

            commands = sys.stdin.read().split('\n')

        else:
            if args.debug:
                debug(f"Reading commands from {args.command[1:]}")

            # SAMP commands look to be ASCII not UTF-8.
            with open(args.command[1:], encoding="ascii", mode="rt") as fh:
                commands = fh.read().split('\n')

    else:
        # Note that argparse converts \n to \\n, hence the odd split call.
        commands = args.command.split('\\n')

    with ds9samp(client=args.client) as ds9:
        if args.debug:
            debug(f"Connected: {ds9}")
            ds9.debug = True

        ds9.timeout = args.timeout
        for command in commands:
            if command.strip() == '':
                continue

            if args.debug:
                debug(f"Command: {command}")

            ds9.set(command)


@handle_error(name="list")
def main_list():
    """Call list_ds9"""

    desc = """Display the names of the DS9 clients attached to the SAMP hub.

Examples:

    % ds9samp_list
    There is one DS9 client: c1
    % ds9samp_list
    There are 2 DS9 clients: c1 c56

"""
    usage = "%(prog)s [options]"
    parser = ArgumentParser(usage=usage, description=desc,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--verbose", action="store_true",
                        help="report the metadata from each client")

    args = parser.parse_args()

    clients = list_ds9()
    nclients = len(clients)
    if nclients == 0:
        raise OSError("There are no DS9 clients connected to the SAMP hub.")

    if nclients == 1:
        print(f"There is one DS9 client: {clients[0]}")
    else:
        names = " ".join(clients)
        print(f"There are {nclients} DS9 clients: {names}")

    if not args.verbose:
        return

    print("")
    for client in clients:
        with ds9samp(client=client) as ds9:
            print(f"* client {client}")
            for k, v in ds9.metadata.items():
                print(f"  {k:10s} {v}")

            print("")
