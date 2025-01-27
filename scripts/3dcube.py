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
