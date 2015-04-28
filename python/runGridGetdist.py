import os, iniFile, batchJobArgs, time, subprocess

def checkDir(fname):
    if not os.path.exists(fname): os.makedirs(fname)


Opts = batchJobArgs.batchArgs('Run getdist over the grid of models', notExist=True)
Opts.parser.add_argument('--update_only', action='store_true')
Opts.parser.add_argument('--plots', action='store_true')
Opts.parser.add_argument('--norun', action='store_true')
Opts.parser.add_argument('--plot_data', default=None, help="directory to store the plot_data in for each chain")
Opts.parser.add_argument('--burn_removed', action='store_true', help="if burn in has already been removed from chains")
Opts.parser.add_argument('--no_plots', action='store_true', help="just make non-plot outputs (faster)")
Opts.parser.add_argument('--delay', type=int, help="run after delay of some number of seconds")
Opts.parser.add_argument('--procs', type=int, default=1, help="number of getdist instances to run in parallel")
Opts.parser.add_argument('--command', default='./getdist', help="program to run")



(batch, args) = Opts.parseForBatch()

base_ini = 'getdist_common.ini'


plot_ext = 'py'
plot_cmd = 'python'

# plot_cmd = 'matlab'

# the plotting matlab run is optional and only if you are using plot_ext=m in getdist
plot_types = ['.', '_2D.']
# you don't need these for python plots generated separately
# '_tri.m' is very slow for so many

if args.plot_data is None: data_dir = batch.batchPath + 'plot_data' + os.sep
else: data_dir = os.path.abspath(args.plot_data) + os.sep
ini_dir = batch.batchPath + 'getdist' + os.sep

checkDir(data_dir)
checkDir(ini_dir)

if args.delay: time.sleep(args.delay)
processes = set()

if not args.plots:
        for jobItem in Opts.filteredBatchItems():
                ini = iniFile.iniFile()
                ini.params['file_root'] = jobItem.chainRoot
                checkDir(jobItem.distPath)
                ini.params['out_dir'] = jobItem.distPath
                ini.params['plot_data_dir'] = data_dir
                custom_plot = batch.commonPath + 'plots' + os.sep + jobItem.paramtag + '.ini'
                custom_plot2 = batch.commonPath + 'plots' + os.sep + jobItem.name + '.ini'
                if os.path.exists(custom_plot2):
                    ini.includes.append(custom_plot2)
                elif os.path.exists(custom_plot):
                    ini.includes.append(custom_plot)
#                elif len(jobItem.param_set) > 0:
#                   ini.params['plot_2D_param'] = jobItem.param_set[0]
                ini.defaults.append(batch.commonPath + base_ini)
                tag = ''
                if jobItem.isImportanceJob or args.burn_removed or jobItem.isBurnRemoved():
                    ini.params['ignore_rows'] = 0
                if jobItem.isImportanceJob:
                    ini.params['compare_num'] = 1
                    ini.params['compare1'] = jobItem.parent.chainRoot
                if args.no_plots: ini.params['no_plots'] = True
                fname = ini_dir + jobItem.name + tag + '.ini'
                ini.params.update(jobItem.dist_settings)
                ini.saveFile(fname)
                if not args.norun and (not args.notexist or not jobItem.getDistExists()) and (not args.update_only or jobItem.getDistNeedsUpdate()):
                    if jobItem.chainExists():
                        print "running: " + fname
                        processes.add(subprocess.Popen([args.command, fname]))
                        while len(processes) >= args.procs:
                            time.sleep(.1)
                            processes.difference_update([p for p in processes if p.poll() is not None])
#                        os.system(args.command + '' + fname)
                    else: print "Chains do not exist yet: " + jobItem.chainRoot



if not args.norun and args.plots:
        cat_cmd = 'cat '
        for jobItem in Opts.filteredBatchItems():
                if plot_ext == 'm': os.chdir(jobItem.distPath)
                for tp in plot_types:
                    fname = jobItem.distRoot + tp + plot_ext
                    print fname
                    if os.path.exists(fname):
                        cat_cmd = cat_cmd + ' ' + fname
                    if hasattr(jobItem, 'compareRoots'):
                        for root in jobItem.compareRoots:
                            fname = root + tp + plot_ext
                            print fname
                            if os.path.exists(fname):
                                cat_cmd = cat_cmd + ' ' + fname

        if len(cat_cmd) > 5: os.system(cat_cmd + '|' + plot_cmd)

#    if args.name is None and not args.compare_only:
#        specficPath = batch.batchPath + 'specific_plots' + os.sep
#        checkDir(specficPath)
#        os.chdir(specficPath)
#        os.system('export getdist_plot_data=' + data_dir + ';export MATLABPATH=' + batch.basePath + 'mscripts' + os.sep
#                    + ';cat ' + batch.commonPath + 'specificplots' + os.sep + '*.m | ' + matlab)

