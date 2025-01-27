"""Simplify the connection to DS9 using SAMP.

This is a simplified interface to talking to DS9 with SAMP, and
assumes certain things, such as:

- a SAMP hub is running,
- the DS9 instance remains connected to it while the module is run,
- there is only one DS9 instance to talk to,
- connections with other SAMP capable clients is not needed,
- and commands are to be executed synchronously (i.e. each command is
  executed and acknowledged by DS9 before the next command is processed).

For more complex cases see the `DS9 SAMP documentation <https://sites.google.com/cfa.harvard.edu/saoimageds9/ds9-astropy>`_
and the `AstroPy SAMP module
<https://docs.astropy.org/en/stable/samp/>`_.

Please note that SAMP is not designed as a secure connection system,
and this module assumes that if a SAMP client supports ds9.set and
ds9.get methods then it is DS9 (or a valid DS9 emulator).

Simple usage
------------

The ds9samp.ds9samp routine is used to create a object that can control
the DS9 instance:

    import ds9samp
    with ds9samp.ds9samp() as ds9:
        ds9.set("frame delete all")
        ds9.set("url http://ds9.si.edu/download/data/img.fits")
        ds9.set("zscale")
        ds9.set("cmap viridis")

The get method will return a value (as a string or None if there is
no response).

Syntax errors are displayed as a screen message (to stdout) but they
do not stop the connection. Lower-level errors - such as the DS9
instance being closed - will raise an error and this will exit the
context manager, and so the connection will be closed.

Direct access
-------------

The `ds9samp.start` routine will return an object that the user is
required to close, via `ds9samp.end`. The previous example can be
written as:

    import ds9samp
    ds9 = ds9samp.start()
    try:
        ds9.set("frame delete all")
        ds9.set("url http://ds9.si.edu/download/data/img.fits")
        ds9.set("zscale")
        ds9.set("cmap viridis")
    finally:
        ds9.end()

Sending images directly
-----------------------

It is possible to send DS9 the contents of a NumPy array directly
by using the `NumPy memmap
<https://numpy.org/doc/stable/reference/generated/numpy.memmap.html>`_
call to create a temporary file. This has been automated with the
`send_array` call. For example:

    import numpy as np
    import ds9samp
    # Create a rotated elliptical gaussian
    x0 = 2200
    x1 = 3510
    theta = 1.2
    ellip = 0.4
    fwhm = 400
    x1s, x0s = np.mgrid[3000:4001, 2000:2501]
    dx0 = (x0s - x0) * np.cos(theta) + (x1s - x1) * np.sin(theta)
    dx1 = (x1s - x1) * np.cos(theta) - (x0s - x0) * np.sin(theta)
    r2 = ((dx0 * (1 - ellip))**2  + dx1**2) / (fwhm * (1 - ellip))**2
    img = np.exp(-4 * np.log(2) * r2)
    # Send it to DS9
    with ds9samp.ds9samp() as ds9:
        ds9.send_array(img)
        ds9.set("cmap viridis")

For more complex cases the creation of the memmap-ed file should be
done manually, as described in the `DS9 example
<https://sites.google.com/cfa.harvard.edu/saoimageds9/ds9-astropy>`_.

Timeouts
--------

The default timeout for the set and get calls is 10 seconds, and this
can be changed by either setting the timeout attribute of the
connection, or by over-riding this value for a single call with the
timeout parameter for the get and set methods. Note that the timeout
must be an integer, and 0 is used to turn off the timeout.

For get calls it is suggested to set the timeout to 0 if the command
requires user interaction, such as selecting a location.

How to connect to a particular DS9 instance
-------------------------------------------

If there are multiple DS9 instances connected to the SAMP hub then
ds9samp.ds9samp or ds9samp.start must be called with the client
argument set to select the DS9 instance to talk to.

The ds9samp.list_ds9 routine returns a list of client names to use.
Unfortunately it's not immediately obvious how to map a client name to
a particular instance. One solution is to ask DS9 to display a window
with a command like

    % ds9samp_set "analysis message og {Selected window}" --name cl3 --timeout 0

(replacing cl3 by one of the values reported by list_samp).

"""

