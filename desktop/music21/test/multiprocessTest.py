# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         multiprocesssTest.py
# Purpose:      Controller for all tests in music21 run concurrently.
#
# Authors:      Michael Scott Cuthbert
#
# Copyright:    Copyright © 2012-13 Michael Scott Cuthbert and the music21 Project
# License:      LGPL, see license.txt
#-------------------------------------------------------------------------------

'''
Multiprocess testing.  Tests all doctests and Test unittest objects in all
modules that are imported when running "import music21".  Runs threads on
each core of a multicore system unless there are more than 2 cores, in which
case it runs on n-1 cores.

N.B. this gets a slightly different set of modules than test/test.py does
because the `imp` module is not available for threaded processing.  Running
both modules gives great coverage of just about everything -- do that before
building a new release.

Run test/testDocumentation after this.
'''
from __future__ import print_function

import doctest
import multiprocessing
import os
import sys
import time
import types
import unittest

import music21
from music21 import base
from music21 import environment
_MOD = 'multiprocessTest.py'
environLocal = environment.Environment(_MOD)


#-------------------------------------------------------------------------------
class ModuleGather(object):
    r'''
    Utility class for gathering and importing all modules in the music21
    package. Puts them in self.modulePaths.
    
    
    >>> from music21.test import testSingleCoreAll as testModule
    >>> mg = testModule.ModuleGather()
    >>> #_DOCS_SHOW print mg.modulePaths[0]
    D:\Web\eclipse\music21base\music21\xmlnode.py
    '''
    def __init__(self):
        self.dirParent = os.path.dirname(base.__file__)

        self.modulePaths = []
    
        self.moduleSkip = [
            'testSingleCoreAll.py', 
            'testExternal.py', 
            'testDefault.py', 
            'testInstallation.py', 
            'testLint.py', 
            'testPerformance.py',
            'multiprocessTest.py',
            'timeGraphs.py',
            'exceldiff.py', 
            'mrjobaws.py', # takes too long.
            'configure.py', # runs oddly...
            ]
        # skip any path that starts with this string
        self.pathSkip = ['abj', 'obsolete', 'ext', 'server', 'demos']
        # search on init
        self._walk()

    def _visitFunc(self, args, dirname, names):
        '''
        append all module paths from _walk() to self.modulePaths.
        Utility function called from os.path.walk()
        '''
        for fileName in names:
            if fileName.endswith('py'):
                fp = os.path.join(dirname, fileName)
                if not os.path.isdir(fp):
                    self.modulePaths.append(fp)

    def _walk(self):
        '''
        Get all the modules in reverse order, storing them in self.modulePaths
        '''
        # the results of this are stored in self.curFiles, self.dirList
        os.path.walk(self.dirParent, self._visitFunc, '')
        self.modulePaths.sort()
        self.modulePaths.reverse()

    def _getName(self, fp):
        r'''
        Given full file path, find a name for the module with : as the separator.
        
        >>> from music21.test import testSingleCoreAll as testModule
        >>> mg = testModule.ModuleGather()
        >>> #_DOCS_SHOW mg._getName(r'D:\Web\eclipse\music21base\music21\xmlnode.py')
        'xmlnode'
        '''
        fn = fp.replace(self.dirParent, '') # remove parent
        if fn.startswith(os.sep):
            fn = fn[1:]
        fn = fn.replace(os.sep, '_') # replace w/ colon
        fn = fn.replace('.py', '')
        return fn

    def _getNamePeriod(self, fp):
        r'''
        Given full file path, find a name for the module with . as the separator.
        
        >>> from music21.test import testSingleCoreAll as testModule
        >>> mg = testModule.ModuleGather()
        >>> #_DOCS_SHOW mg._getName(r'D:\Web\eclipse\music21base\music21\trecento\findSevs.py')
        'trecento.findSevs'
        '''
        fn = fp.replace(self.dirParent, '') # remove parent
        parts = [x for x in fn.split(os.sep) if x]
        if parts[-1] == '__init__.py':
            parts.pop()
        fn = '.'.join(parts) # replace w/ period
        fn = fn.replace('.py', '')

        return fn
     

    def getModuleWithoutImp(self, fp, restoreEnvironmentDefaults = False):
        '''
        gets one module object from the file path without using Imp
        '''
        print(fp)
        skip = False
        for fnSkip in self.moduleSkip:
            if fp.endswith(fnSkip):
                skip = True
                break
        if skip:
            return "skip"
        for dirSkip in self.pathSkip:
            dirSkipSlash = os.sep + dirSkip + os.sep
            if dirSkipSlash in fp:
                skip = True  
                break
        if skip:
            return "skip"
        moduleName = self._getNamePeriod(fp)
        moduleNames = moduleName.split('.')
        currentModule = music21
        for thisName in moduleNames:
            if hasattr(currentModule, thisName):
                currentModule = object.__getattribute__(currentModule, thisName)
                if not isinstance(currentModule, types.ModuleType):
                    return "notInTree"
            else:
                return "notInTree"
        mod = currentModule
        
        if restoreEnvironmentDefaults:
            if hasattr(mod, 'environLocal'):
                mod.environLocal.restoreDefaults()
        return mod



