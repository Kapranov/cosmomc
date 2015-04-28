CosmoMC update: April 2015
-----------------------------------------

[Download from](http://cosmologist.info/cosmomc/private_DONTLINK_downs/)

Note that if you downloaded earlier today, it was updated just now to fix a couple of issues.

The February update mainly includes more extensive documentation for how to
use Planck 2015 chains with the python plotting and analysis tools, plus a few fixes. The Planck 2015
likelihoods will not be available for another month or so.

* For a detailed list of January 2015 changes see:

[January 2015](http://cosmologist.info/cosmomc/readme.html#Version)

Additions include the new Bicep-Keck-Planck (BKP) likelihood, new general CMB likelihood structures,
new support for weak lensing, redshift distortion and new types of BAO data, and updated data likelihoods.
To run with the BKP likelihood include batch2/BKPlanck.ini, or see the readme under batch2 for various
BKP-only configurations; the likelihood is native CosmoMC and included in the installation.

There is also a new pure-python version of GetDist, and a new GUI for browsing chains and
making plots. The plotting scripts no longer require you to run GetDist first - pre-computing a large
number of plot_data files - so making plots should be quicker and easier, as well as having the flexibility
to define new derived parameters on the fly.

* Please read the new Python, Planck, parameter grids, plotting and GUI specific documentation linked here:

[README](http://cosmologist.info/cosmomc/readme.html)

If anyone is still using Matlab plots, I suggest you learn how to use python instead. Python outputs are
much nicer and more flexible, and no new features are supported in the legacy Matlab scripts.


* For where to get and how to use Planck chains see

[Planck](http://cosmologist.info/cosmomc/readme_planck.html)

The +BKP chains are currently missing, but hopefully will be added soon.

As ever, please post any questions on CosmoCoffee.
