# -*- coding: utf-8 -*-
"""
chemdataextractor.parse.tg
~~~~~~~~~~~~~~~~~~~~~~~~~~

LUMO energy level parser.

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
from ..model import Compound, LUMOLevel
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

lumo_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)
lumo_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)
value = (lumo_range | lumo_value)('value')

#keyword matching for text that triggers value scraping
prefix = (Optional(I('a') | I('the')) + \
         Optional(I('^LUMO$') | I('LUMO') | I('LUMO level') | I('LUMO energy') | I('LUMO energy level')) +\
         Optional(I('ELUMO') | I('E_LUMO')) + \
         Optional(I('of') | I('=') | I('equal to') | I('is') | I('is equal to')))


#combine everything into a single, labeled regex-matching pattern
lumo = (prefix + value + units)('lumo')


class LUMOParser(BaseParser):
    """
    
    """
    root = lumo

    def interpret(self, result, start, end):
        compound = Compound(
            LUMO_level=[
                LUMOLevel(
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