def multime(multinum):
    sleeptime = multinum[0]/1000.0
    if multinum[0] == 900:
        raise Exception("Ha! 900!") 
    print(multinum, sleeptime)
    sys.stdout.flush()
    time.sleep(sleeptime)
    x = multinum[0] * multinum[1] / 10
    return (x, multinum[0])

def examplePoolRunner(testGroup=['test'], restoreEnvironmentDefaults=False):
    '''
    demo of a pool runner with failures and successes...
    '''
    poolSize = 2 #multiprocessing.cpu_count()
    print('Creating %d processes for multiprocessing' % poolSize)
    pool = multiprocessing.Pool(processes=poolSize)

    storage = []
    
    numbers = [500, 200, 100, 50, 7000, 900]
    res = pool.imap_unordered(multime, ((i,10) for i in numbers))
    continueIt = True
    timeouts = 0
    eventsProcessed = 0
    while continueIt is True:
        try:
            newResult = res.next(timeout=1)
            print(newResult)
            timeouts = 0
            eventsProcessed += 1
            storage.append(newResult)
        except multiprocessing.TimeoutError:
            timeouts += 1
            print("TIMEOUT!")
            if timeouts > 3 and eventsProcessed > 0:
                print("Giving up...")
                continueIt = False
                pool.close()
                pool.join()
        except StopIteration:
            continueIt = False
            pool.close()    
            pool.join()
        except Exception as excp:
            exceptionLog = ("UntrappedException", "%s" % excp)
            storage.append(exceptionLog)

    storageTwo = [i[1] for i in storage]
    for x in numbers:
        if x not in storageTwo:
            failLog = ("Fail", x)
            storage.append(failLog)
    print(storage)

def runOneModuleWithoutImp(args):
    modGath = args[0] # modGather object
    fp = args[1]
    verbosity = False
    moduleObject = modGath.getModuleWithoutImp(fp)
    environLocal.printDebug('running %s \n' % fp)
    if moduleObject == 'skip':
        environLocal.printDebug('%s is skipped \n' % fp)
        return ("Skipped", fp)
    elif moduleObject == 'notInTree':
        environLocal.printDebug('%s is in the music21 directory but not imported in music21. Skipped -- fix! \n' % fp)
        return ("NotInTree", fp, '%s is in the music21 directory but not imported in music21. Skipped -- fix!' % modGath._getNamePeriod(fp))

    
    try:
        moduleName = modGath._getName(fp)
        globs = __import__('music21').__dict__.copy()
        docTestOptions = (doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE)
        s1 = doctest.DocTestSuite(
            globs=globs,
            optionflags=docTestOptions,
            )
        
        # get Test classes in moduleObject
        if not hasattr(moduleObject, 'Test'):
            environLocal.printDebug('%s has no Test class' % moduleObject)
        else:
            s1.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(moduleObject.Test))
        try:
            globs = __import__('music21').__dict__.copy()
            s3 = doctest.DocTestSuite(moduleObject,
                globs=globs,
                optionflags=docTestOptions,
                )
            s1.addTests(s3)
        except ValueError:
            environLocal.printDebug('%s cannot load Doctests' % moduleObject)
            pass        
        environLocal.printDebug('running Tests...\n')
        runner = unittest.TextTestRunner(verbosity=verbosity)
        try:
            testResult = runner.run(s1)  
            
            # need to make testResult pickleable by removing the instancemethod parts...
            trE = []
            for e in testResult.errors:
                trE.append(e[1])
            trF = []
            for f in testResult.failures:
                trF.append(f[1])
            testResult.errors = trE
            testResult.failures = trF
            return ("TestsRun", fp, moduleName, testResult)
        except Exception as excp:
            environLocal.printDebug('*** Exception in running %s: %s...\n' % (moduleName, excp))
            return ("TrappedException", fp, moduleName, str(excp))
    except Exception as excp:
        environLocal.printDebug('*** Large Exception in running %s: %s...\n' % (fp, excp))
        return ("LargeException", fp, str(excp))

    
