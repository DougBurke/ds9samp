"""Simplify the connection to DS9 using SAMP.

See https://sites.google.com/cfa.harvard.edu/saoimageds9/ds9-astropy

This is a simplified interface and assumes certain things, such as a
SAMP hub is running and the DS9 instance remains connected to it while
the module is run.

Please note that SAMP is not designed as a secure connection system,
and this module assumes that if a SAMP client supports ds9.set and
ds9.get methods then it is DS9 (or a valid DS9 emulator).

"""

from contextlib import contextmanager
import importlib.metadata

from astropy import samp

__all__ = ["ds9samp"]


VERSION = importlib.metadata.version("ds9samp")


class Connection:
    """Store the DS9 connection."""

    def __init__(self,
                 ds9: samp.SAMPIntegratedClient,
                 client: str
                 ) -> None:

        self.ds9 = ds9
        self.client = client
        self.metadata = ds9.get_metadata(client)
        self.timeout = 10
        """Timeout, in seconds (must be an integer)."""

    def __str__(self) -> str:
        try:
            version = self.metadata['ds9.version']
        except KeyError:
            version = "<unknown>"

        return f"Connection to DS9 {version} (client {self.client})"

    def get(self,
            command: str
            ) -> str | None:
        """Call ds9.get for the given command and arguments.

        If the call fails then a ValueError is raised.

        Parameters
        ----------
        command
           The DS9 command to call, e.g. "cmap"

        Returns
        -------
        retval
           The return value, as a string, or None if there was no
           return value.

        """

        out = self.ds9.ecall_and_wait(self.client,
                                      "ds9.get",
                                      timeout=str(int(self.timeout)),
                                      cmd=command)

        status = out["samp.status"]
        if status != "samp.ok":
            evals = out["samp.error"]
            try:
                emsg = f"DS9 reported: {evals['samp.errortxt']}"
            except KeyError:
                emsg = "Unknown DS9 error"

            if status == "samp.error":
                raise ValueError(emsg)

            print(f"WARNING: {emsg}")

        # We assume that there is a result, but the value may not
        # exist.
        #
        result = out["samp.result"]
        try:
            return result["value"]
        except KeyError:
            return None

    def set(self,
            command: str
            ) -> None:
        """Call ds9.set for the given command and arguments.

        If the call fails then a ValueError is raised. The assumption
        here is that ds9.set never returns any information.

        Parameters
        ----------
        command
           The DS9 command to call, e.g. "cmap viridis"

        """

        # Use ecall_and_wait to
        # - validate the message
        # - ensure it's been processed by DS9
        #
        # rather than sending the message and continuing before it has
        # been handled by DS9.
        #
        out = self.ds9.ecall_and_wait(self.client, "ds9.get",
                                      timeout=str(int(self.timeout)),
                                      cmd=command)

        status = out["samp.status"]
        if status == "samp.ok":
            return

        evals = out["samp.error"]
        try:
            emsg = f"DS9 reported: {evals['samp.errortxt']}"
        except KeyError:
            emsg = "Unknown DS9 error"

        # Does DS9 support samp.warning?
        if status == "samp.warning":
            print(f"WARNING: {emsg}")
            return

        raise ValueError(emsg)


def start(name: str | None = None,
          desc: str | None = None,
          client: str | None = None
          ) -> Connection:
    """Set up the SAMP connection.

    This checks that a DS9 instance exists and is connected to
    the SAMP hub.

    Parameters
    ----------
    name: optional
       Override the default name.
    desc: optional
       Override the default description.
    client: optional
       The name of the DS9 client to use (only needed if multiple
       DS9 instances are connected to the hub).

    Returns
    -------
    connection
       Used to represent the DS9 SAMP connection.

    """

    name = "ds9samp" if name is None else name
    desc = "Client created by ds9samp" if desc is None else desc
    ds9 = samp.SAMPIntegratedClient(name=name, description=desc,
                                    metadata={"ds9samp.version": VERSION})

    ds9.connect()

    # Is there a DS9 instance to connect to? Just because something
    # supports ds9.get does not mean it is DS9, so check that we
    # at least have the interfaces we need and assume that whoever
    # is on the other end is doing the right thing. This is not
    # a secure connection!
    #
    gkeys = ds9.get_subscribed_clients("ds9.get").keys()
    skeys = ds9.get_subscribed_clients("ds9.set").keys()
    names = set(gkeys) & set(skeys)

    if len(names) == 0:
        raise OSError("Unable to find a SAMP client that "
                      "supports ds9.get/set")

    # For now require a single connection, since it makes the
    # processing of calls a lot easier. Unfortunately there's no easy
    # way for a user to say "use this version", so they have to use
    # the actual client name (which they can get from the SAMP Hub).
    #
    #
    if client is not None:
        if client in names:
            name = client
        else:
            raise ValueError(f"client name {client} is not valid")

    else:
        if len(names) > 1:
            raise OSError("Unable to support multiple DS9 SAMP clients. Try setting the client parameter.")

        name = names.pop()

    return Connection(ds9=ds9, client=name)


def end(connection: Connection) -> None:
    """Stop the connection to the DS9 hub.

    This does not close the hub or the DS9 instance.

    Parameters
    ----------
    connection
       The DS9 connection.

    """

    connection.ds9.disconnect()


@contextmanager
def ds9samp(name: str | None = None,
            desc: str | None = None,
            client: str | None = None
            ) -> Connection:
    """Set up the SAMP connection.

    This checks that a DS9 instance exists and is connected to
    the SAMP hub. The connection will be automatically closed
    when used as a context manager.

    Parameters
    ----------
    name: optional
       Override the default name.
    desc: optional
       Override the default description.
    client: optional
       The name of the DS9 client to use (only needed if multiple
       DS9 instances are connected to the hub).

    Returns
    -------
    connection
       Used to represent the DS9 SAMP connection.

    """

    conn = start(name=name, desc=desc, client=client)
    try:
        yield conn
    finally:
        end(conn)