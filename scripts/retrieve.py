import numpy as np
import ds9samp

orig = np.random.randn(300, 400)

# Send it to DS9
with ds9samp.ds9samp() as ds9:
    ds9.send_array(orig)
    ds9.set("cmap gray")
    ds9.set("smooth function gaussian")
    ds9.set("smooth radius 3")

    # The color map and scaling do not change the retrieved values
    smoothed = ds9.retrieve_array()

    # Turn off the smoothing
    ds9.set("smooth off")

    # Identify the most-discrepant points in the smoothed image
    discrepant = np.abs(smoothed) > 3

    # Add it as a mask
    ds9.send_array(discrepant, mask=True)
