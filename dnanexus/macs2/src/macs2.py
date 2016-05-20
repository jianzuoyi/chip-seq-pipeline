#!/usr/bin/env python
# macs2 0.0.1
# Generated by dx-app-wizard.
#
# Basic execution pattern: Your app will run on a single machine from
# beginning to end.
#
# See https://wiki.dnanexus.com/Developer-Portal for documentation and
# tutorials on how to modify this file.
#
# DNAnexus Python Bindings (dxpy) documentation:
#   http://autodoc.dnanexus.com/bindings/python/current/

import os, time, common
import dxpy

@dxpy.entry_point('main')
def main(experiment, control, xcor_scores_input, chrom_sizes, narrowpeak_as, gappedpeak_as, broadpeak_as, genomesize):

    # Initialize data object inputs on the platform
    # into dxpy.DXDataObject instances.

    experiment        = dxpy.DXFile(experiment)
    control           = dxpy.DXFile(control)
    xcor_scores_input = dxpy.DXFile(xcor_scores_input)
    chrom_sizes       = dxpy.DXFile(chrom_sizes)
    narrowPeak_as     = dxpy.DXFile(narrowpeak_as)
    gappedPeak_as     = dxpy.DXFile(gappedpeak_as)
    broadPeak_as      = dxpy.DXFile(broadpeak_as)

    # Download the file inputs to the local file system
    # and use their own filenames.

    dxpy.download_dxfile(experiment.get_id(),        experiment.name)
    dxpy.download_dxfile(control.get_id(),           control.name)
    dxpy.download_dxfile(xcor_scores_input.get_id(), xcor_scores_input.name)
    dxpy.download_dxfile(chrom_sizes.get_id(),       chrom_sizes.name)
    dxpy.download_dxfile(narrowPeak_as.get_id(),     narrowPeak_as.name)
    dxpy.download_dxfile(gappedPeak_as.get_id(),     gappedPeak_as.name)
    dxpy.download_dxfile(broadPeak_as.get_id(),      broadPeak_as.name)

    #Define the output filenames

    peaks_dirname = 'peaks_macs'
    if not os.path.exists(peaks_dirname):
        os.makedirs(peaks_dirname)
    prefix = experiment.name
    if prefix.endswith('.gz'):
        prefix = prefix[:-3]

    narrowPeak_fn    = "%s/%s.narrowPeak" %(peaks_dirname, prefix)
    gappedPeak_fn    = "%s/%s.gappedPeak" %(peaks_dirname, prefix)
    broadPeak_fn     = "%s/%s.broadPeak"  %(peaks_dirname, prefix)
    narrowPeak_gz_fn = narrowPeak_fn + ".gz"
    gappedPeak_gz_fn = gappedPeak_fn + ".gz"
    broadPeak_gz_fn  = broadPeak_fn  + ".gz"
    narrowPeak_bb_fn = "%s.bb" %(narrowPeak_fn)
    gappedPeak_bb_fn = "%s.bb" %(gappedPeak_fn)
    broadPeak_bb_fn  = "%s.bb" %(broadPeak_fn)
    fc_signal_fn     = "%s/%s.fc_signal.bw"     %(peaks_dirname, prefix)
    pvalue_signal_fn = "%s/%s.pvalue_signal.bw" %(peaks_dirname, prefix)

    #Extract the fragment length estimate from column 3 of the cross-correlation scores file
    with open(xcor_scores_input.name,'r') as fh:
        firstline = fh.readline()
        fraglen = firstline.split()[2] #third column
        print "Fraglen %s" %(fraglen)

    #===========================================
    # Generate narrow peaks and preliminary signal tracks
    #============================================

    command = 'macs2 callpeak ' + \
              '-t %s -c %s ' %(experiment.name, control.name) + \
              '-f BED -n %s/%s ' %(peaks_dirname, prefix) + \
              '-g %s -p 1e-2 --nomodel --shift 0 --extsize %s --keep-dup all -B --SPMR' %(genomesize, fraglen)
    print command
    returncode = common.block_on(command)
    print "MACS2 exited with returncode %d" %(returncode)
    assert returncode == 0, "MACS2 non-zero return"

    # MACS2 sometimes calls features off the end of chromosomes.  Fix that.
    clipped_narrowpeak_fn = common.slop_clip('%s/%s_peaks.narrowPeak' %(peaks_dirname, prefix), chrom_sizes.name)

    # Rescale Col5 scores to range 10-1000 to conform to narrowPeak.as format (score must be <1000)
    rescaled_narrowpeak_fn = common.rescale_scores(clipped_narrowpeak_fn, scores_col=5)

    # Sort by Col8 in descending order and replace long peak names in Column 4 with Peak_<peakRank>
    pipe = ['sort -k 8gr,8gr %s' %(rescaled_narrowpeak_fn),
            r"""awk 'BEGIN{OFS="\t"}{$4="Peak_"NR ; print $0}'""",
            'tee %s' %(narrowPeak_fn),
            'gzip -c']
    print pipe
    out,err = common.run_pipe(pipe,'%s' %(narrowPeak_gz_fn))

    # remove additional files
    #rm -f ${PEAK_OUTPUT_DIR}/${CHIP_TA_PREFIX}_peaks.xls ${PEAK_OUTPUT_DIR}/${CHIP_TA_PREFIX}_peaks.bed ${peakFile}_summits.bed

    #===========================================
    # Generate Broad and Gapped Peaks
    #============================================

    command = 'macs2 callpeak ' + \
              '-t %s -c %s ' %(experiment.name, control.name) + \
              '-f BED -n %s/%s ' %(peaks_dirname, prefix) + \
              '-g %s -p 1e-2 --broad --nomodel --shift 0 --extsize %s --keep-dup all' %(genomesize, fraglen)
    print command
    returncode = common.block_on(command)
    print "MACS2 exited with returncode %d" %(returncode)
    assert returncode == 0, "MACS2 non-zero return"

    # MACS2 sometimes calls features off the end of chromosomes.  Fix that.
    clipped_broadpeak_fn = common.slop_clip('%s/%s_peaks.broadPeak' %(peaks_dirname, prefix), chrom_sizes.name)

    # Rescale Col5 scores to range 10-1000 to conform to narrowPeak.as format (score must be <1000)
    rescaled_broadpeak_fn = common.rescale_scores(clipped_broadpeak_fn, scores_col=5)

    # Sort by Col8 (for broadPeak) or Col 14(for gappedPeak)  in descending order and replace long peak names in Column 4 with Peak_<peakRank>
    pipe = ['sort -k 8gr,8gr %s' %(rescaled_broadpeak_fn),
            r"""awk 'BEGIN{OFS="\t"}{$4="Peak_"NR ; print $0}'""",
            'tee %s' %(broadPeak_fn),
            'gzip -c']
    print pipe
    out,err = common.run_pipe(pipe,'%s' %(broadPeak_gz_fn))

    # MACS2 sometimes calls features off the end of chromosomes.  Fix that.
    clipped_gappedpeaks_fn = common.slop_clip('%s/%s_peaks.gappedPeak' %(peaks_dirname, prefix), chrom_sizes.name)

    # Rescale Col5 scores to range 10-1000 to conform to narrowPeak.as format (score must be <1000)
    rescaled_gappedpeak_fn = common.rescale_scores(clipped_gappedpeaks_fn, scores_col=5)

    pipe = ['sort -k 14gr,14gr %s' %(rescaled_gappedpeak_fn),
            r"""awk 'BEGIN{OFS="\t"}{$4="Peak_"NR ; print $0}'""",
            'tee %s' %(gappedPeak_fn),
            'gzip -c']
    print pipe
    out,err = common.run_pipe(pipe,'%s' %(gappedPeak_gz_fn))

    # remove additional files
    #rm -f ${PEAK_OUTPUT_DIR}/${CHIP_TA_PREFIX}_peaks.xls ${PEAK_OUTPUT_DIR}/${CHIP_TA_PREFIX}_peaks.bed ${peakFile}_summits.bed

    #===========================================
    # For Fold enrichment signal tracks
    #============================================

    # This file is a tab delimited file with 2 columns Col1 (chromosome name), Col2 (chromosome size in bp).

    command = 'macs2 bdgcmp ' + \
              '-t %s/%s_treat_pileup.bdg ' %(peaks_dirname, prefix) + \
              '-c %s/%s_control_lambda.bdg ' %(peaks_dirname, prefix) + \
              '--outdir %s -o %s_FE.bdg ' %(peaks_dirname, prefix) + \
              '-m FE'
    print command
    returncode = common.block_on(command)
    print "MACS2 exited with returncode %d" %(returncode)
    assert returncode == 0, "MACS2 non-zero return"
    
    # Remove coordinates outside chromosome sizes (stupid MACS2 bug)
    pipe = ['slopBed -i %s/%s_FE.bdg -g %s -b 0' %(peaks_dirname, prefix, chrom_sizes.name),
            'bedClip stdin %s %s/%s.fc.signal.bedgraph' %(chrom_sizes.name, peaks_dirname, prefix)]
    print pipe
    out, err = common.run_pipe(pipe)

    #rm -f ${PEAK_OUTPUT_DIR}/${CHIP_TA_PREFIX}_FE.bdg

    # Convert bedgraph to bigwig
    command = 'bedGraphToBigWig ' + \
              '%s/%s.fc.signal.bedgraph ' %(peaks_dirname, prefix) + \
              '%s ' %(chrom_sizes.name) + \
              '%s' %(fc_signal_fn)
    print command
    returncode = common.block_on(command)
    print "bedGraphToBigWig exited with returncode %d" %(returncode)
    assert returncode == 0, "bedGraphToBigWig non-zero return"
    #rm -f ${PEAK_OUTPUT_DIR}/${CHIP_TA_PREFIX}.fc.signal.bedgraph
    
    #===========================================
    # For -log10(p-value) signal tracks
    #============================================

    # Compute sval = min(no. of reads in ChIP, no. of reads in control) / 1,000,000

    out, err = common.run_pipe([
        'gzip -dc %s' %(experiment.name),
        'wc -l'])
    chipReads = out.strip()
    out, err = common.run_pipe([
        'gzip -dc %s' %(control.name),
        'wc -l'])
    controlReads = out.strip()
    sval=str(min(float(chipReads), float(controlReads))/1000000)

    print "chipReads = %s, controlReads = %s, sval = %s" %(chipReads, controlReads, sval)

    returncode = common.block_on(
        'macs2 bdgcmp ' + \
        '-t %s/%s_treat_pileup.bdg ' %(peaks_dirname, prefix) + \
        '-c %s/%s_control_lambda.bdg ' %(peaks_dirname, prefix) + \
        '--outdir %s -o %s_ppois.bdg ' %(peaks_dirname, prefix) + \
        '-m ppois -S %s' %(sval))
    print "MACS2 exited with returncode %d" %(returncode)
    assert returncode == 0, "MACS2 non-zero return"

    # Remove coordinates outside chromosome sizes (stupid MACS2 bug)
    pipe = ['slopBed -i %s/%s_ppois.bdg -g %s -b 0' %(peaks_dirname, prefix, chrom_sizes.name),
            'bedClip stdin %s %s/%s.pval.signal.bedgraph' %(chrom_sizes.name, peaks_dirname, prefix)]
    print pipe
    out, err = common.run_pipe(pipe)

    #rm -rf ${PEAK_OUTPUT_DIR}/${CHIP_TA_PREFIX}_ppois.bdg

    # Convert bedgraph to bigwig
    command = 'bedGraphToBigWig ' + \
              '%s/%s.pval.signal.bedgraph ' %(peaks_dirname, prefix) + \
              '%s ' %(chrom_sizes.name) + \
              '%s' %(pvalue_signal_fn)
    print command
    returncode = common.block_on(command)
    print "bedGraphToBigWig exited with returncode %d" %(returncode)
    assert returncode == 0, "bedGraphToBigWig non-zero return"

    #rm -f ${PEAK_OUTPUT_DIR}/${CHIP_TA_PREFIX}.pval.signal.bedgraph
    #rm -f ${PEAK_OUTPUT_DIR}/${CHIP_TA_PREFIX}_treat_pileup.bdg ${peakFile}_control_lambda.bdg

    #===========================================
    # Generate bigWigs from beds to support trackhub visualization of peak files
    #============================================

    narrowPeak_bb_fname = common.bed2bb('%s' %(narrowPeak_fn), chrom_sizes.name, narrowPeak_as.name, bed_type='bed6+4')
    gappedPeak_bb_fname = common.bed2bb('%s' %(gappedPeak_fn), chrom_sizes.name, gappedPeak_as.name, bed_type='bed12+3')
    broadPeak_bb_fname =  common.bed2bb('%s' %(broadPeak_fn),  chrom_sizes.name, broadPeak_as.name,  bed_type='bed6+3')

    #Temporary during development to create empty files just to get the applet to exit 
    # for fn in [narrowPeak_fn, gappedPeak_fn, broadPeak_fn, narrowPeak_bb_fn, gappedPeak_bb_fn, broadPeak_bb_fn, fc_signal_fn, pvalue_signal_fn]:
    #     common.block_on('touch %s' %(fn))

    # Upload the file outputs

    narrowPeak    = dxpy.upload_local_file(narrowPeak_gz_fn)
    gappedPeak    = dxpy.upload_local_file(gappedPeak_gz_fn)
    broadPeak     = dxpy.upload_local_file(broadPeak_gz_fn)
    narrowPeak_bb = dxpy.upload_local_file(narrowPeak_bb_fn)
    gappedPeak_bb = dxpy.upload_local_file(gappedPeak_bb_fn)
    broadPeak_bb  = dxpy.upload_local_file(broadPeak_bb_fn)
    fc_signal     = dxpy.upload_local_file(fc_signal_fn)
    pvalue_signal = dxpy.upload_local_file(pvalue_signal_fn)

    # Build the output structure.

    output = {
        "narrowpeaks":    dxpy.dxlink(narrowPeak),
        "gappedpeaks":    dxpy.dxlink(gappedPeak),
        "broadpeaks":     dxpy.dxlink(broadPeak),
        "narrowpeaks_bb": dxpy.dxlink(narrowPeak_bb),
        "gappedpeaks_bb": dxpy.dxlink(gappedPeak_bb),
        "broadpeaks_bb":  dxpy.dxlink(broadPeak_bb),
        "fc_signal":     dxpy.dxlink(fc_signal),
        "pvalue_signal": dxpy.dxlink(pvalue_signal)
    }

    return output

dxpy.run()
