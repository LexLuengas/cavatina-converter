import unittest
from music21 import *
from .language.syntax import parse
from .translator import translateToMusic21

testStrings = {
    'key signatures' : '+------- F F F,_-- F F F,+_= F F F,',
    'time signatures' : '_~44D D D D,~68d d d d d d,~128D,~1216,~816.',
    'pitches' : {
            'eighths' : 'z x c v b n m a s d f g h j q w e r t y u 1 2 3 4 5 6 7 8 9 0',
            'quarters' : 'Z X C V B N M A S D F G H J Q W E R T Y U ! @ # $ % ^ & * ( )'
        },
    'chords' : {
        'eighths': ', adg sfh dgj fhq etu, zcb 680 zh0, sd dfg asdfghj,',
        'quarters': ', ADG SFH DGJ FHQ ETU,',
        'mixed' : ', DG~ DG~~ FG~~,'
        },
    'rests' : {
        'simple' : ', f G H~ J~~, ] } ]] }~ }~~.',
        'dotted' : ', ] } ]< }< ]]< }~< }~~<.'
        },
    'note-length modifiers' : ', a a~ a~~, A A~ A~~, D D< D~< D~~<, d d< d~< d~~<.',
    'accidentals' : ', a a- a--, g g= g==, f- f= f-=.',
    'articulations' : ', A\' A\'\' A\" A\"\", E\' E\'\' E\" E\"\",',
    'repetition markings' : {
        'simple' : ', A A A A; A A A A, A A A A: A A A A.',
        'endings' : [
                ', A A A A; A A A A,o A A A A o`,oo A A A A o`:',
                ', A A A A; A A A Ao, A A A A o`oo, A A A A o`:',
                ', A A A A; A A A Ao, A A A A oo, A A A A :',
            ]
        },
    'coda & segno' : {
        'simple' : ', A A A Ai, A A A AI, A A A A.',
        'references' : ', D Dk, D DK, D Dki , D DkI , D DKi , D DKI ;I  ,i  :'
        },
    'dynamics' : r', g\, g\\, g\\\, g|, g||, g|||, g\|, g|\, g\\\|, g||\, g\\|',
    'expressions' : ', d[ d[[ d[[[ d[[[[ g, d[[[[[ d d, d[[[[[[ d d d, d[`, d{ d{`.',
    'ottava' : ', DO F G HO`, F GOO G G,',
    'beams' : ', d f.., df f.., d dg.., j q.., f`h` f`.. f g.. d f.., d< f<--..,',
    'grand staff' : {
        'simple' : [
                r',+ D F G D,' + '\n' + r',\\_ D F G D,' + '\\',
                r',+~44F G H J, D F G H,' + '\n' + r',\\_~44F D Q J,\ H J H H,' + '\\',
            ],
        'muliple parts' : [
                r',+ D~~,' + '\n' + r',\_ F~~,' + '\\' + '\n' + r',\_+ S~~,' + '\\', # 3 parts
                r',+ D~~,' + '\n' + r',\_ F~~,' + '\\' + '\n' + r',+ G~,' + '\n' + r',\_ R~,' + '\\', # 2 parts
            ]
        }
}

