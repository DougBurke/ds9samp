# Changes for ds9samp

## Version 0.0.5 - 2025-01-27

The `send_array` method will create a new frame if needed (otherwise
the call to load the array data will fail).

## Version 0.0.4 - 2025-01-27

The command-line tools now include the package version number when
reporting an error. For example:

    % ds9samp_list
    # ds9samp_list (0.0.4): ERROR Unable to find a running SAMP Hub.

## Version 0.0.3 - 2025-01-24

Added the `send_array` method to allow users to send a NumPy array
directly to DS9. Added this
[changelog](https://github.com/cxcsds/ds9samp/blob/main/CHANGELOG.md).

## Version 0.0.2 - 2025-01-17

A documentation release:

- added a note about the
[astropy-samp-ds9](https://pypi.org/project/astropy-samp-ds9/) Python
version that was released at essentially the same time as `ds9samp`;

- added links to some of the tools and systems we talk about;

- and additions and improvements to the README.

## Version 0.0.1 - 2024-12-20

Initial version.
