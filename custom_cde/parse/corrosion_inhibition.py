# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.corrosion_inhibition
~~~~~~~~~~~~~~~~~~~~~~~~~~

Corrosion inhibition efficiency (%) parser.

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
from ..model import Compound, CorrosionInhibition
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

corrosion_inhibition_specifier = ((I('^Corrosion inhibition efficiency$') | (Optional(I('corrosion')) + (I('inhibitor') | I('inhibition')) + Optional(I('efficiency')))).hide() + \
                                  Optional(I('range')).hide() | \
                                  (Optional(lbrct) + (I('η') | I('CI') | I('CIE')) + Optional(rbrct)))('corrosion_inhibition').add_action(merge)

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         corrosion_inhibition_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match units of property
units = (R('%'))('units')

#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() +(R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + ((I('to') | I('and')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
corrosion_inhibition_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
corrosion_inhibition_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a corrosion_inhibition efficiency value
value = Optional(lbrct).hide() + (corrosion_inhibition_range | corrosion_inhibition_value) + Optional(rbrct).hide()('value')

#all corrosion_inhibition instances
corrosion_inhibition = (prefix + Optional(delim).hide() + value + units)('corrosion_inhibition')

#phrases that list corrosion_inhibition efficiency in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(corrosion_inhibition) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given corrosion_inhibition efficiency
cem_corrosion_inhibition_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + corrosion_inhibition + Optional(rbrct))('corrosion_inhibition_phrase')

#phrases that culminate in a corrosion_inhibition efficiency value after experimental augmentation
to_give_corrosion_inhibition_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(corrosion_inhibition) + Not(cem) + Any()).hide() + corrosion_inhibition)('corrosion_inhibition_phrase')

#other phrases where experimental changes lead to a corrosion_inhibition efficiency value
obtained_corrosion_inhibition_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was') + Optional(I('found to be'))).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(corrosion_inhibition) + Not(cem) + Any()).hide() + corrosion_inhibition)('corrosion_inhibition_phrase')

#declaratory CEM phrase (the __ of cem is..)
declaratory_corrosion_inhibition_phrase = (I('the') + corrosion_inhibition + I('of') + (cem | chemical_label | lenient_chemical_label) + (I('is') | I('is equal to') | I('=')) + corrosion_inhibition)('corrosion_inhibition_phrase')

#final, cumulative phrase pattern matching
corrosion_inhibition_phrase = cem_corrosion_inhibition_phrase | to_give_corrosion_inhibition_phrase | obtained_corrosion_inhibition_phrase | declaratory_corrosion_inhibition_phrase

class CorrosionInhibitionParser(BaseParser):
    """
    
    """
    root = corrosion_inhibition_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            corrosion_inhibition=[
                CorrosionInhibition(
                    #Why won't it work if using xpath('./corrosion_inhibition/value/text()')?
                    value=first(result.xpath('./corrosion_inhibition/value/text()')),
                    units=first(result.xpath('./corrosion_inhibition/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