class GlobalTester(unittest.TestCase):
    def testKeySignature(self):
        s = testStrings['key signatures']
        t = parse(s)
        score = translateToMusic21(t)
        
        keys = []
        for m in score[1]:
            for i in m.getElementsByClass(key.KeySignature):
                keys.append(i)
        
        self.assertEqual(len(keys), 3)
        self.assertEqual(keys[0].sharps, -7)
        self.assertEqual(keys[1].sharps, -2)
        self.assertEqual(keys[2].sharps, 1)
        
        clefs = []
        for m in score[1]:
            for i in m.getElementsByClass(clef.Clef):
                clefs.append(i)
        
        self.assertTrue(isinstance(clefs[0], clef.TrebleClef))
        self.assertTrue(isinstance(clefs[1], clef.BassClef))
        self.assertTrue(isinstance(clefs[2], clef.AltoClef))
        
        _show(score)
    
    def testTimeSignature(self):
        s = testStrings['time signatures']
        t = parse(s)
        score = translateToMusic21(t)
        _show(score)
    
    def testPitches(self):
        sEighths = testStrings['pitches']['eighths']
        sQuarters = testStrings['pitches']['quarters']
        
        t1 = parse(sEighths)
        score1 = translateToMusic21(t1)
        _show(score1)
        
        t2 = parse(sQuarters)
        score2 = translateToMusic21(t2)
        _show(score2)
        
    def testNoteLength(self):
        s = testStrings['note-length modifiers']
        t = parse(s)
        score = translateToMusic21(t)
        _show(score, 'musicxml')
    
    def testChords(self):
        sEighths = testStrings['chords']['eighths']
        sQuarters = testStrings['chords']['quarters']
        sMixed = testStrings['chords']['mixed']
        
        t1 = parse(sEighths)
        score1 = translateToMusic21(t1)
        _show(score1)
        
        t2 = parse(sQuarters)
        score2 = translateToMusic21(t2)
        _show(score2)
        
        t3 = parse(sMixed)
        score3 = translateToMusic21(t3)
        _show(score3)
    
    def testRests(self):
        s1 = testStrings['rests']['simple']
        s2 = testStrings['rests']['dotted']
        
        t1 = parse(s1)
        score1 = translateToMusic21(t1)
        _show(score1, 'musicxml')
        
        t2 = parse(s2)
        score2 = translateToMusic21(t2)
        _show(score2, 'musicxml')
    
    def testAccidentals(self):
        s = testStrings['accidentals']
        t = parse(s)
        score = translateToMusic21(t)
        _show(score)
    
    def testArticulations(self):
        s = testStrings['articulations']
        t = parse(s)
        score = translateToMusic21(t)
        _show(score)
    
    def testRepetition(self):
        sSimple = testStrings['repetition markings']['simple']
        sReferences = testStrings['repetition markings']['endings']
        
        t1 = parse(sSimple)
        score1 = translateToMusic21(t1)
        _show(score1)
        for r in sReferences:
            t2 = parse(r)
            score2 = translateToMusic21(t2)
            _show(score2)
    
    def testCodaAndSegno(self):
        sSimple = testStrings['coda & segno']['simple']
        sReferences = testStrings['coda & segno']['references']
        
        t1 = parse(sSimple)
        score1 = translateToMusic21(t1)
        _show(score1)
        t2 = parse(sReferences)
        score2 = translateToMusic21(t2)
        _show(score2)
    
    def testDynamics(self):
        s = testStrings['dynamics']
        t = parse(s)
        score = translateToMusic21(t)
        _show(score)
    
    def testExpressions(self):
        s = testStrings['expressions']
        t = parse(s)
        score = translateToMusic21(t)
        _show(score)
        
    def testOttava(self):
        s = testStrings['ottava']
        t = parse(s)
        score = translateToMusic21(t)
        _show(score)
        
    def testPedal(self):
        pass
        # NOTE: Not implemented in music21 library
        # s = testStrings['Pedal']
        # t = parse(s)
        # score = translateToMusic21(t)
        # _show(score)
    
    def testBeams(self):
        s = testStrings['beams']
        t = parse(s)
        score = translateToMusic21(t)
        _show(score, 'musicxml')
    
    def testGrandStaff(self):
        sList = testStrings['grand staff']['simple']
        for s in sList:
            t = parse(s)
            score = translateToMusic21(t)
            self.assertEqual(len(score.parts), 2)
            _show(score)
    
    def testMultiparts(self):
        sList = testStrings['grand staff']['muliple parts']
        for i, s in enumerate(sList):
            t = parse(s)
            score = translateToMusic21(t)
            if i == 0:
                self.assertEqual(len(score.parts), 3)
            if i == 1:
                self.assertEqual(len(score.parts), 2)
            _show(score)

def _show(stream, format=None):
    if __name__ != '__main__':
        if not format:
            stream.show('text')
        else:
            stream.show(format)

if __name__ == '__main__':
    unittest.main()
