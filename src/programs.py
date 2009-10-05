import os.path
import re
import subprocess
from versioncontrol import get_repository

version_pattern = re.compile(r'(?P<version>\d\S*)\s')

class VersionedProgram(object):
    pass
    
        
class Executable(VersionedProgram): # call this Simulator? what about PyNEST?
    # store compilation/configuration options?

    def __init__(self, path, version=None):
        VersionedProgram.__init__(self)
        self.path = path or self._find_executable()    
        if not hasattr(self, 'name'):
            self.name = os.path.basename(path)
        self.version = version or self._get_version()

    def __str__(self):
        return "%s (version: %s) at %s" % (self.name, self.version, self.path)

    def _find_executable(self):
        found = []
        for path in os.getenv('PATH').split(':'):
            if os.path.exists(os.path.join(path, self.default_executable_name)):
                found += [path] 
        if not found:
            raise Exception('%s could not be found. Please supply the path to the %s executable.' % (self.name, self.default_executable_name))
        else:
            executable = os.path.join(found[0], self.default_executable_name) 
            if len(found) == 1:
                print 'Using', executable
            else:
                print 'Multiple versions found, using %s. If you wish to use a different version, please specify it explicitly' % executable
        return executable

    def _get_version(self):
        p = subprocess.Popen("%s --version" % self.path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        returncode = p.wait()
        match = version_pattern.search(p.stdout.read())
        if match:
            version = match.groupdict()['version']
        else:
            version = None
        return version


class NEURONSimulator(Executable):
    
    name = "NEURON"
    default_executable_name = "nrniv"
    

class PythonExecutable(Executable):
    
    name = "Python"
    default_executable_name = "python"
    
    @staticmethod
    def write_parameters(parameters, filename):
        parameters.save(filename)


class NESTSimulator(Executable):
    
    name = "NEST"
    default_executable_name = 'nest'
    

class Script(VersionedProgram): # call this SimulationCode?
    # note that a script need not be a single file, but could be a suite of files
    # generally, should define a VCS repository and a main file
    
    def __init__(self, repository_url=None, main_file=None):
    # store reference to the executable for which the script is destined?
        VersionedProgram.__init__(self)
        self.main_file = main_file
        self.repository = get_repository(repository_url)
        self.version = None
    
    def __str__(self):
        if self.repository:
            return "%s r%s (main file is %s)" % (self.repository, self.version, self.main_file)
        else:
            return "%s (no repository)" % self.main_file
    
    def checkout(self):
        if self.repository and not self.repository.working_copy:
            self.repository.checkout()
    
    def change_repository(self, repository_url):
        self.repository = get_repository(repository_url)
    
    def _get_current_version(self):
        return self.repository.working_copy.current_version()
    
    def has_changed(self):
        return self.repository.has_changed()
    
    def update_code(self):
        if self.version is None:
            self.version = self._get_current_version()
        self.repository.use_version(self.version)
    
registered_program_names = {}
registered_executables = {}
registered_extensions = {}
    
def register_executable(cls, name, executable, extensions):
    assert issubclass(cls, Executable)
    registered_program_names[name] = cls
    registered_executables[executable] = cls
    for ext in extensions:
        registered_extensions[ext] = cls
    
register_executable(NEURONSimulator, 'NEURON', 'nrniv', ('.hoc', '.oc'))
register_executable(PythonExecutable, 'Python', 'python', ('.py',))
register_executable(NESTSimulator, 'NEST', 'nest', ('.sli',))
    
def get_executable(path=None, script_file=None):
    """
    Given the path to an executable, determine what program it is, if possible.
    Given the name of a script file, try to infer the program that runs that
    script.
    Return an appropriate subclass of Executable
    """
    if path:
        prog_name = os.path.basename(path)
        if prog_name in registered_executables:
            program = registered_executables[prog_name](path)
        else:
            program = Executable(path)
    elif script_file:
        script_path, ext = os.path.splitext(script_file)
        if ext in registered_extensions:
            program = registered_extensions[ext](path)
        else:
            raise Exception("Extension not recognized.")
    else:
        raise Exception('Either path or script_file must be specified')
        
    return program