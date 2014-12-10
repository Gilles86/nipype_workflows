import os

import nipype.pipeline.engine as pe
import nipype.interfaces.ants as ants
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util

from . import FDR

def create_fdr_threshold_workflow(name='fdr_threshold'):
    
    workflow = pe.Workflow(name=name)
    
    inputspec = pe.Node(util.IdentityInterface(fields=['p_values',
                                               'z_stats',
                                               'mask',
                                               'q']), 'inputspec')

    inputspec.inputs.q = 0.05

    fdr = pe.MapNode(FDR(), iterfield=['p_values'], name='fdr')

    workflow.connect(inputspec, 'p_values', fdr, 'p_values')
    workflow.connect(inputspec, 'mask', fdr, 'mask')

    thresholder = pe.MapNode(fsl.Threshold(), iterfield=['in_file'], name='thresholder')
    thresholder.inputs.direction = 'above'
    workflow.connect(inputspec, 'q', thresholder, 'thresh')
    workflow.connect(fdr, 'adjusted_p_values', thresholder, 'in_file')

    masker = pe.MapNode(fsl.ApplyMask(), iterfield=['in_file', 'mask_file'], name='masker')
    workflow.connect(thresholder, 'out_file', masker, 'mask_file')
    workflow.connect(inputspec, 'z_stats', masker, 'in_file')

    outputspec = pe.Node(util.IdentityInterface(fields=['thresholded_z_stats',
        'adjusted_p_values']), name='outputspec')

    workflow.connect(masker, 'out_file', outputspec, 'thresholded_z_stats')
    workflow.connect(fdr, 'adjusted_p_values', outputspec, 'adjusted_p_values')

    return workflow
    
    
