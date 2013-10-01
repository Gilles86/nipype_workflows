from nipype.pipeline import engine as pe
from nipype.interfaces import fsl
from nipype.interfaces import io as nio
from custom_nipype_interfaces import MiconvResize
import os

ECHO_SPACING = 0.00105
DELTA_TE = 0.00102
SMOOTH_3D = 2.5
N_PROCESSORS = 4

workflow = pe.Workflow(name='register_and_unwarp_leipzig_data')

workflow.base_dir = os.path.abspath('/home/gdholla1/workflow_folders/')

dg = pe.Node(nio.DataGrabber(infields=['subject_id'], outfields=['fieldmap_scanner', 'magnitude_fieldmap', 'epi_slab'], sort_filelist=True), name='datagrabber')
dg.inputs.base_directory = '/home/public/Leipzig_sep_2013/'
dg.inputs.template = '*'
dg.inputs.field_template = dict(fieldmap_scanner='%s*/S*_cor_fieldmap_Te7.02.nii',
                                magnitude_fieldmap='%s*/S*_cor_fieldmap_Te6.nii',
                                epi_slab='%s*/S*_cor_34sli_TE23_0p83_1p0sl.nii')
dg.inputs.template_args = dict(fieldmap_scanner=[['subject_id']],
                               magnitude_fieldmap=[['subject_id']],
                               epi_slab=[['subject_id']])

dg.inputs.subject_id = 'BI3T'


# returns the first three dimensions of nifti-file IN REVERSE ORDER (because of way Miconv handles things)
def get_dims(in_file):
    import nibabel as nb
    
    if type(in_file) == list:
        in_file = in_file[0]
    
    return nb.load(in_file).get_shape()[:3][::-1]


motion_correct = pe.MapNode(fsl.MCFLIRT(), name='motion_correct', iterfield=['in_file'])

# fslmaths $folder/$fieldmap_scanner -div 4096 -mul 3.14159 -div $DELTA_TE $folder/fieldmap.nii.gz -odt float
DELTA_TE = 0.00102
normalizer = pe.Node(fsl.maths.MathsCommand(), name='normalizer')
normalizer.inputs.args = '-div 4096 -mul 3.14159 -div %s' % DELTA_TE
normalizer.inputs.out_file = 'fieldmap.nii.gz'
normalizer.inputs.output_datatype = 'float'

# bet $folder/$Magnitude_fieldmap $folder/mag1_brain -m -f 0.5 -g 0
better = pe.Node(fsl.BET(), name='brain_extracter')
better.inputs.mask = True
better.inputs.frac = 0.5
better.inputs.vertical_gradient = 0.


#miconv -resize "$NZ,$NY,$NX" $folder/fieldmap.nii.gz $folder/fieldmap.nii.gz
#miconv -resize "$NZ,$NY,$NX" $folder/mag1_brain_mask.nii.gz $folder/mag1_brain_mask.nii.gz
#miconv -resize "$NZ,$NY,$NX" $folder/$Magnitude_fieldmap $folder/mag_fieldmap_resampled.nii.gz

resize_fieldmap = pe.Node(MiconvResize(), name='resize_fieldmap')
resize_brain_mask = pe.Node(MiconvResize(), name='resize_brain_mask')
resize_magnitude_fieldmap = pe.Node(MiconvResize(), name='resize_magnitude_fieldmap')

## options fuer glattere Fieldmap: --despike ; --smooth3=sigma[mm] ; check with --savefmap=fieldmap_new 
#fugue -i $folder/mcf_$EPI_IMAGE --dwell=$echospacing --mask=$folder/mag1_brain_mask.nii.gz --loadfmap=$folder/fieldmap.nii.gz --smooth3=2.5 --unwarpdir=x -u $folder/result_mcf 
#fugue -i $folder/$EPI_IMAGE --dwell=$echospacing --mask=$folder/mag1_brain_mask.nii.gz --loadfmap=$folder/fieldmap.nii.gz --smooth3=2.5 --unwarpdir=x -u $folder/result

field_corrector_original = pe.MapNode(fsl.FUGUE(), name='field_corrector_original', iterfield=['in_file'])
field_corrector_mc = pe.MapNode(fsl.FUGUE(), name='field_corrector_mc', iterfield=['in_file'])

field_corrector_original.inputs.smooth3d = SMOOTH_3D
field_corrector_original.inputs.dwell_time = ECHO_SPACING
field_corrector_original.inputs.unwarp_direction = 'x'

field_corrector_mc.inputs.smooth3d = SMOOTH_3D
field_corrector_mc.inputs.dwell_time = ECHO_SPACING
field_corrector_mc.inputs.unwarp_direction = 'x'


workflow.connect(dg, 'epi_slab', motion_correct, 'in_file')
workflow.connect(dg, 'fieldmap_scanner', normalizer, 'in_file')
workflow.connect(dg, 'magnitude_fieldmap', better, 'in_file')

workflow.connect(normalizer, 'out_file', resize_fieldmap, 'in_file')
workflow.connect(better, 'mask_file', resize_brain_mask, 'in_file')
workflow.connect(dg, 'magnitude_fieldmap', resize_magnitude_fieldmap, 'in_file')

workflow.connect(dg, ('epi_slab', get_dims), resize_fieldmap, 'size')
workflow.connect(dg, ('epi_slab', get_dims), resize_brain_mask, 'size')
workflow.connect(dg, ('epi_slab', get_dims), resize_magnitude_fieldmap, 'size')

workflow.connect(dg, 'epi_slab', field_corrector_original, 'in_file')
workflow.connect(motion_correct, 'out_file', field_corrector_mc, 'in_file')

workflow.connect(resize_brain_mask, 'resized_file', field_corrector_original, 'mask_file')
workflow.connect(resize_brain_mask, 'resized_file', field_corrector_mc, 'mask_file')


workflow.connect(resize_fieldmap, 'resized_file', field_corrector_original, 'fmap_in_file')
workflow.connect(resize_fieldmap, 'resized_file', field_corrector_mc, 'fmap_in_file')

workflow.write_graph()
workflow.run(plugin='MultiProc', plugin_args={'n_procs' : N_PROCESSORS})