from contextlib import contextmanager
import importlib.metadata
import tempfile

import numpy as np

from astropy import samp

__all__ = ["ds9samp", "list_ds9"]


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
            command: str,
            timeout: int | None = None
            ) -> str | None:
        """Call ds9.get for the given command and arguments.

        If the call fails then an error message is displayed (to
        stdout) and None is returned. This call will raise an error if
        there is a SAMP commmunication problem.

        Parameters
        ----------
        command
           The DS9 command to call, e.g. "cmap"
        timeout: optional
           Over-ride the default timeout setting. Use 0 to remove
           any timeout.

        Returns
        -------
        retval
           The return value, as a string, or None if there was no
           return value.

        """

        tout = self.timeout if timeout is None else timeout
        tout_str = str(int(tout))
        out = self.ds9.ecall_and_wait(self.client, "ds9.get",
                                      timeout=tout_str, cmd=command)

        status = out["samp.status"]
        if status != "samp.ok":
            evals = out["samp.error"]
            try:
                emsg = f"DS9 reported: {evals['samp.errortxt']}"
            except KeyError:
                emsg = "Unknown DS9 error"

            if status == "samp.error":
                print(f"ERROR: {emsg}")
                return None

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
            command: str,
            timeout: int | None = None
            ) -> None:
        """Call ds9.set for the given command and arguments.

        If the call fails then an error message is displayed (to
        stdout). The assumption here is that ds9.set never returns any
        information. This call will raise an error if there is a SAMP
        commmunication problem.

        Parameters
        ----------
        command
           The DS9 command to call, e.g. "cmap viridis"
        timeout: optional
           Over-ride the default timeout setting. Use 0 to remove
           any timeout.

        """

        # Use ecall_and_wait to
        # - validate the message
        # - ensure it's been processed by DS9
        #
        # rather than sending the message and continuing before it has
        # been handled by DS9.
        #
        tout = self.timeout if timeout is None else timeout
        tout_str = str(int(tout))
        out = self.ds9.ecall_and_wait(self.client, "ds9.set",
                                      timeout=tout_str, cmd=command)

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

        print(f"ERROR: {emsg}")

    def send_array(self,
                   img: np.ndarray,
                   *,
                   mask: bool = False,
                   timeout: int | None = None
                   ) -> None:
        """Send the array to DS9.

        This creates a temporary file to store the data,
        sends the data, and then deletes the file.

        .. versionchanged:: 0.0.5
           A DS9 frame will be created if needed. The mask argument
           has been added and optional arguments are now keyword-only
           arguments.

        .. versionadded:: 0.0.3

        Parameters
        ----------
        img:
           The 2D data to send.
        mask: optional
           Should the array be treated as a mask?
        timeout: optional
           The timeout, in seconds. If not set then use the
           default timeout value.

        See Also
        --------
        retrieve_array

        """

        # Create a frame if necessary, since otherwise the ARRAY call
        # will fail.
        #
        if self.get("frame active") is None:
            self.set("frame new")

        # Map between NumPy and DS9 storage fields.
        #
        # Hack in support for bool values
        if img.dtype.type == np.bool_:
            img = img.astype("int8")

        arr = np_to_array(img)
        with tempfile.NamedTemporaryFile(prefix="ds9samp",
                                         suffix=".arr") as fh:
            fp = np.memmap(fh, mode='w+', dtype=img.dtype,
                           shape=img.shape)
            fp[:] = img
            fp.flush()

            # Should this over-ride the filename as it is going to be
            # invalid as soon as this call ends? I am not sure that it
            # is possible.
            #
            cmd = "array "
            if mask:
                cmd += "mask "
            cmd += f" {fh.name}{arr}"
            self.set(cmd, timeout=timeout)

    def retrieve_array(self,
                       *,
                       timeout: int | None = None
                       ) -> np.ndarray:
        """Get the current frame as a NumPy array.

        .. versionadded:: 0.0.5

        Parameters
        ----------
        timeout: optional
           The timeout, in seconds. If not set then use the
           default timeout value.

        See Also
        --------
        send_array

        Notes
        -----

        An alternative would be to get DS9 to create a FITS file and
        then read that in.

        """

        # Get the data information before creating the temporary file.
        # Do we have to worry about WCS messing around with the units?
        #
        # These values should convert, so do not try to improve the
        # error handling.
        #
        bitpix = int(self.get("fits bitpix"))
        nx = int(self.get("fits width"))
        ny = int(self.get("fits height"))

        dtype = bitpix_to_dtype(bitpix)

        with tempfile.NamedTemporaryFile(prefix="ds9samp",
                                         suffix=".arr") as fh:
            cmd = f"export array {fh.name} native"
            self.set(cmd, timeout=timeout)

            fp = np.memmap(fh.name, dtype=dtype, mode='r', shape=(ny, nx))
            out = fp[:]

        return out


