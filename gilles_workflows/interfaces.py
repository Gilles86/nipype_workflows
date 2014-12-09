from nipype.utils import filemanip
# !fdr -i /Users/Gilles/workflow_folders/modelfit_GE/ztop/mapflow/_ztop0/zstat1_pval.nii.gz -m /Users/Gilles/Dropbox/Science/t2_optimizing/datasink/mask/_func_..Users..Gilles..Dropbox..Science..t2_optimizing..analysis..GE_2std.nii/_dilatemask0/GE_2std_dtype_mcf_bet_thresh_dil.nii.gz -q 0.05
from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    CommandLineInputSpec,
    CommandLine,
    File,
    isdefined
)
import os

from nipype.interfaces.fsl.base import FSLCommand, FSLCommandInputSpec

class FDRInputSpec(FSLCommandInputSpec):
    p_values = traits.File(exists=True, mandatory=True, position=0, argstr='-i %s', genfile=True, desc='image of p-values')
    mask = traits.File(exists=True, mandatory=True, position=1, argstr='-m %s', desc='mask')
    q = traits.Tuple(mandatory=False, argstr='-q %s', position=2, desc='threshold')
    adjusted_p_values = traits.File(mandatory=False, argstr='-a %s', position=-1, desc='FDR-adjusted p-value image', genfile=True,)
    
    
class FDROutputSpec(TraitedSpec):
    adjusted_p_values = traits.File()
    
class FDR(FSLCommand):
    _cmd = 'fdr'
    input_spec = FDRInputSpec
    output_spec = FDROutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['adjusted_p_values'] = self._gen_outfilename()
        return outputs
    
    def _gen_outfilename(self):
        out_file = self.inputs.adjusted_p_values
        if not isdefined(out_file):
            out_file = self._gen_fname(self.inputs.p_values,
                                       suffix='_adjusted')
        return os.path.abspath(out_file)
    
    def _gen_filename(self, name):
        if name == 'adjusted_p_values':
            return self._gen_outfilename()
        return None