def mainPoolRunner(testGroup=['test'], restoreEnvironmentDefaults=False, leaveOut = 1):
    '''
    Run all tests. Group can be test and external
    '''    
    
    timeStart = time.time()
    poolSize = multiprocessing.cpu_count()
    if poolSize > 2:
        poolSize = poolSize - leaveOut
    else:
        leaveOut = 0

    print('Creating %d processes for multiprocessing (omitting %d processors)' % (poolSize, leaveOut))
    

    modGather = ModuleGather()

    maxTimeout = 300
    pathsToRun = modGather.modulePaths

    pool = multiprocessing.Pool(processes=poolSize)
    res = pool.imap_unordered(runOneModuleWithoutImp, ((modGather,fp) for fp in pathsToRun))

    continueIt = True
    timeouts = 0
    eventsProcessed = 0
    summaryOutput = []
    
    while continueIt is True:
        try:
            newResult = res.next(timeout=1)
            if timeouts >= 5:
                print("")
            print(newResult)
            timeouts = 0
            eventsProcessed += 1
            summaryOutput.append(newResult)
        except multiprocessing.TimeoutError:
            timeouts += 1
            if timeouts == 5 and eventsProcessed > 0:
                print("Delay in processing, seconds: ", end="")
            elif timeouts == 5:
                print("Starting first modules, should take 5-10 seconds: ", end="")
            if timeouts % 5 == 0:
                print(str(timeouts) + " ", end="")
            if timeouts > maxTimeout and eventsProcessed > 0:
                print("\nToo many delays, giving up...")
                continueIt = False
                printSummary(summaryOutput, timeStart, pathsToRun)
                pool.close()
                exit()
        except StopIteration:
            continueIt = False
            pool.close()    
            pool.join()
        except Exception as excp:
            eventsProcessed += 1
            exceptionLog = ("UntrappedException", "%s" % excp)
            summaryOutput.append(exceptionLog)

    printSummary(summaryOutput, timeStart, pathsToRun)

def printSummary(summaryOutput, timeStart, pathsToRun):
    outStr = ""
    summaryOutputTwo = [i[1] for i in summaryOutput]
    for fp in pathsToRun:
        if fp not in summaryOutputTwo:
            failLog = ("NoResult", fp)
            summaryOutput.append(failLog)

    totalTests = 0

    skippedSummary = []
    successSummary = []
    errorsFoundSummary = []
    otherSummary = []
    for l in summaryOutput:
        (returnCode, fp) = (l[0], l[1])
        if returnCode == 'Skipped':
            skippedSummary.append("Skipped: %s" % fp)
        elif returnCode == 'NoResult':
            otherSummary.append("Silent test fail for %s: Run separately!" % fp)
        elif returnCode == 'UntrappedException':
            otherSummary.append("Untrapped Exception for unknown module: %s" % fp)
        elif returnCode == 'TrappedException':
            (moduleName, excp) = (l[2], l[3])
            otherSummary.append("Trapped Exception for module %s, at %s: %s" % (moduleName, fp, excp))
        elif returnCode == 'LargeException':
            excp = l[2]
            otherSummary.append("Large Exception for file %s: %s" % (fp, excp))
        elif returnCode == 'ImportError':
            otherSummary.append("Import Error for %s" % fp)
        elif returnCode == 'NotInTree':
            otherSummary.append("Not in Tree Error: %s " % l[2]) 
        elif returnCode == 'TestsRun':
            (moduleName, textTestResultObj) = (l[2], l[3])
            testsRun = textTestResultObj.testsRun
            totalTests += testsRun
            if textTestResultObj.wasSuccessful():
                successSummary.append("%s successfully ran %d tests" % (moduleName, testsRun))
            else:
                errorsList = textTestResultObj.errors # not the original errors list! see pickle note above
                failuresList = textTestResultObj.failures
                errorsFoundSummary.append("\n-----------\n%s had %d ERRORS and %d FAILURES in %d tests:" %(moduleName, len(errorsList), len(failuresList), testsRun))

                for e in errorsList:
                    outStr += e + "\n"
                    errorsFoundSummary.append('%s' % (e))
                for f in failuresList:
                    outStr += f + "\n"
                    errorsFoundSummary.append('%s' % (f))
#                for e in errorsList:
#                    print e[0], e[1]
#                    errorsFoundSummary.append('%s: %s' % (e[0], e[1]))
#                for f in failuresList:
#                    print f[0], f[1]
#                    errorsFoundSummary.append('%s: %s' % (f[0], f[1]))    
        else:
            otherSummary.append("Unknown return code %s" % l)


    outStr += "\n\n---------------SUMMARY---------------------------------------------------\n"
    for l in skippedSummary:
        outStr += l + "\n"
    for l in successSummary:
        outStr += l + "\n"
    for l in otherSummary:
        outStr += l + "\n"
    for l in errorsFoundSummary:
        outStr += l + "\n"
    outStr += "-------------------------------------------------------------------------\n"
    elapsedTime = time.time() - timeStart
    outStr += "Ran %d tests in %.4f seconds\n" % (totalTests, elapsedTime)
    sys.stdout.flush()
    print(outStr)
    sys.stdout.flush()
    
    from music21 import common
    import datetime
    with open(os.path.join(common.getSourceFilePath(), 'test', 'lastResults.txt'), 'w') as f:
        f.write(outStr)
        f.write("Run at " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == '__main__':
    #mg = ModuleGather()
    #mm = mg.getModuleWithoutImp('trecento.capua')
    #print mm
    mainPoolRunner()
