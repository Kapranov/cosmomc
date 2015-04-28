# settings to test out BKP-only runs
import batchJob

# Directory to find .ini files
ini_dir = 'batch2/'

# directory to look for existing covariance matrices
covmat = 'planck_covmats/BKPlanck.covmat'

# ini files you want to base each set of runs on
defaults = ['common.ini']

# set up list of groups of parameters and data sets
groups = []

# make first group of runs (all parameter variations with all data combinations)
g = batchJob.jobGroup('main')

g.params = [['r']]

# skip lensing for now as slow
variants = ['fiducial', 'y1y2', '9bins', 'no217', 'relaxbetad', 'relaxalphad', 'sync000', 'sync100']

g.datasets = []

for i, var in enumerate(variants):
    g.datasets.append(batchJob.dataSet(['BKPlanckonly', var], [{'root_dir':''},
                                                               'BKPlanck/BKPlanck_0%u_%s.ini' % (i + 1, var)]))


# add importance name tags, and list of specific .ini files to include (in batch1/)
g.importanceRuns = []

groups.append(g)
