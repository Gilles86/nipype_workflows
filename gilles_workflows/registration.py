import os

import nipype.pipeline.engine as pe
import nipype.interfaces.ants as ants
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util
from nipype.interfaces.c3 import C3dAffineTool


def create_fsl_ants_registration_workflow(name='fsl_ants_registration_workflow',
                        base_dir=None,
                        quick=False):
    
    if base_dir == None:
        base_dir = os.path.expanduser('~/workflow_folders/')
    
    workflow = pe.Workflow(name=name,
                       base_dir=base_dir)
    
    inputspec = pe.Node(util.IdentityInterface(fields=['mean_epi',
                                                       'anatomical_t1_weighted',
                                                       'anatomical_mp2rage',
                                                       'target',
                                                       'to_target']),
                        name='inputspec')
    
    inputspec.inputs.target = fsl.Info.standard_image('MNI152_T1_2mm_brain.nii.gz')
    inputspec.inputs.to_target = []    
    
    fast = pe.Node(fsl.FAST(), name='fast')
    
    binarize = pe.Node(fsl.ImageMaths(op_string='-nan -thr 0.5 -bin'),
                       name='binarize')
    pickindex = lambda x, i: x[i]
    workflow.connect(fast, ('partial_volume_files', pickindex, 2),
                     binarize, 'in_file')

    workflow.connect(inputspec, 'anatomical_t1_weighted', fast, 'in_files')
    
    mean2anat = pe.Node(fsl.FLIRT(), name='mean2anat')
    mean2anat.inputs.dof = 6
    workflow.connect(inputspec, 'mean_epi', mean2anat, 'in_file')
    workflow.connect(inputspec, 'anatomical_mp2rage', mean2anat, 'reference')


    mean2anatbbr = pe.Node(fsl.FLIRT(), name='mean2anatbbr')
    mean2anatbbr.inputs.dof = 6
    mean2anatbbr.inputs.cost = 'bbr'
    mean2anatbbr.inputs.schedule = os.path.join(os.getenv('FSLDIR'),
                                                'etc/flirtsch/bbr.sch')
    workflow.connect(inputspec, 'mean_epi', mean2anatbbr, 'in_file')
    workflow.connect(binarize, 'out_file', mean2anatbbr, 'wm_seg')
    workflow.connect(inputspec, 'anatomical_mp2rage', mean2anatbbr, 'reference')
    workflow.connect(mean2anat, 'out_matrix_file',
                     mean2anatbbr, 'in_matrix_file')
    

    reg = pe.Node(ants.Registration(), name='antsRegister')
    reg.inputs.transforms = ['Rigid', 'Affine', 'SyN']
    reg.inputs.transform_parameters = [(0.1,), (0.1,), (0.1, 3.0, 0.0)]
    reg.inputs.number_of_iterations = [[1000,500,250,100]]*2 + [[100,100,70,20]]
    reg.inputs.dimension = 3
    reg.inputs.write_composite_transform = True
    reg.inputs.collapse_output_transforms = True
    reg.inputs.metric = ['MI']*2 + ['CC']
    reg.inputs.metric_weight = [1]*3 # Default (value ignored currently by ANTs)
    reg.inputs.radius_or_number_of_bins = [32]*2 + [4]
    reg.inputs.sampling_strategy = ['Regular']*2 + [None]
    reg.inputs.sampling_percentage = [0.25]*2 + [None]
    reg.inputs.convergence_threshold = [1.e-8]*2 + [1e-9]
    reg.inputs.convergence_window_size = [10]*2 + [15]
    reg.inputs.smoothing_sigmas = [[3,2,1,0]]*3
    reg.inputs.sigma_units = ['mm']*3
    reg.inputs.shrink_factors = [[8,4,2,1]]*2 + [[6,4,2,1]]
    reg.inputs.use_estimate_learning_rate_once = [True, True, True]
    reg.inputs.use_histogram_matching = [False]*2 + [True] # This is the default
    reg.inputs.initial_moving_transform_com = True
    reg.inputs.output_warped_image = True
    reg.inputs.winsorize_lower_quantile = 0.01
    reg.inputs.winsorize_upper_quantile = 0.99
    
    if quick:
        reg.inputs.number_of_iterations = [[100,50,25,10]]*2 + [[10,10,7,2]]        
    else:
        reg.inputs.number_of_iterations = [[1000,500,250,100]]*2 + [[100,100,70,20]]
        
    
    
    
    workflow.connect(inputspec, 'target', reg, 'fixed_image')
    workflow.connect(inputspec, 'anatomical_mp2rage', reg, 'moving_image')
    
    fields_ants = reg.outputs.get().keys()
    
    outputspec = pe.Node(util.IdentityInterface(fields=fields_ants + ['transformed_anat_space',
                                                                 'transformed_target_space',
                                                                 'epi2anat_transform',
                                                                      'epi_in_anat_space']),
                         name='outputspec')
    
    for field in fields_ants:
        workflow.connect(reg, field, outputspec, field)
    
    convert2itk = pe.Node(C3dAffineTool(),
                      name='convert2itk')
    convert2itk.inputs.fsl2ras = True
    convert2itk.inputs.itk_transform = True
    
    
    workflow.connect(mean2anatbbr, 'out_matrix_file', convert2itk, 'transform_file')
    workflow.connect(mean2anatbbr, 'out_file', outputspec, 'epi_in_anat_space')
    workflow.connect(inputspec, 'mean_epi', convert2itk, 'source_file')    
    workflow.connect(inputspec, 'anatomical_mp2rage', convert2itk, 'reference_file')
    workflow.connect(convert2itk, 'itk_transform', outputspec, 'epi2anat_transform')
    
    merge = pe.Node(util.Merge(2), name='mergexfm')
    workflow.connect(convert2itk, 'itk_transform', merge, 'in1')
    workflow.connect(reg, 'composite_transform', merge, 'in2')


    mni_applier = pe.MapNode(ants.ApplyTransforms(), iterfield=['input_image'], name='mni_applier')

    workflow.connect(inputspec, 'target', mni_applier, 'reference_image')
    workflow.connect(merge, 'out', mni_applier, 'transforms')
    workflow.connect(inputspec, 'to_target', mni_applier, 'input_image')
    workflow.connect(mni_applier, 'output_image', outputspec, 'transformed_target_space')

    
    return workflow
        
    
    
