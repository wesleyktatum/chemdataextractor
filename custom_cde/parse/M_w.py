# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.M_w
~~~~~~~~~~~~~~~~~~~~~~~~~~

Weight average molecular weight
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import re

from .cem import cem, chemical_label, lenient_chemical_label, solvent_name
from .common import lbrct, dt, rbrct, hyphen
from ..utils import first
from ..model import Compound, WeightAvgMolecularWeight
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

M_w_specifier = ((I('^Molecular weight$') | I('^Weight averaged molecular weight$')) | \
                 (Optional(lbrct) + (I('Mw') | I('M_w')) + Optional(rbrct)) | \
                 (Optional(I('weight') + Optional(I('/-')) + I('average')) + I('molecular weight'))).hide()('M_w')

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         M_w_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match units of property
units = ((I('kDa') | I('Da')) | \
         ((I('g') | I('kg')) + (R('/') | I('per')) + R('mol')))('units').add_action(merge)




#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() +(R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + ((I('to') | I('and')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
M_w_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
M_w_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a M_w value
value = Optional(lbrct).hide() + (M_w_range | M_w_value) + Optional(rbrct).hide()('value')

#all M_w instances
M_w = (prefix + Optional(delim).hide() + value + units)('M_w')

#phrases that list M_w in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(M_w) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given M_w
cem_M_w_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + M_w + Optional(rbrct))('M_w_phrase')

#phrases that culminate in a M_w value after experimental augmentation
to_give_M_w_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(M_w) + Not(cem) + Any()).hide() + M_w)('M_w_phrase')

#other phrases where experimental changes lead to a M_w value
obtained_M_w_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was') + Optional(I('found to be'))).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(M_w) + Not(cem) + Any()).hide() + M_w)('M_w_phrase')

#declaratory CEM phrase (the __ of cem is..)
declaratory_M_w_phrase = (I('the') + M_w + I('of') + (cem | chemical_label | lenient_chemical_label) + (I('is') | I('is equal to') | I('=')) + M_w)('M_w_phrase')

#final, cumulative phrase pattern matching
M_w_phrase = cem_M_w_phrase | to_give_M_w_phrase | obtained_M_w_phrase | declaratory_M_w_phrase

class WeightAvgMolecularWeightParser(BaseParser):
    """
    
    """
    root = M_w_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            M_w=[
                WeightAvgMolecularWeight(
                    #Why won't it work if using xpath('./M_w/value/text()')?
                    value=first(result.xpath('./M_w/value/text()')),
                    units=first(result.xpath('./M_w/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


