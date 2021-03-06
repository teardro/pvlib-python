import datetime

import numpy as np
import pandas as pd

from pandas.util.testing import (assert_frame_equal, assert_series_equal,
                                 assert_index_equal)
from numpy.testing import assert_allclose
import pytest

from pvlib.location import Location
from pvlib import solarposition

from conftest import (requires_ephem, needs_pandas_0_17,
                      requires_spa_c, requires_numba)


# setup times and locations to be tested.
times = pd.date_range(start=datetime.datetime(2014,6,24),
                      end=datetime.datetime(2014,6,26), freq='15Min')

tus = Location(32.2, -111, 'US/Arizona', 700) # no DST issues possible
# In 2003, DST in US was from April 6 to October 26
golden_mst = Location(39.742476, -105.1786, 'MST', 1830.14) # no DST issues possible
golden = Location(39.742476, -105.1786, 'America/Denver', 1830.14) # DST issues possible

times_localized = times.tz_localize(tus.tz)

tol = 5

@pytest.fixture()
def expected_solpos():
    return pd.DataFrame({'elevation': 39.872046,
                         'apparent_zenith': 50.111622,
                         'azimuth': 194.340241,
                         'apparent_elevation': 39.888378},
                        index=['2003-10-17T12:30:30Z'])

# the physical tests are run at the same time as the NREL SPA test.
# pyephem reproduces the NREL result to 2 decimal places.
# this doesn't mean that one code is better than the other.

@requires_spa_c
def test_spa_c_physical(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,12,30,30),
                          periods=1, freq='D', tz=golden_mst.tz)
    ephem_data = solarposition.spa_c(times, golden_mst.latitude,
                                     golden_mst.longitude,
                                     pressure=82000,
                                     temperature=11)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


@requires_spa_c
def test_spa_c_physical_dst(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.spa_c(times, golden.latitude,
                                     golden.longitude,
                                     pressure=82000,
                                     temperature=11)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_spa_python_numpy_physical(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,12,30,30),
                          periods=1, freq='D', tz=golden_mst.tz)
    ephem_data = solarposition.spa_python(times, golden_mst.latitude,
                                          golden_mst.longitude,
                                          pressure=82000,
                                          temperature=11, delta_t=67,
                                          atmos_refract=0.5667,
                                          how='numpy')
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_spa_python_numpy_physical_dst(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.spa_python(times, golden.latitude,
                                          golden.longitude,
                                          pressure=82000,
                                          temperature=11, delta_t=67,
                                          atmos_refract=0.5667,
                                          how='numpy')
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


@requires_numba
def test_spa_python_numba_physical(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,12,30,30),
                          periods=1, freq='D', tz=golden_mst.tz)
    ephem_data = solarposition.spa_python(times, golden_mst.latitude,
                                          golden_mst.longitude,
                                          pressure=82000,
                                          temperature=11, delta_t=67,
                                          atmos_refract=0.5667,
                                          how='numba', numthreads=1)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


