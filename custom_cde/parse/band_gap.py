# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.tg
~~~~~~~~~~~~~~~~~~~~~~~~~~

HOMO energy level parser.

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

#Regex to match units that may be followed by delimiters
units = (R('eV'))('units')

#Regex to match ranges of values or single values
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)

spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() +(R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)

to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + (I('to') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)

bg_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)
bg_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)
value = (bg_range | bg_value)('value')

#keyword matching for text that triggers value scraping
prefix = (Optional(I('a') | I('the')) + \
         Optional(I('^Band gap$') | I('Band gap') | I('Band gap energy') | I('HOMO\-LUMO offset')) + \
         Optional(I('EBandGap') | I('E_BandGap') | I('E_Gap') | I('E_BG') | I('E_G')) + \
         Optional(I('of') | I('=') | I('equal to') | I('is') | I('is equal to')))


#combine everything into a single, labeled regex-matching pattern
band_gap = (prefix + value + units)('band_gap')


class BandGapParser(BaseParser):
    """
    
    """
    root = band_gap

    def interpret(self, result, start, end):
        compound = Compound(
            band_gap=[
                BandGap(
                    value=first(result.xpath('./value/text()')),
                    units=first(result.xpath('./units/text()'))
                )
            ]
        )
        cem_el = first(result.xpath('./cem'))
        if cem_el is not None:
            compound.names = cem_el.xpath('./name/text()')
            compound.labels = cem_el.xpath('./label/text()')
        yield compound


