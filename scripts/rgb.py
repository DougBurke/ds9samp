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