@requires_numba
def test_spa_python_numba_physical_dst(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.spa_python(times, golden.latitude,
                                          golden.longitude, pressure=82000,
                                          temperature=11, delta_t=67,
                                          atmos_refract=0.5667,
                                          how='numba', numthreads=1)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


@needs_pandas_0_17
def test_get_sun_rise_set_transit():
    south = Location(-35.0, 0.0, tz='UTC')
    times = pd.DatetimeIndex([datetime.datetime(1996, 7, 5, 0),
                              datetime.datetime(2004, 12, 4, 0)]
                             ).tz_localize('UTC')
    sunrise = pd.DatetimeIndex([datetime.datetime(1996, 7, 5, 7, 8, 15),
                                datetime.datetime(2004, 12, 4, 4, 38, 57)]
                               ).tz_localize('UTC').tolist()
    sunset = pd.DatetimeIndex([datetime.datetime(1996, 7, 5, 17, 1, 4),
                               datetime.datetime(2004, 12, 4, 19, 2, 2)]
                              ).tz_localize('UTC').tolist()
    result = solarposition.get_sun_rise_set_transit(times, south.latitude,
                                                    south.longitude,
                                                    delta_t=64.0)
    frame = pd.DataFrame({'sunrise':sunrise, 'sunset':sunset}, index=times)
    result_rounded = pd.DataFrame(index=result.index)
    # need to iterate because to_datetime does not accept 2D data
    # the rounding fails on pandas < 0.17
    for col, data in result.iteritems():
        result_rounded[col] = pd.to_datetime(
            np.floor(data.values.astype(np.int64) / 1e9)*1e9, utc=True)

    del result_rounded['transit']
    assert_frame_equal(frame, result_rounded)


    # tests from USNO
    # Golden
    golden = Location(39.0, -105.0, tz='MST')
    times = pd.DatetimeIndex([datetime.datetime(2015, 1, 2),
                              datetime.datetime(2015, 8, 2),]
                             ).tz_localize('MST')
    sunrise = pd.DatetimeIndex([datetime.datetime(2015, 1, 2, 7, 19, 2),
                                datetime.datetime(2015, 8, 2, 5, 1, 26)
                                ]).tz_localize('MST').tolist()
    sunset = pd.DatetimeIndex([datetime.datetime(2015, 1, 2, 16, 49, 10),
                               datetime.datetime(2015, 8, 2, 19, 11, 31)
                               ]).tz_localize('MST').tolist()
    result = solarposition.get_sun_rise_set_transit(times, golden.latitude,
                                                    golden.longitude,
                                                    delta_t=64.0)
    frame = pd.DataFrame({'sunrise':sunrise, 'sunset':sunset}, index=times)
    result_rounded = pd.DataFrame(index=result.index)
    # need to iterate because to_datetime does not accept 2D data
    # the rounding fails on pandas < 0.17
    for col, data in result.iteritems():
        result_rounded[col] = (pd.to_datetime(
            np.floor(data.values.astype(np.int64) / 1e9)*1e9, utc=True)
            .tz_convert('MST'))

    del result_rounded['transit']
    assert_frame_equal(frame, result_rounded)


@requires_ephem
def test_pyephem_physical(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,12,30,30),
                          periods=1, freq='D', tz=golden_mst.tz)
    ephem_data = solarposition.pyephem(times, golden_mst.latitude,
                                       golden_mst.longitude, pressure=82000,
                                       temperature=11)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos.round(2),
                       ephem_data[expected_solpos.columns].round(2))

@requires_ephem
def test_pyephem_physical_dst(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30), periods=1,
                          freq='D', tz=golden.tz)
    ephem_data = solarposition.pyephem(times, golden.latitude,
                                       golden.longitude, pressure=82000,
                                       temperature=11)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos.round(2),
                       ephem_data[expected_solpos.columns].round(2))

@requires_ephem
def test_calc_time():
    import pytz
    import math
    # validation from USNO solar position calculator online

    epoch = datetime.datetime(1970,1,1)
    epoch_dt = pytz.utc.localize(epoch)

    loc = tus
    loc.pressure = 0
    actual_time = pytz.timezone(loc.tz).localize(
        datetime.datetime(2014, 10, 10, 8, 30))
    lb = pytz.timezone(loc.tz).localize(datetime.datetime(2014, 10, 10, tol))
    ub = pytz.timezone(loc.tz).localize(datetime.datetime(2014, 10, 10, 10))
    alt = solarposition.calc_time(lb, ub, loc.latitude, loc.longitude,
                                  'alt', math.radians(24.7))
    az = solarposition.calc_time(lb, ub, loc.latitude, loc.longitude,
                                 'az', math.radians(116.3))
    actual_timestamp = (actual_time - epoch_dt).total_seconds()

    assert_allclose((alt.replace(second=0, microsecond=0) -
                          epoch_dt).total_seconds(), actual_timestamp)
    assert_allclose((az.replace(second=0, microsecond=0) -
                          epoch_dt).total_seconds(), actual_timestamp)