# From https://ds9.si.edu/doc/ref/file.html the array command says
#    xdim=value
#    ydim=value
#    zdim=value # default is a depth of 1
#    dim=value
#    dims=value
#    bitpix=[8|16|-16|32|64|-32|-64]
#    skip=value # must be even, most must be factor of 4
#    arch|endian=[big|bigendian|little|littleendian]
#
def np_to_array(img: np.ndarray) -> str:
    """Convert from NumPy data type to DS9 settings."""

    # For now restrict to 2D data only
    #
    if img.ndim != 2:
        raise ValueError(f"img must be 2D, sent {img.ndim}D")

    ny, nx = img.shape
    bpix = dtype_to_bitpix(img.dtype)
    out = f"xdim={nx},ydim={ny},bitpix={bpix}"

    # Is this needed?
    match img.dtype.byteorder:
        case '<':
            out += ",arch=little"
        case '>':
            out += ",arch=big"
        case _:  # handle native and not-applicable
            pass

    return f"[{out}]"


def dtype_to_bitpix(dtype: np.dtype) -> int:
    """Convert the data type to DS9/FITS BITPIX setting."""

    # Not trying to be clever here. Can we just piggy back on astropy
    # instead?
    #
    size = dtype.itemsize
    if np.issubdtype(dtype, np.integer):
        # Unfortunately unsigned types are not going to be handled
        # well here for those elements with the MSB/LSB set. Should
        # we warn the user in this case or error out?
        #
        return size * 8

    if np.issubdtype(dtype, np.floating):
        return size * -8

    raise ValueError(f"Unsupported dtype: {dtype}")


def bitpix_to_dtype(bpix: int) -> np.dtype:
    """Convert the DS9/FITS BITPIX setting to a NumPy datatype"""

    match bpix:
        case -64: return np.dtype("float64")
        case -32: return np.dtype("float32")
        case -16: return np.dtype("float16")

        case 64: return np.dtype("int64")
        case 32: return np.dtype("int32")
        case 16: return np.dtype("int16")
        case 8: return np.dtype("int8")

        case _: raise ValueError(f"Unsupported BITPIX: {bpix}")


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

    See Also
    --------
    ds9samp, end, list_ds9

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
        ds9.disconnect()
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
            ds9.disconnect()
            raise ValueError(f"client name {client} is not valid")

    else:
        if len(names) > 1:
            ds9.disconnect()
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

    See Also
    --------
    ds9samp, start

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

    See Also
    --------
    end, list_ds9, start

    """

    conn = start(name=name, desc=desc, client=client)
    try:
        yield conn
    finally:
        end(conn)


def list_ds9() -> list[str]:
    """Return the SAMP client names of all the SAMP-connected DS9s.

    This is only needed when ds9samp errors out because there are
    multiple SAMP clients available. This routine lets a user find out
    what names can be used for the client argument.

    See Also
    --------
    ds9samp, start

    """

    temp = samp.SAMPIntegratedClient(name="ds9samp-list",
                                     description="Identify DS9 clients",
                                     metadata={"ds9samp-list.version": VERSION})
    temp.connect()
    try:
        gkeys = temp.get_subscribed_clients("ds9.get").keys()
        skeys = temp.get_subscribed_clients("ds9.set").keys()
    finally:
        temp.disconnect()

    keys = set(gkeys) & set(skeys)
    return sorted(keys)
