# Test suite
import unittest

testStrings = {
    'Key signatures' : '+-------~34F F F,_-- F F F,+_= F F F,',
    'Time signatures' : '_~44D D D D,~68d d d d d d,~128D,~1216,~816.',
    'Chords' : {
        'eighth': ', adg sfh dgj fhq etu, zcb 680 zh0, sd dfg asdfghj,',
        'quarter': ', ADG SFH DGJ FHQ ETU,'
        },
    'Rests' : ', f G H~ J~~, ] } ]] }~ }~~.',
    'Note-length modifiers' : ', a a~ a~~, A A~ A~~, D D< D~< D~~<.',
    'Accidentals' : ', a a- a--, g g= g==, f- f= f-=.',
    'Articulations' : ', A\' A\'\' A\" A\"\", E\' E\'\' E\" E\"\",',
    'Repetition markings' : {
        'simple' : ', A A A A; A A A A, A A A A: A A A A.',
        'endings' : {
            '1' : ', A A A A; A A A A,o A A A A o`,oo A A A A o`:',
            '2' : ', A A A A; A A A Ao, A A A A o`oo, A A A A o`:',
            '3' : ', A A A A; A A A Ao, A A A A oo, A A A A :'
            },
        },
    'Coda & segno' : {
        'simple' : ', A A A Ai, A A A AI, A A A A.',
        'references' : ', D Dk, D DK, D Dki , D DkI , D DKi , D DKI ;I  ,i  :'
        },
    'Dynamics' : r', g\, g\\, g\\\, g|, g||, g|||, g\|, g|\, g\\\|, g||\, g\\|',
    'Expressions' : ', d[ d[[ d[[[ d[[[[ g, d[[[[[ d d, d[[[[[[ d d d, d[`, d{ d{`.',
    'Beams' : ', d f.., df f.., d dg.., j q.., f`h` f`.. f g.. d f..,',
    'Grand staff' : {
        'simple' : {
            '1' : r',+ D F G D,' + '\n' + r',\\_ D F G D,' + '\\',
            '2' : r',+~44F G H J, D F G H,' + '\n' + r',\\_~44F D Q J,\ H J H H,' + '\\'
            },
        'muliple parts' : {
            '1' : r',+ D~~,' + '\n' + r',\_ F~~,' + '\\' + '\n' + r',\_+ S~~,' + '\\',
            '2' : r',+ D~~,' + '\n' + r',\_ F~~,' + '\\' + '\n' + r',+ G~,' + '\n' + r',\_ R~,' + '\\'
            }
        }
}

class GlobalTester(unittest.TestCase):
    
    def testKeySignature(self):
        pass
    
    def testTimeSignature(self):
        pass
    
    def testPitches(self):
        pass
    
    def testChords(self):
        pass
    
    def testRests(self):
        pass
    
    def testAccidentals(self):
        pass
    
    def testArticulations(self):
        pass
    
    def testRepetition(self):
        pass
    
    def testCodaAndSegno(self):
        pass
    
    def testDynamics(self):
        pass
    
    def testExpressions(self):
        pass
    
    def testBeams(self):
        pass
    
    def testGrandStaff(self):
        pass
    
    def testLongBarlines(self):
        pass
    
    def testMultiparts(self):
        pass
        
def _show(self, stream, format=None):
    if __name__ != '__main__':
        if not format:
            stream.show()
        else:
            stream.show(format)

if __name__ == '__main__':
    unittest.main()
