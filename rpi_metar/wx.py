"""Weather parsing utilities."""
import logging
import re
from enum import Enum
from fractions import Fraction
from rpi_metar.leds import GREEN, RED, BLUE, MAGENTA, YELLOW, BLACK, ORANGE, WHITE

log = logging.getLogger(__name__)


class FlightCategory(Enum):
    VFR = BLUE
    IFR = ORANGE
    MVFR = GREEN
    LIFR = RED
    UNKNOWN = YELLOW
    OFF = BLACK
    MISSING = MAGENTA


def get_conditions(metar_info):
    """Returns the visibility, ceiling, wind speed, and gusts for a given airport from some metar info."""
    log.debug(metar_info)
    visibility = ceiling = 10000
    speed = gust = 0
    # Visibility

    # Match metric visibility and convert to KM and find visibility greater than 9999 = KM
    match = re.search(r'(?P<CAVOK>CAVOK)|(\s(?P<visibility>\d{4}|\/{4})\s)|(\s(?P<visibilityKM>\d{2}.[KM]|\/{2})\s)', metar_info)
    if match.group('visibility'):
        try:
            visibility = float(match.group('visibility')) / 1000
        except ValueError:
            visibility = 10
    if match.group('CAVOK'):
        visibility = 10
    if match.group('visibilityKM'):
        visibility = 10

    # Match SM Visibility and convert to KM
    # We may have fractions, e.g. 1/8SM or 1 1/2SM
    # Or it will be whole numbers, e.g. 2SM
    # There's also variable wind speeds, followed by vis, e.g. 300V360 1/2SM
    match = re.search(r'(?P<visibility>\b(?:\d+\s+)?\d+(?:/\d)?)SM', metar_info)
    if match:
        visibility = match.group('visibility')
        try:
            visibility = float(sum(Fraction(s) for s in visibility.split())) * 1609 / 1000
        except ZeroDivisionError:
            visibility = None
    # Ceiling for SCT and BKN and OVC
    # match = re.search(r'(VV|SCT|BKN|OVC)(?P<ceiling>\d{3})', metar_info)
    # Alternative ceiling only for BKN and OVC > more practicable
    match = re.search(r'(VV|BKN|OVC)(?P<ceiling>\d{3})', metar_info)
    if match:
        ceiling = int(match.group('ceiling')) * 100  # It is reported in hundreds of feet
    # Wind info
    match = re.search(r'\b\d{3}(?P<speed>\d{2,3})G?(?P<gust>\d{2,3})?KT', metar_info)
    if match:
        speed = int(match.group('speed'))
        gust = int(match.group('gust')) if match.group('gust') else 0
    return (visibility, ceiling, speed, gust)


def get_flight_category(visibility, ceiling):
    """Converts weather conditions into a category."""
    log.debug('Finding category for %s, %s', visibility, ceiling)
    if visibility is None and ceiling is None:
        return FlightCategory.UNKNOWN

    # Unlimited ceiling
    if visibility and ceiling is None:
        ceiling = 10000

    # http://www.faraim.org/aim/aim-4-03-14-446.html
    # Visibility thresholds in KM
    #try:
    #    if visibility < 1 or ceiling < 500:
    #        return FlightCategory.LIFR
    #    elif 1 <= visibility < 3 or 500 <= ceiling < 1000:
    #        return FlightCategory.IFR
    #    elif 3 <= visibility <= 5 or 1000 <= ceiling <= 3000:
    #        return FlightCategory.MVFR
    #    elif visibility > 5 and ceiling > 3000:
    #        return FlightCategory.VFR
    
    # Visibilty thresholds mapped to a more VFR-like decission matrix near to European GAFOR reporting
    # airports.py has also to be changed to get als metar data to be parsed by this section
    # VFR = Blue sky, no clouds below 5000 feet and visibility 10km or more
    # MVFR = Visibilty more than 8km and acceptable ceiling
    # IFR = critical for VFR
    # LIFR = no VFR possible
        try:
        if visibility < 8 or ceiling < 1500:
            return FlightCategory.LIFR
        elif visibility >= 8 and ceiling < 2500:
            return FlightCategory.IFR
        elif visibility >= 8 and 2500 <= ceiling < 5000:
            return FlightCategory.MVFR
        elif 8 <= visibility < 9.999  and ceiling >= 5000 :
            return FlightCategory.MVFR
        elif visibility >= 9.999 and ceiling >= 5000:
            return FlightCategory.VFR

    
    except (TypeError, ValueError):
        log.exception('Failed to get flight category from {vis}, {ceil}'.format(
            vis=visibility,
            ceil=ceiling
        ))
