import os

import nipype.pipeline.engine as pe
import nipype.interfaces.ants as ants
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util
from nipype.interfaces.c3 import C3dAffineTool


def create_fsl_afni_reg(name='ants_fsl_registration',
                        base_dir=None,
                        quick=False):
    
    if base_dir == None:
        base_dir = os.path.expanduser('~/workflow_folders/')
    
    workflow = pe.Workflow(name=name,
                       base_dir=base_dir)
    
    inputspec = pe.Node(util.IdentityInterface(fields=['to_anat',
                                                       'to_target',
                                                       'mean_epi',
                                                       'anatomical',
                                                       'target']),
                        name='inputspec')
    
    inputspec.inputs.target = fsl.Info.standard_image('MNI152_T1_2mm_brain.nii.gz')
    inputspec.inputs.to_anat = []
    inputspec.inputs.to_target = []    
    
    fast = pe.Node(fsl.FAST(), name='fast')
    
    binarize = pe.Node(fsl.ImageMaths(op_string='-nan -thr 0.5 -bin'),
                       name='binarize')
    pickindex = lambda x, i: x[i]
    workflow.connect(fast, ('partial_volume_files', pickindex, 2),
                     binarize, 'in_file')

    workflow.connect(inputspec, 'anatomical', fast, 'in_files')
    
    mean2anat = pe.Node(fsl.FLIRT(), name='mean2anat')
    mean2anat.inputs.dof = 6
    workflow.connect(inputspec, 'mean_epi', mean2anat, 'in_file')
    workflow.connect(inputspec, 'anatomical', mean2anat, 'reference')


    mean2anatbbr = pe.Node(fsl.FLIRT(), name='mean2anatbbr')
    mean2anatbbr.inputs.dof = 6
    mean2anatbbr.inputs.cost = 'bbr'
    mean2anatbbr.inputs.schedule = os.path.join(os.getenv('FSLDIR'),
                                                'etc/flirtsch/bbr.sch')
    workflow.connect(inputspec, 'mean_epi', mean2anatbbr, 'in_file')
    workflow.connect(binarize, 'out_file', mean2anatbbr, 'wm_seg')
    workflow.connect(inputspec, 'anatomical', mean2anatbbr, 'reference')
    workflow.connect(mean2anat, 'out_matrix_file',
                     mean2anatbbr, 'in_matrix_file')
    
    reg = pe.Node(ants.Registration(), name='antsRegister')
    reg.inputs.output_transform_prefix = ""
    reg.inputs.transforms = ['Translation', 'Rigid', 'Affine', 'SyN']
    reg.inputs.transform_parameters = [(0.1,), (0.1,), (0.1,), (0.2, 3.0, 0.0)]
    
    if quick:
        reg.inputs.number_of_iterations = [[100, 100, 100]] * 3 + [[100, 20, 10]]        
    else:
        reg.inputs.number_of_iterations = ([[10000, 111110, 11110]]*3 +
                                                   [[100, 50, 30]])        
    
    
    reg.inputs.dimension = 3
    reg.inputs.write_composite_transform = True
    reg.inputs.collapse_output_transforms = False
    reg.inputs.metric = ['Mattes'] * 3 + [['Mattes', 'CC']]
    reg.inputs.metric_weight = [1] * 3 + [[0.5, 0.5]]
    reg.inputs.radius_or_number_of_bins = [32] * 3 + [[32, 4]]
    reg.inputs.sampling_strategy = ['Regular'] * 3 + [[None, None]]
    reg.inputs.sampling_percentage = [0.3] * 3 + [[None, None]]
    reg.inputs.convergence_threshold = [1.e-8] * 3 + [-0.01]
    reg.inputs.convergence_window_size = [20] * 3 + [5]
    reg.inputs.smoothing_sigmas = [[4, 2, 1]] * 3 + [[1, 0.5, 0]]
    reg.inputs.sigma_units = ['vox'] * 4
    reg.inputs.shrink_factors = [[6, 4, 2]] + [[3, 2, 1]]*2 + [[4, 2, 1]]
    reg.inputs.use_estimate_learning_rate_once = [True] * 4
    reg.inputs.use_histogram_matching = [False] * 3 + [True]
    reg.inputs.output_warped_image = 'output_warped_image.nii.gz'

    
    workflow.connect(inputspec, 'target', reg, 'fixed_image')
    workflow.connect(inputspec, 'mean_epi', reg, 'moving_image')
    
    fields_afni = reg.outputs.get().keys()
    
    outputspec = pe.Node(util.IdentityInterface(fields=fields_afni + ['transformed_anat_space',
                                                                 'transformed_target_space',
                                                                 'epi2anat_transform']),
                         name='outputspec')
    
    for field in fields_afni:
        workflow.connect(reg, field, outputspec, field)
    
    convert2itk = pe.Node(C3dAffineTool(),
                      name='convert2itk')
    convert2itk.inputs.fsl2ras = True
    convert2itk.inputs.itk_transform = True
    
    
    workflow.connect(mean2anatbbr, 'out_matrix_file', convert2itk, 'transform_file')
    workflow.connect(inputspec, 'mean_epi', convert2itk, 'source_file')    
    workflow.connect(inputspec, 'anatomical', convert2itk, 'reference_file')
    workflow.connect(convert2itk, 'itk_transform', outputspec, 'epi2anat_transform')
    
    pickfirst = lambda x: x[0]
    merge = pe.Node(util.Merge(2), name='mergexfm')
    workflow.connect(convert2itk, 'itk_transform', merge, 'in2')
    workflow.connect(reg, ('composite_transform', pickfirst), merge, 'in1')
    
    apply_epi2mni_transform = pe.MapNode(ants.ApplyTransforms(), 
                                         iterfield=['input_image'],
                                         name='apply_epi2mni_transform') 
    apply_epi2mni_transform.inputs.interpolation = 'BSpline'
    workflow.connect(inputspec, 'to_target', apply_epi2mni_transform, 'input_image')
    workflow.connect(inputspec, 'target', apply_epi2mni_transform, 'reference_image')
    workflow.connect(merge, 'out', apply_epi2mni_transform, 'transforms')
    
    apply_epi2anat_transform = pe.MapNode(ants.ApplyTransforms(), 
                                       iterfield=['input_image'],
                                       name='apply_epi2anat_transform')    
    workflow.connect(inputspec, 'to_anat', apply_epi2anat_transform, 'input_image')    
    workflow.connect(inputspec, 'anatomical', apply_epi2anat_transform, 'reference_image')
    workflow.connect(convert2itk, 'itk_transform', apply_epi2anat_transform, 'transforms')    
    apply_epi2anat_transform.inputs.interpolation = 'BSpline'
    
    workflow.connect(apply_epi2mni_transform, 'output_image', outputspec, 'transformed_target_space')
    workflow.connect(apply_epi2anat_transform, 'output_image', outputspec, 'transformed_anat_space')    

        
    return workflow
        
    
    
