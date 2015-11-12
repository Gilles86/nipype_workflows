import os
from . import FDR

import nipype.pipeline.engine as pe
import nipype.interfaces.ants as ants
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util

from gilles_workflows import create_fdr_threshold_workflow
from nipype.workflows.fmri.fsl import create_modelfit_workflow, create_fixed_effects_flow

from nipype.algorithms.modelgen import SpecifyModel

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
    
    
def create_modelfit_workflow_bfsl(name='modelfit_workflow_bfsl'):
    
    
    inputspec = pe.Node(util.IdentityInterface(fields=['functional_runs',
                                                        'bases', 
                                                       'bfsl_files',
                                                       'contrasts', 
                                                       'interscan_interval', 
                                                       'film_threshold', 
                                                        'model_serial_correlations',
                                                        'highpass_filter',
                                                        'mask',
                                                        'realignment_parameters'],),
                                              name='inputspec')
    
    workflow = pe.Workflow(name=name)

        
    

    modelfit_workflow = create_modelfit_workflow()                      
                        
    inputspec.inputs.bases = {'dgamma': {'derivs': True}}
    inputspec.inputs.film_threshold = 1000
    inputspec.inputs.interscan_interval = 2.0
    inputspec.inputs.model_serial_correlations = True
    inputspec.inputs.highpass_filter = 128
    
    

    for field in ['bases', 'contrasts', 'film_threshold', 'interscan_interval', 'model_serial_correlations']:
        workflow.connect(inputspec, field, modelfit_workflow, 'inputspec.%s' % field)


    from nipype.algorithms.modelgen import SpecifyModel
    from nipype.interfaces import fsl

    specifymodel = pe.Node(SpecifyModel(), name='specifymodel')
    specifymodel.inputs.input_units = 'secs'
    
    def get_highpas_filter_cutoff(hz, tr):
        return float(hz) / (tr * 2)
    
    get_highpas_filter_cutoff_node = pe.Node(util.Function(function=get_highpas_filter_cutoff,
                                                           input_names=['hz', 'tr'],
                                                           output_names='cutoff'),
                                            name='get_highpas_filter_cutoff_node')
    
    workflow.connect(inputspec, 'interscan_interval', get_highpas_filter_cutoff_node, 'tr')
    workflow.connect(inputspec, 'highpass_filter', get_highpas_filter_cutoff_node, 'hz')    
    workflow.connect(get_highpas_filter_cutoff_node, 'cutoff', specifymodel, 'high_pass_filter_cutoff')
    
    workflow.connect(inputspec, 'interscan_interval', specifymodel, 'time_repetition')    
    workflow.connect(inputspec, 'bfsl_files', specifymodel, 'event_files')
    workflow.connect(inputspec, 'functional_runs', specifymodel, 'functional_runs')
    workflow.connect(inputspec, 'realignment_parameters', specifymodel, 'realignment_parameters')    
    
    workflow.connect(specifymodel, 'session_info', modelfit_workflow, 'inputspec.session_info')
    workflow.connect(inputspec, 'functional_runs', modelfit_workflow, 'inputspec.functional_data')


    fixedfx = create_fixed_effects_flow()

    workflow.connect(inputspec, 'mask', fixedfx, 'flameo.mask_file')

    def num_copes(files):
        return len(files)

    def transpose_copes(copes):    
        import numpy as np
        return np.array(copes).T.tolist()

    workflow.connect([(modelfit_workflow, fixedfx,
                       [(('outputspec.copes', transpose_copes), 'inputspec.copes'),
                        (('outputspec.varcopes', transpose_copes), 'inputspec.varcopes'),
                        ('outputspec.dof_file', 'inputspec.dof_files'),
                        (('outputspec.copes', num_copes), 'l2model.num_copes')])])


    ztopval = pe.MapNode(interface=fsl.ImageMaths(op_string='-ztop',
                                                  suffix='_pval'),
                         nested=True,
                         iterfield=['in_file'],
                         name='ztop',)

    fdr_workflow = create_fdr_threshold_workflow()

    workflow.connect([
                      (fixedfx, ztopval,
                       [('outputspec.zstats', 'in_file'),]),
                      (fixedfx, fdr_workflow,
                       [('outputspec.zstats', 'inputspec.z_stats'),]),
                      (ztopval, fdr_workflow,
                       [('out_file', 'inputspec.p_values'),]),
                      (inputspec, fdr_workflow,
                       [('mask', 'inputspec.mask'),]),
                      ])

    outputpsec = pe.Node(util.IdentityInterface(fields=['zstats', 'level2_copes', 'level2_varcopes', 'level2_tdof', 'thresholded_zstats']), name='outputspec')


    workflow.connect(fixedfx, 'outputspec.zstats', outputpsec, 'zstats')
    workflow.connect(fixedfx, 'outputspec.copes', outputpsec, 'level2_copes')
    workflow.connect(fixedfx, 'outputspec.varcopes', outputpsec, 'level2_varcopes')
    workflow.connect(fixedfx, 'flameo.tdof', outputpsec, 'level2_tdof')
    workflow.connect(fdr_workflow, 'outputspec.thresholded_z_stats', outputpsec, 'thresholded_z_stats')

    
    return workflow

