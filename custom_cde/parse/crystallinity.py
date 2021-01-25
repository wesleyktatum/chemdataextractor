# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.crystallinity
~~~~~~~~~~~~~~~~~~~~~~~~~~

Parser for the degree of crystallinity (Xc)
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
from ..model import Compound, Crystallinity
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

#####################################################################
# Customize these patterns and variable names to your custom property
#####################################################################


crystallinity_specifier = ((I('^Crystallinity$') | I("^Relative Crystallinity$")) | \
                 (Optional(lbrct) + (I('Xc') | I('X_c') | I('Χ') | I('Χc') | I('Χ_c') | I('χ') | I('χc') | I('χ_c') | I('RDOC') | I('DOC')) + Optional(rbrct)) | \
                 (Optional(I('relative')) + Optional(I('degree')) + Optional(I('of')) + I('crystallinity'))).hide()('crystallinity')

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         crystallinity_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#Regex to match units of property
units = (I('%'))('units')


######################################################
# make sure variable names match up below here
######################################################

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() +(R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + ((I('to') | I('and')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
crystallinity_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
crystallinity_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a crystallinity value
value = Optional(lbrct).hide() + (crystallinity_range | crystallinity_value) + Optional(rbrct).hide()('value')

#all crystallinity instances
crystallinity = (prefix + Optional(delim).hide() + value + units)('crystallinity')

#phrases that list crystallinity in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(crystallinity) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given crystallinity
cem_crystallinity_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + crystallinity + Optional(rbrct))('crystallinity_phrase')

#phrases that culminate in a crystallinity value after experimental augmentation
to_give_crystallinity_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(crystallinity) + Not(cem) + Any()).hide() + crystallinity)('crystallinity_phrase')

#other phrases where experimental changes lead to a crystallinity value
obtained_crystallinity_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was') + Optional(I('found to be'))).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(crystallinity) + Not(cem) + Any()).hide() + crystallinity)('crystallinity_phrase')

#declaratory CEM phrase (the __ of cem is..)
declaratory_crystallinity_phrase = (I('the') + crystallinity + I('of') + (cem | chemical_label | lenient_chemical_label) + (I('is') | I('is equal to') | I('=')) + crystallinity)('crystallinity_phrase')

#final, cumulative phrase pattern matching
crystallinity_phrase = cem_crystallinity_phrase | to_give_crystallinity_phrase | obtained_crystallinity_phrase | declaratory_crystallinity_phrase

class CrystallinityParser(BaseParser):
    """
    
    """
    root = crystallinity_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            crystallinity=[
                Crystallinity(
                    #Why won't it work if using xpath('./crystallinity/value/text()')?
                    value=first(result.xpath('./crystallinity/value/text()')),
                    units=first(result.xpath('./crystallinity/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