@requires_ephem
def test_earthsun_distance():
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D')
    distance = solarposition.pyephem_earthsun_distance(times).values[0]
    assert_allclose(1, distance, atol=0.1)


def test_ephemeris_physical(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,12,30,30),
                          periods=1, freq='D', tz=golden_mst.tz)
    ephem_data = solarposition.ephemeris(times, golden_mst.latitude,
                                         golden_mst.longitude,
                                         pressure=82000,
                                         temperature=11)
    expected_solpos.index = times
    expected_solpos = np.round(expected_solpos, 2)
    ephem_data = np.round(ephem_data, 2)
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_ephemeris_physical_dst(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.ephemeris(times, golden.latitude,
                                         golden.longitude, pressure=82000,
                                         temperature=11)
    expected_solpos.index = times
    expected_solpos = np.round(expected_solpos, 2)
    ephem_data = np.round(ephem_data, 2)
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_get_solarposition_error():
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    with pytest.raises(ValueError):
        ephem_data = solarposition.get_solarposition(times, golden.latitude,
                                                     golden.longitude,
                                                     pressure=82000,
                                                     temperature=11,
                                                     method='error this')


@pytest.mark.parametrize(
    "pressure, expected", [
    (82000, expected_solpos()),
    (90000, pd.DataFrame(
        np.array([[  39.88997,   50.11003,  194.34024,   39.87205,   14.64151,
                     50.12795]]),
        columns=['apparent_elevation', 'apparent_zenith', 'azimuth', 'elevation',
                 'equation_of_time', 'zenith'],
        index=expected_solpos().index))
    ])
def test_get_solarposition_pressure(pressure, expected):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.get_solarposition(times, golden.latitude,
                                                 golden.longitude,
                                                 pressure=pressure,
                                                 temperature=11)
    this_expected = expected.copy()
    this_expected.index = times
    this_expected = np.round(this_expected, 5)
    ephem_data = np.round(ephem_data, 5)
    assert_frame_equal(this_expected, ephem_data[this_expected.columns])


@pytest.mark.parametrize(
    "altitude, expected", [
    (golden.altitude, expected_solpos()),
    (2000, pd.DataFrame(
        np.array([[  39.88788,   50.11212,  194.34024,   39.87205,   14.64151,
                     50.12795]]),
        columns=['apparent_elevation', 'apparent_zenith', 'azimuth', 'elevation',
                 'equation_of_time', 'zenith'],
        index=expected_solpos().index))
    ])
def test_get_solarposition_altitude(altitude, expected):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.get_solarposition(times, golden.latitude,
                                                 golden.longitude,
                                                 altitude=altitude,
                                                 temperature=11)
    this_expected = expected.copy()
    this_expected.index = times
    this_expected = np.round(this_expected, 5)
    ephem_data = np.round(ephem_data, 5)
    assert_frame_equal(this_expected, ephem_data[this_expected.columns])


def test_get_solarposition_no_kwargs(expected_solpos):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.get_solarposition(times, golden.latitude,
                                                 golden.longitude)
    expected_solpos.index = times
    expected_solpos = np.round(expected_solpos, 2)
    ephem_data = np.round(ephem_data, 2)
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_nrel_earthsun_distance():
    times = pd.DatetimeIndex([datetime.datetime(2015, 1, 2),
                              datetime.datetime(2015, 8, 2),]
                             ).tz_localize('MST')
    result = solarposition.nrel_earthsun_distance(times, delta_t=64.0)
    expected = pd.Series(np.array([0.983289204601, 1.01486146446]),
                         index=times)
    assert_series_equal(expected, result)

    times = datetime.datetime(2015, 1, 2)
    result = solarposition.nrel_earthsun_distance(times, delta_t=64.0)
    expected = pd.Series(np.array([0.983289204601]),
                         index=pd.DatetimeIndex([times, ]))
    assert_series_equal(expected, result)
