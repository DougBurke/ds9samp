from ds9samp import ds9samp

with ds9samp() as ds9:
    ds9.set("url http://ds9.si.edu/download/data/img.fits")
    ds9.set("zscale")

    print("Click anwhere in the image")
    coord = ds9.get("imexam wcs icrs", timeout=0)
    x, y = [float(c) for c in coord.split()]
    print(f" -> '{coord}'")
    print(f" -> x={x}  y={y}")

    # Extract pixel data around this location, using a box size of 0.7
    # arcseconds.
    #
    size = 0.7 / 3600
    vals = ds9.get(f"data wcs {x} {y} {size:.5f} {size:.5f} no")
    print("Data values:")
    print(vals)
