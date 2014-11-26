import os

import nipype.pipeline.engine as pe
import nipype.interfaces.ants as ants
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util
from nipype.interfaces.c3 import C3dAffineTool


def create_extract_mni_roi_workflow(name='extract_mni_roi_workflow',
                                    base_dir=None,):
    
    if base_dir == None:
        base_dir = os.path.expanduser('~/workflow_folders/')
    
    workflow = pe.Workflow(name=name,
                       base_dir=base_dir)
    
    inputspec_subjects = pe.Node(util.IdentityInterface(fields=['anatomical_t1_weighted',
                                                       'mat_epi2anat',
                                                       'composite_mni2anat',
                                                       'epi',
                                                       'mean_epi',]),
                        name='inputspec_subjects')

    inputspec_masks = pe.Node(util.IdentityInterface(fields=['mask']),
                        name='inputspec_masks')

    fast = pe.Node(fsl.FAST(), name='fast')

    workflow.connect(inputspec_subjects, 'anatomical_t1_weighted', fast, 'in_files')

    merge = pe.Node(util.Merge(2), name='mergexfm')
    workflow.connect(inputspec_subjects, 'composite_mni2anat', merge, 'in2')
    workflow.connect(inputspec_subjects, 'mat_epi2anat', merge, 'in1')

    apply_transform = pe.Node(ants.ApplyTransforms(),
                              name='apply_transform')
    apply_transform.inputs.invert_transform_flags = [True, False]
    workflow.connect(inputspec_masks, 'mask', apply_transform, 'input_image')
    workflow.connect(inputspec_subjects, 'mean_epi', apply_transform, 'reference_image')
    workflow.connect(merge, 'out', apply_transform, 'transforms')


    def get_weighted_mean(data, mask):
        import nibabel as nb
        import numpy as np
        import os
        
        data_image = nb.load(data)
        mask_image = nb.load(mask)
        
        data = data_image.get_data().astype(float)
        mask = mask_image.get_data().astype(float)
        
        mask = mask / mask.sum()
        weighted_mean = (data * mask[..., np.newaxis]).reshape((-1, data.shape[-1])).sum(0)
        
        fn = os.path.abspath('weighted_mean.txt')
        
        np.savetxt(fn, [weighted_mean])
        
        return fn

    extracter = pe.MapNode(util.Function(function=get_weighted_mean,
                                         input_names=['data', 'mask'],
                                         output_names=['weighted_mean']), 
                           iterfield=['data'],
                           name='extracter')
    workflow.connect(apply_transform, 'output_image', extracter, 'mask')
    workflow.connect(inputspec_subjects, 'epi', extracter, 'data')

    pick1 = lambda x: x[1]
    listify = lambda x: [x]
    apply_transform_gray_matter_mask = pe.Node(ants.ApplyTransforms(),
                              name='apply_transform_gray_matter_mask')
    apply_transform_gray_matter_mask.inputs.invert_transform_flags = [True]
    workflow.connect(fast, ('partial_volume_files', pick1), apply_transform_gray_matter_mask, 'input_image')
    workflow.connect(inputspec_subjects, 'mean_epi', apply_transform_gray_matter_mask, 'reference_image')
    workflow.connect(inputspec_subjects, ('mat_epi2anat', listify), apply_transform_gray_matter_mask, 'transforms')


    gray_matter_mask_conjoiner = pe.Node(fsl.MultiImageMaths(),
                               name='gray_matter_mask_conjoiner')
    gray_matter_mask_conjoiner.inputs.op_string = '-mul %s'
    workflow.connect(apply_transform_gray_matter_mask, 'output_image', gray_matter_mask_conjoiner, 'in_file')
    workflow.connect(apply_transform, 'output_image', gray_matter_mask_conjoiner, 'operand_files')

    extracter_gray_matter_conjunction = extracter.clone(name='extracter_gray_matter_conjunction')
    workflow.connect(gray_matter_mask_conjoiner, 'out_file', extracter_gray_matter_conjunction, 'mask')
    workflow.connect(inputspec_subjects, 'epi', extracter_gray_matter_conjunction, 'data')

    outputspec = pe.Node(util.IdentityInterface(fields=['roi_signal',
                                                        'roi_signal_only_gray_matter']), name='outputspec')

    workflow.connect(extracter, 'weighted_mean', outputspec, 'roi_signal')
    workflow.connect(extracter_gray_matter_conjunction, 'weighted_mean', outputspec, 'roi_signal_only_gray_matter')


    return workflow
