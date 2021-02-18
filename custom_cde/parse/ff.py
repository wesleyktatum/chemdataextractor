# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.ff
~~~~~~~~~~~~~~~~~~~~~~~~~~

Fill Factor (FF,unitless) of photovoltaic devices
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
from ..model import Compound, FF
from .actions import merge, join, fix_whitespace
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

#####################################################################
# Customize these patterns and variable names to your custom property
#####################################################################

ff_specifier = ((I('^Fill factor$') | I('^FF$')) | \
                 (Optional(lbrct) + I('FF') + Optional(rbrct)) | \
                 (I('fill') + I('factor'))).hide()('ff')

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         ff_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#############################################################
# make sure variable names and xpath tags match up below here
#############################################################

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + (R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + ((I('to') | I('and')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
ff_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
ff_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a ff value
value = Optional(lbrct).hide() + (ff_range | ff_value) + Optional(rbrct).hide()('value')

#all ff instances
ff = (prefix + Optional(delim).hide() + value)('ff')

#phrases that list ff in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(ff) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given ff
cem_ff_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + ff + Optional(rbrct))('ff_phrase')

#phrases that culminate in a ff value after experimental augmentation
to_give_ff_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(ff) + Not(cem) + Any()).hide() + ff)('ff_phrase')

#other phrases where experimental changes lead to a ff value
obtained_ff_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was') + Optional(I('found to be'))).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(ff) + Not(cem) + Any()).hide() + ff)('ff_phrase')

#declaratory CEM phrase (the __ of cem is..)
declaratory_ff_phrase = (I('the') + ff + I('of') + (cem | chemical_label | lenient_chemical_label) + (I('is') | I('is equal to') | I('=')) + ff)('ff_phrase')

#final, cumulative phrase pattern matching
ff_phrase = cem_ff_phrase | to_give_ff_phrase | obtained_ff_phrase | declaratory_ff_phrase

class FFParser(BaseParser):
    """
    
    """
    root = ff_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            ff=[
                FF(
                    value=first(result.xpath('./ff/value/text()')),
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


