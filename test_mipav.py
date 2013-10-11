from nipype.pipeline import engine as pe
from nipype.interfaces import fsl
from nipype.interfaces import io as nio
import os
from IPython.display import Image

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    CommandLineInputSpec,
    CommandLine,
    File,
    isdefined
)
from nipype.utils.filemanip import fname_presuffix

                        
class MP2RageSkullStripInputSpec(CommandLineInputSpec):
    in_filter_image = traits.File(mandatory=False, argstr='-inFilter %s', desc=' Filter Image')
    in_inv2 = traits.File(exists=True, argstr='-inInv2 %s', desc='Inv2 Image')
    in_t1 = traits.File(exists=True, argstr='-inT1 %s', desc='T1 Map image')
    int_t1_weighted = traits.File(exists=True, argstr='-inT1weighted %s', desc='T1-Weighted Image')
    out_brain_mask = traits.File(argstr='-outBrain %s', desc='Path/name of brain mask')
    out_masked_t1 = traits.Bool(argstr='-outMasked %s', desc='Create masked T1')    
    out_masked_t1_weighted = traits.Bool(argstr='-outMasked2 %s', desc='Path/name of masked T1-weighted image')        
    out_masked_filter_image = traits.Bool(argstr='-outMasked3 %s', desc='Path/name of masked Filter image')    
    
class MP2RageSkullStripOutputSpec(TraitedSpec):
    brain_mask = traits.File()
    masked_t1 = traits.File()
    masked_t1_weighted = traits.File()
    masked_filter_image = traits.File()    
    
    
class MP2RageSkullStrip(CommandLine):
    _cmd = os.environ['MIPAV_JAVA_BIN'] + ' -classpath ' + os.environ['MIPAV_PATH'] + ' edu.jhu.ece.iacl.jist.cli.run de.mpg.cbs.jist.brain.JistBrainMp2rageSkullStripping'
    input_spec = MP2RageSkullStripInputSpec
    output_spec = MP2RageSkullStripOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['resized_file'] = os.path.abspath(self.inputs.out_file)
        return outputs      
    
    def _format_arg(self, name, spec, value):
        if name == 'out_brain_mask':
            if not isdefined(self.inputs.out_brain_mask):
                return self._gen_filename(self.inputs.in_t1, suffix='_brain_mask')
            else:
                return self.inputs.out_brain_mask
        
        if name == 'out_masked_t1':
            print 'ja'
            return self._gen_filename(self.inputs.in_t1, suffix='_brain_stripped')        
        
        if name == 'out_masked_t1_weighted':
            return self._gen_filename(self.inputs.in_t1_weighted, suffix='_brain_stripped')
        
        if name == 'out_masked_filter_image':
            return self._gen_filename(self.inputs.in_filter_image, suffix='_brain_stripped')        

        return super(MP2RageSkullStrip, self)._format_arg(name, spec, value)
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        
        if not isdefined(self.inputs.out_brain_mask):
            outputs['out_brain_mask'] = self._gen_filename(self.inputs.in_t1, suffix='_brain_mask')
        else:
            return self.inputs.out_brain_mask
        
        if isdefined(self.inputs.out_masked_t1):
            outputs['resized_file'] = self._gen_filename(self.inputs.in_t1, suffix='_brain_stripped')

        if isdefined(self.inputs.out_masked_t1_weighted):
            outputs['out_masked_t1_weighted'] = self._gen_filename(self.inputs.in_t1_weighted, suffix='_brain_stripped') 
        
        if isdefined(self.inputs.out_masked_filter_image):
            outputs['out_masked_filter_image'] = self._gen_filename(self.inputs.in_filter_image, suffix='_brain_stripped')         
                
        
        return outputs
    
    
    def _gen_fname(self, basename, cwd=None, suffix=None, change_ext=True,
                   ext=None):
        """Generate a filename based on the given parameters.

        The filename will take the form: cwd/basename<suffix><ext>.
        If change_ext is True, it will use the extentions specified in
        <instance>intputs.output_type.

        Parameters
        ----------
        basename : str
            Filename to base the new filename on.
        cwd : str
            Path to prefix to the new filename. (default is os.getcwd())
        suffix : str
            Suffix to add to the `basename`.  (defaults is '' )
        change_ext : bool
            Flag to change the filename extension to the FSL output type.
            (default True)

        Returns
        -------
        fname : str
            New filename based on given parameters.

        """

        if basename == '':
            msg = 'Unable to generate filename for command %s. ' % self.cmd
            msg += 'basename is not set!'
            raise ValueError(msg)
        if cwd is None:
            cwd = os.getcwd()
        if ext is None:
            ext = Info.output_type_to_ext(self.inputs.output_type)
        if change_ext:
            if suffix:
                suffix = ''.join((suffix, ext))
            else:
                suffix = ext
        if suffix is None:
            suffix = ''
        fname = fname_presuffix(basename, suffix=suffix,
                                use_ext=False, newpath=cwd)
        return fname


mprage = MP2RageSkullStrip()

mprage.inputs.in_t1 = '/home/gdholla1/data/leipzig_data/unwarp_tests/BI3T130926/S4_mp2rage_whole_brain_T1_Images.nii'
mprage.inputs.int_t1_weighted = '/home/gdholla1/data/leipzig_data/unwarp_tests/BI3T130926/S5_mp2rage_whole_brain_UNI_Images.nii'
mprage.inputs.in_inv2 = '/home/gdholla1/data/leipzig_data/unwarp_tests/BI3T130926/S6_mp2rage_whole_brain_INV2.nii'

mprage.run()