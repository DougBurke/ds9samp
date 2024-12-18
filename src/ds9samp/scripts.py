"""Provide simple one-show commands to set/get DS9 data."""

from optparse import OptionParser
import sys

from ds9samp import ds9samp, VERSION


def parse():
    usage = "usage: %prog [options] command"
    version = f"%prog {VERSION}"
    parser = OptionParser(usage=usage, version=version)
    parser.add_option("-n", "--name", type="str",
                      dest="client",
                      help="Name of DS9 client in the SAMP hub")
    parser.add_option("-t", "--timeout", type="int",
                      dest="timeout", default=10,
                      help="Timeout in seconds (integer)")

    opts, args = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments")

    return opts.client, opts.timeout, args[0]


def handle_error(name):
    """Convert a traceback into a more-manageable error."""

    def decorator(fn):
        def new_fn(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                emsg = f"# ds9samp_{name}: ERROR: {exc}\n"
                sys.stderr.write(emsg)
                sys.exit(1)

            except KeyboardInterrupt:
                sys.stderr.write("# ds9samp_{name}: "
                                 "Keyboard interrupt (control c)\n")
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

    client, timeout, command = parse()
    with ds9samp(client=client) as ds9:
        ds9.timeout = timeout
        out = ds9.get(command)

    if out is None:
        print("Command succeeded.")
    else:
        print(f"Returned: {out}")


@handle_error(name="set")
def main_set():
    """Call ds9.set <command>"""

    client, timeout, command = parse()
    with ds9samp(client=client) as ds9:
        ds9.timeout = timeout
        ds9.set(command)
