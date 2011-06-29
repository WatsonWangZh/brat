#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

'''
Primitive sentente splitting using Sampo Pyysalo's GeniaSS sentence split
refiner. Also a primitive Japanese sentence splitter.

Author:     Pontus Stenetorp <pontus stenetorp se>
Version:    2011-05-09
'''

from re import compile as re_compile
from re import DOTALL
from os.path import join as path_join
from os.path import dirname
from subprocess import Popen, PIPE
from shlex import split as shlex_split

### Constants
# Require a leading non-whitespace, end on delimiter and space
# or newline followed by non-whitespace
# TODO XXX The last alternative group appears to have wrong grouping, check
EN_SENTENCE_END_REGEX = re_compile( r'\S.*?(:?(?:\.|!|\?)(?=\s+)|(?=\n+\S))', DOTALL)
JP_SENTENCE_END_REGEX = re_compile(ur'\S.*?[。！？]+(:?(?![。！？])|(?=\n+\S))', DOTALL)
###

def _refine_split(offsets, original_text):
    # Postprocessor expects newlines, so add. Also, replace
    # sentence-internal newlines with spaces not to confuse it.
    new_text = '\n'.join((original_text[o[0]:o[1]].replace('\n', ' ')
            for o in offsets))

    from sspostproc import refine_split
    output = refine_split(new_text)

    # Align the texts and see where our offsets don't match
    old_offsets = offsets[::-1]
    # Protect against edge case of single-line docs missing
    # sentence-terminal newline
    if len(old_offsets) == 0:
        old_offsets.append((0,len(original_text)))
    new_offsets = []
    for refined_sentence in output.split('\n'):
        new_offset = old_offsets.pop()
        # Merge the offsets if we have received a corrected split
        while new_offset[1] - new_offset[0] < len(refined_sentence) - 1:
            _, next_end = old_offsets.pop()
            new_offset = (new_offset[0], next_end)
        new_offsets.append(new_offset)

    # protect against missing document-final newline causing the last
    # sentence to fall out of offset scope
    if len(new_offsets) != 0 and new_offsets[-1][1] != len(original_text)-1:
        start = new_offsets[-1][1]+1
        while start < len(original_text) and original_text[start].isspace():
            start += 1
        if start < len(original_text)-1:
            new_offsets.append((start, len(original_text)-1))

    return new_offsets

def _sentence_boundary_gen(text, regex):
    for match in regex.finditer(text):
        yield match.span()

def jp_sentence_boundary_gen(text):
    for o in _sentence_boundary_gen(text, JP_SENTENCE_END_REGEX):
        yield o
       
# TODO: The regular expression is too crude, plug in the refine
#       script as well so that we can have reasonable splits.
def en_sentence_boundary_gen(text):
    for o in _refine_split([_o for _o in _sentence_boundary_gen(
                text, EN_SENTENCE_END_REGEX)], text):
        yield o

if __name__ == '__main__':
    from sys import argv

    from annotation import open_textfile

    def _text_by_offsets_gen(text, offsets):
        for start, end in offsets:
            yield text[start:end]

    if len(argv) > 1:
        try:
            for txt_file_path in argv[1:]:
                print
                print '### Splitting:', txt_file_path
                with open_textfile(txt_file_path, 'r') as txt_file:
                    text = txt_file.read()
                print '# Original text:'
                print text.replace('\n', '\\n')
                offsets = [o for o in en_sentence_boundary_gen(text)]
                print '# Offsets:'
                print offsets
                print '# Sentences:'
                for sentence in _text_by_offsets_gen(text, offsets):
                    assert sentence, 'blank sentences disallowed'
                    assert not sentence[0].isspace(), (
                            'sentence may not start with white-space "%s"' % sentence)
                    print '"%s"' % sentence.replace('\n', '\\n')
        except IOError:
            pass # Most likely a broken pipe
    else:
        sentence = u'　変しん！　両になった。うそ！　かも　'
        print 'Sentence:', sentence
        print 'Len sentence:', len(sentence)

        ret = [o for o in jp_sentence_boundary_gen(sentence)]
        ans = [(1, 5), (6, 12), (12, 15), (16, 18)]
        assert ret == ans, '%s != %s' % (ret, ans)
        print 'Succesful!'

        sentence = ' One of these days Jimmy, one of these days. Boom! Kaboom '
        print 'Sentence:', sentence
        print 'Len sentence:', len(sentence)

        ret = [o for o in en_sentence_boundary_gen(sentence)]
        ans = [(1, 44), (45, 50), (51, 57)]
        assert ret == ans, '%s != %s' % (ret, ans)
        print 'Succesful!'

        # TODO XXX: remove tests that assume local filesystem structure
        with open('/home/ninjin/public_html/brat/brat_test_data/epi/PMID-18573876.txt', 'r') as _file:
            sentence = _file.read()

        print 'Sentence:', sentence
        print 'Len sentence:', len(sentence)

        ret = [o for o in en_sentence_boundary_gen(sentence)]
        last_end = 0
        for start, end in ret:
            if last_end != start:
                print 'DROPPED: "%s"' % sentence[last_end:start]
            print 'SENTENCE: "%s"' % sentence[start:end]
            last_end = end
        print ret
