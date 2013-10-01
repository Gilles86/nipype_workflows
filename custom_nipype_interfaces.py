import os

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    CommandLineInputSpec,
    CommandLine,
    File,
    isdefined
)

from nipype.utils import filemanip
# miconv -resize "$NZ,$NY,$NX" $folder/fieldmap.nii.gz $folder/fieldmap.nii.gz

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
        return os.path.abspath(fn + '_resized' + ext)


