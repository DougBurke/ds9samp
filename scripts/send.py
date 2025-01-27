import numpy as np
import ds9samp

# Create a rotated elliptical gaussian
x0 = 2200
x1 = 3510
theta = 1.2
ellip = 0.4
fwhm = 400

# The grid is x=2000...2500 and y=3000...4000 (inclusive).
#
x1s, x0s = np.mgrid[3000:4001, 2000:2501]

# Create the "delta" values
dx0 = (x0s - x0) * np.cos(theta) + (x1s - x1) * np.sin(theta)
dx1 = (x1s - x1) * np.cos(theta) - (x0s - x0) * np.sin(theta)

# Create the gaussian image
r2 = ((dx0 * (1 - ellip))**2  + dx1**2) / (fwhm * (1 - ellip))**2
img = np.exp(-4 * np.log(2) * r2)

# Send it to DS9
with ds9samp.ds9samp() as ds9:
    ds9.send_array(img)
    ds9.set("cmap viridis")
