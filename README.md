# DS9 and Python

DS9 can be controlled with XPA and SAMP. The AstroPy project
provides a SAMP interface, so it can be used to control DS9.
However, using the SAMP interface is likely to be annoying,
so can we make something a bit more user friendly?

## Usage

The aim is to support the "simple" case where

- DS9 has been started,
- and is connected to a SAMP hub (probably its own),
- the DS9 instance is not going to be closed down during processing,
- the code is only going to talk to a single DS9 instance
  (ideally only one DS9 is connected to the SAMP hub to make things
   easier),
- and each call is made synchronously, that is the response from
  DS9 is waited for before finishing the call.

If any of these conditions do not hold then the [DS9 SAMP
examples](https://sites.google.com/cfa.harvard.edu/saoimageds9/ds9-astropy)
and the [AstroPy SAMP
module](https://docs.astropy.org/en/stable/samp/) pages should be
read.

### Security warning

Note that there is no expectation of security in this module; the
connections to DS9 depend on the SAMP protocol, and in fact there is
no guarantee that a DS9 instance is actually being talked to. All
that is checked is that the SAMP client supports the "ds9.get" and
"ds9.set" SAMP message names.

### Expected use

The code is written as a "context manager", to make sure the
connection is cleaned up, and it expected to be used something like:

```python
from ds9samp import ds9samp

with ds9samp() as ds9:

    # At this point use
    #    ds9.set("...")
    #    ds9.get("...")
    # to send messages to and from the DS9 instance.
    #
```

If there are any syntax errors in the DS9 commands then a message is
printed to the stdout channel. An exception is not raised as this
would exit the context manager, and so close the connection, which
would not be useful for the expected work flow.

Exceptions will be raised if there are "low-level" SAMP problems,
such as the DS9 instance or the SAMP hub closing down.

### Direct access

If direct access is needed - that is, one where you are required to
close down the connection - then you can use

```python
import ds9samp

ds9 = ds9samp.start()
try:
    old_dir = ds9.get("cd")
    ds9.set("cd /tmp/")
    ...

finally:
    ds9samp.close(ds9)
```

### Command-line tools

The module comes with three command-line tools:

- ds9samp_get
- ds9samp_set
- ds9samp_list

The get and set tools allow you to make a single `ds9.get` or
`ds9.set` call, and the last one is useful if there are multiple
DS9 instances connected to the SAMP hub.

If the tools error out then the output message will include some
colorized text (in red), unless

- the [NO_COLOR environment variable](https://no-color.org/) is set,
- or the output is not a TTY (e.g. it is being piped to a file).

#### ds9samp_get

```
% ds9samp_get --help
usage: ds9samp_get [options] command

Send a single command to DS9 via SAMP and print out any response.

Examples:

    % ds9samp_get scale
    linear
    % ds9samp_get 'frame all'
    1 3
    % ds9samp_get 'frame frameno'
    3

positional arguments:
  command

options:
  -h, --help            show this help message and exit
  -n CLIENT, --name CLIENT
                        Name of DS9 client in the SAMP hub
  -t TIMEOUT, --timeout TIMEOUT
                        Timeout in seconds (integer, use 0 to disable)
  --version             show program's version number and exit
  --debug               Provide debugging output
```

As examples:

```
% ds9samp_get cmap
grey
% ds9samp_get 'frame frameno'
2
% ds9samp_get 'frame all'
1 2
```

#### ds9samp_set

```
% ds9samp_set --help
usage: ds9samp_set [options] command

Send one or more commands to DS9 via SAMP. If the command begins
with @ then it assumed to be a text file, with one command per line.

Any command errors will cause screen output but will not stop
running any remaining commands.

Examples:

    % ds9samp_set 'frame frameno 2'
    % ds9samp_set @commands
    % ds9samp_set 'frame delete all
frame new'

positional arguments:
  command

options:
  -h, --help            show this help message and exit
  -n CLIENT, --name CLIENT
                        Name of DS9 client in the SAMP hub
  -t TIMEOUT, --timeout TIMEOUT
                        Timeout in seconds (integer, use 0 to disable)
  --version             show program's version number and exit
  --debug               Provide debugging output
```

As examples:

```
% ds9samp_set 'cmap viridis'
% ds9samp_set 'frame delete all\nframe new'
```

#### ds9samp_list

The `ds9samp_list` script ignores any arguments or command-line options.

As an example:

```
% ds9samp_list
There is one DS9 client: c1
% ds9samp_list
There are 2 DS9 clients: c1 c7
```

### What happens if there are multiple DS9 instances?

A call to `ds9samp` or `start` can error out with the message:

```
OSError: Unable to support multiple DS9 SAMP clients. Try setting the client parameter.
```

In this case there are multiple DS9 instances connected to the SAMP hub.
If the hub can be queried then the "client name" for the DS9 instance
to use can be found, otherwise the ds9samp_list script can be used:

```
% There are 2 DS9 clients: c1 c4
```

Unfortunately there's no easy way to tell which is which. You can try
something like

```
% ds9samp_set "analysis message ok {Selected window}" --name c4 --timeout 0
```

(chose one of the names from the output above) as it should display
a pop up window centered on the DS9 instance.

The `ds9samp_get` and `ds9samp_set` commands accept a `--name` argument
which accepts the client name reported by `ds9samp_list`.

## Examples

### RGB Images

This is the same as the "RGB Images" section of the [DS9+Astropy
page](https://sites.google.com/cfa.harvard.edu/saoimageds9/ds9-astropy),
with several simplifications:

 - the "client name" of the DS9 application does not need to be
   specified, as this is handled for you
 - the timeout can be set once, rather than each call
 - since this interface is for DS9, and not a generic SAMP-enabled
   tool, we can hide some parts of the SAMP interface,
 - the connection is automatically closed for us.

```python
from ds9samp import ds9samp

with ds9samp() as ds9:
    ds9.timeout = 10  # this is the default setting
    ds9.set("rgb")
    ds9.set("rgb red")
    ds9.set("url http://ds9.si.edu/download/data/673nmos.fits")
    ds9.set("zscale")
    ds9.set("rgb green")
    ds9.set("url http://ds9.si.edu/download/data/656nmos.fits")
    ds9.set("zscale")
    ds9.set("rgb blue")
    ds9.set("url http://ds9.si.edu/download/data/502nmos.fits")
    ds9.set("zscale")
    ds9.set("rotate 270")
    ds9.set("zoom to fit")
```

### 3D Data Cube

This will create a file called `3d.gif` in the current working
directory:

```python
from pathlib import Path

from ds9samp import ds9samp

this_dir = Path().resolve()

with ds9samp() as ds9:
    ds9.set("frame delete all")
    ds9.set(f"cd {this_dir}")
    ds9.set("3d")
    ds9.set("url http://ds9.si.edu/download/data/image3d.fits")
    ds9.set("cmap viridis")
    ds9.set("movie 3d gif 3d.gif number 10 az from -90 az to 90 el from 45 el to 45 zoom from 4 zoom to 4 oscillate 1")
```

### Imexam

Note that the timeout for the `imexam wcs icrs` is set to 0 so that
it does not fail because the user has taken too long to select a
position.

```python
from ds9samp import ds9samp

with ds9samp() as ds9:
    ds9.set("url http://ds9.si.edu/download/data/img.fits")
    ds9.set("zscale")

    print("Click anwhere in the image")
    coord = ds9.get("imexam wcs icrs", timeout=0)
    print(f" -> {coord}")
```

If a `get` call returns a value then it is returned as a string.
