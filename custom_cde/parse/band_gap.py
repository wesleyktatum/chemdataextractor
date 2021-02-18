# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.band_gap
~~~~~~~~~~~~~~~~~~~~~~~~~~

band gap energy level parser.

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
from ..model import Compound, BandGap
from .actions import merge, join
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore

log = logging.getLogger(__name__)

band_gap_specifier = ((I('^Band Gap$') | I('^Optical band gap$')) | \
                      (Optional(lbrct) + (I('EG') | I('Eg') | I('E_g') | I('EBG') | I('E_BG') | I('EBandGap') | I('X')) + Optional(rbrct)) | \
                      (Optional (I('optical')) + (I('band gap') | I('bandgap')) + Optional(I('energy')) + Optional(I('level'))))('band_gap').add_action(merge)

#keyword matching for phrases that trigger value scraping
prefix = (Optional(Optional('has') + Optional(I('a') | I('an')))).hide() + \
         (Optional(I('the'))).hide() + \
         band_gap_specifier + \
         (Optional(I('of') | I('=') | I('equal to') | (I('is') + Optional(I('between'))) | I('is equal to')) | I('was found to be')).hide() + \
         (Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('ca') | I('ca.'))).hide()

#generic list of delimiters
delim = R('^[:;\.,]$')

#Regex to match units of property
units = (R('eV'))('units')

#Regex to match ranges of values or single values (with or without spaces)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() +(R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + ((I('to') | I('and')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

#ranged instances
band_gap_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)

#value instances
band_gap_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)

#regex or matching the reporting of a band_gap energy
energy = Optional(lbrct).hide() + (band_gap_range | band_gap_value)('value') + Optional(rbrct).hide()

#all band_gap instances
band_gap = (prefix + Optional(delim).hide() + energy + units)('band_gap')

#phrases that list band_gap level in parentheses or brackets
bracket_any = lbrct + OneOrMore(Not(band_gap) + Not(rbrct) + Any()) + rbrct

#phrases that list an entity having a given band_gap level
cem_band_gap_phrase = (Optional(cem) + Optional(I('having')).hide() + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() + Optional(lbrct) + band_gap + Optional(rbrct))('band_gap_phrase')

#phrases that culminate in a band_gap level after experimental augmentation
to_give_band_gap_phrase = ((I('to') + (I('give') | I('afford') | I('yield') | I('obtain')) | I('affording') | I('afforded') | I('gave') | I('yielded')).hide() + Optional(dt).hide() + (cem | chemical_label | lenient_chemical_label) + ZeroOrMore(Not(band_gap) + Not(cem) + Any()).hide() + band_gap)('band_gap_phrase')

#other phrases where experimental changes lead to a band_gap level
obtained_band_gap_phrase = ((cem | chemical_label) + (I('is') | I('are') | I('was')).hide() + (I('afforded') | I('obtained') | I('yielded')).hide() + ZeroOrMore(Not(band_gap) + Not(cem) + Any()).hide() + band_gap)('band_gap')

#final, cumulative phrase pattern matching
band_gap_phrase = cem_band_gap_phrase | to_give_band_gap_phrase | obtained_band_gap_phrase


class BandGapParser(BaseParser):
    """
    
    """
    root = band_gap_phrase

    def interpret(self, result, start, end):
        compound = Compound(
            band_gap=[
                BandGap(
                    value=first(result.xpath('./band_gap/value/text()')),
                    units=first(result.xpath('./band_gap/units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


