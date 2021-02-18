# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.dispersity
~~~~~~~~~~~~~~~~~~~~~~~~~~

Dispersity (Đ), or polydispersity index (PDI).

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
from ..model import Compound, Dispersity
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

#####################################################################
# Customize these patterns and variable names to your custom property
#####################################################################


dispersity_specifier = ((I('^Dispersity$') | I('^Polydispersity index$')) | \
                 (Optional(lbrct) + (I('PDI') | I('Đ') | I('Đm')) + Optional(rbrct)) | \
                 (I('dispersity') | I('polydispersity index'))).hide()('dispersity')

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         dispersity_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()


######################################################
# make sure variable names match up below here
######################################################

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + (R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + ((I('to') | I('and')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
dispersity_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
dispersity_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a dispersity value
value = Optional(lbrct).hide() + (dispersity_range | dispersity_value) + Optional(rbrct).hide()('value')

#all dispersity instances
dispersity = (prefix + Optional(delim).hide() + value)('dispersity')

#phrases that list dispersity in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(dispersity) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given dispersity
cem_dispersity_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + dispersity + Optional(rbrct))('dispersity_phrase')

#phrases that culminate in a dispersity value after experimental augmentation
to_give_dispersity_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(dispersity) + Not(cem) + Any()).hide() + dispersity)('dispersity_phrase')

#other phrases where experimental changes lead to a dispersity value
obtained_dispersity_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was') + Optional(I('found to be'))).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(dispersity) + Not(cem) + Any()).hide() + dispersity)('dispersity_phrase')

#declaratory CEM phrase (the __ of cem is..)
declaratory_dispersity_phrase = (I('the') + dispersity + I('of') + (cem | chemical_label | lenient_chemical_label) + (I('is') | I('is equal to') | I('=')) + dispersity)('dispersity_phrase')

#final, cumulative phrase pattern matching
dispersity_phrase = cem_dispersity_phrase | to_give_dispersity_phrase | obtained_dispersity_phrase | declaratory_dispersity_phrase

class DispersityParser(BaseParser):
    """
    
    """
    root = dispersity_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            dispersity=[
                Dispersity(
                    value=first(result.xpath('./dispersity/value/text()')),
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


