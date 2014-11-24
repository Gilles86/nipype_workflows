from nipype.utils import filemanip
# miconv -resize "$NZ,$NY,$NX" $folder/fieldmap.nii.gz $folder/fieldmap.nii.gz
from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    CommandLineInputSpec,
    CommandLine,
    File,
    isdefined
)
import os

class MiconvResizeInputSpec(CommandLineInputSpec):
    size = traits.Tuple(mandatory=True, argstr='%s', position=0)
    in_file = traits.File(exists=True, position=1, argstr='%s')
    out_file = traits.File(default='resized.nii.gz', argstr='%s', position=2, genfile=True)
    
class MiconvResizeOutputSpec(TraitedSpec):
    resized_file = traits.File(exists=True)
    
class MiconvResize(CommandLine):
    _cmd = 'miconv -resize'
    input_spec = MiconvResizeInputSpec
    output_spec = MiconvResizeOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['resized_file'] = os.path.abspath(self.inputs.out_file)
        return outputs      
    
    def _format_arg(self, name, spec, value):
        if name == 'size':
            return '"%s,%s,%s"' % value
        
        if name == 'in_file':
            return value

        return super(MiconvResize, self)._format_arg(name, spec, value)
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        if not isdefined(self.inputs.out_file):
            outputs['resized_file'] = self._gen_filename(self.inputs.in_file)
        else:
            outputs['resized_file'] = os.path.abspath(self.inputs.out_file)
        return outputs
    
    
    
    def _gen_filename(self, name):
        pth, fn, ext = filemanip.split_filename(self.inputs.in_file)
        return os.path.join(os.getcwd(), fn + '_resized' + ext)
        
        
        
from nipype.utils.filemanip import fname_presuffix

from nipype import config

config.set('execution', 'display_variable', os.environ['DISPLAY'])
print config.get('execution', 'display_variable')


class MP2RageSkullStripInputSpec(CommandLineInputSpec):
    in_filter_image = traits.File(mandatory=False, argstr='-inFilter %s', desc=' Filter Image')
    in_inv2 = traits.File(exists=True, argstr='-inInv2 %s', desc='Inv2 Image')
    in_t1 = traits.File(exists=True, argstr='-inT1 %s', desc='T1 Map image')
    in_t1_weighted = traits.File(exists=True, argstr='-inT1weighted %s', desc='T1-Weighted Image')
    out_brain_mask = traits.File('brain_mask.nii.gz', usedefault=True, argstr='-outBrain %s', desc='Path/name of brain mask')
    out_masked_t1 = traits.Bool(True, usedefault=True, argstr='-outMasked %s', desc='Create masked T1')    
    out_masked_t1_weighted = traits.Bool(True, usedefault=True, argstr='-outMasked2 %s', desc='Path/name of masked T1-weighted image')        
    out_masked_filter_image = traits.Bool(False, usedefault=True, argstr='-outMasked3 %s', desc='Path/name of masked Filter image')    

class MP2RageSkullStripOutputSpec(TraitedSpec):
    brain_mask = traits.File()
    masked_t1 = traits.File()
    masked_t1_weighted = traits.File()
    masked_filter_image = traits.File()    


class MP2RageSkullStrip(CommandLine):
#    _cmd = '$MIPAV_JAVA_BIN -Djava.awt.headless=true -classpath ' + os.environ['MIPAV_PATH'] + ' edu.jhu.ece.iacl.jist.cli.run de.mpg.cbs.jist.brain.JistBrainMp2rageSkullStripping'
    _cmd = 'xvfb-run --auto-servernum ' + os.environ['MIPAV_JAVA_BIN'] + ' -classpath $MIPAV_PATH edu.jhu.ece.iacl.jist.cli.run de.mpg.cbs.jist.brain.JistBrainMp2rageSkullStripping'
#    _cmd = os.environ['MIPAV_JAVA_BIN'] + ' -classpath $MIPAV_PATH -headless edu.jhu.ece.iacl.jist.cli.run de.mpg.cbs.jist.brain.JistBrainMp2rageSkullStripping'
    input_spec = MP2RageSkullStripInputSpec
    output_spec = MP2RageSkullStripOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs['resized_file'] = os.path.abspath(self.inputs.out_file)
        return outputs      



    def _format_arg(self, name, spec, value):
        if name == 'out_brain_mask':
            return '-outBrain %s' % self._gen_filename(self.inputs.in_t1, suffix='_brain_mask')

        if name == 'out_masked_t1':
            return '-outMasked %s' % self._gen_filename(self.inputs.in_t1, suffix='_brain_stripped')        

        if name == 'out_masked_t1_weighted':
            return '-outMasked2 %s' % self._gen_filename(self.inputs.in_t1_weighted, suffix='_brain_stripped')

        if name == 'out_masked_filter_image':
            if self.inputs.in_filter_image:
                return '-outMasked3 %s' % self._gen_filename(self.inputs.in_filter_image, suffix='_brain_stripped')        
            else:
                return ''

        return super(MP2RageSkullStrip, self)._format_arg(name, spec, value)

    def _list_outputs(self):
        outputs = self._outputs().get()        
        outputs['brain_mask'] = self._gen_filename(self.inputs.in_t1, suffix='_brain_mask')
        outputs['masked_t1'] = self._gen_filename(self.inputs.in_t1, suffix='_brain_stripped')
        outputs['masked_t1_weighted'] = self._gen_filename(self.inputs.in_t1_weighted, suffix='_brain_stripped') 

        if isdefined(self.inputs.in_filter_image):
            outputs['masked_filter_image'] = self._gen_filename(self.inputs.in_filter_image, suffix='_brain_stripped')         


        return outputs


    def _gen_filename(self, basename, cwd=None, suffix=None, change_ext=True,
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
            ext = '.nii.gz'
        if suffix is None:
            suffix = ''
        if change_ext:
            print suffix, ext
            if suffix:
                suffix = ''.join((suffix, ext))
            else:
                suffix = ext

        fname = fname_presuffix(basename, suffix=suffix,
                                use_ext=False, newpath=cwd)
        return fname