#  Copyright 2019 The Salish Sea MEOPAR contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Functions for generating atmospheric forcing files for the SalishSeaCast NEMO model
from the ECCC 2007-2014 archival GEMLAM files produced by the experimental phase
of the HRPDS model.
"""
import logging
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import arrow
import click
import numpy
import xarray

from salishsea_tools import viz_tools

logging.getLogger(__name__).addHandler(logging.NullHandler())


def rpn_to_gemlam(
    netcdf_start_date,
    netcdf_end_date,
    forecast,
    rpn_dir,
    dest_dir,
    tmp_dir,
    keep_rpn_fcst_hr_files,
    bunzip2_rpn_fcst_hr_files,
):
    """Generate an atmospheric forcing file for the SalishSeaCast NEMO model
    from the ECCC 2007-2014 archival GEMLAM files produced by the experimental
    phase of the HRPDS model.
    \f
    :param netcdf_start_date: Start date for which to calculate netCDF file from RPN files.
    :type netcdf_start_date: :py:class:`arrow.Arrow`

    :param netcdf_end_date: End date for which to calculate netCDF file from RPN files.
    :type netcdf_end_date: :py:class:`arrow.Arrow`

    :param str forecast: HRDPS forecast to calculate netCDF file from; 00, 06, 12, or 18.

    :param rpn_dir: Directory tree in which GEMLAM RPN files are stored in year directories.
    :type rpn_dir: :py:class:`pathlib.Path`

    :param dest_dir: Directory in which to store GEMLAM netCDF file calculated from RPN files.
    :type dest_dir: :py:class:`pathlib.Path`

    :param str tmp_dir: Directory to use for temporary files storage for debugging.

    :param keep_rpn_fcst_hr_files: Don't delete the uncompressed RPN forecast hour files
                                   from :command:`bzip2 -d`.
                                   *This is a debugging option that is only useful in
                                   combination with the :kbd:`--tmp_dir` command-line option.*
    :type keep_rpn_fcst_hr_files: boolean

    :param bunzip2_rpn_fcst_hr_files: Uncompress RPN forecast hour files with :command:`bzip2 -d`.
                                      *This is a debugging option that is only useful in
                                      combination with the :kbd:`--tmp_dir` command-line option,
                                      and after having run with :kbd:`--keep-rpn-fcst-hr-files`.*
    :type bunzip2_rpn_fcst_hr_files: boolean
    """
    if tmp_dir:
        tmp_dir = Path(tmp_dir)
        tmp_dir.mkdir(exist_ok=True)
        _do_work(
            netcdf_end_date,
            netcdf_start_date,
            forecast,
            rpn_dir,
            dest_dir,
            tmp_dir,
            keep_rpn_fcst_hr_files,
            bunzip2_rpn_fcst_hr_files,
        )
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _do_work(
                netcdf_end_date,
                netcdf_start_date,
                forecast,
                rpn_dir,
                dest_dir,
                tmp_dir,
                keep_rpn_fcst_hr_files,
                bunzip2_rpn_fcst_hr_files,
            )


def _do_work(
    netcdf_end_date,
    netcdf_start_date,
    forecast,
    rpn_dir,
    dest_dir,
    tmp_dir,
    keep_rpn_fcst_hr_files,
    bunzip2_rpn_fcst_hr_files,
):
    _rpn_hrs_to_nemo_hrs(
        netcdf_start_date,
        netcdf_end_date,
        forecast,
        rpn_dir,
        Path(tmp_dir),
        keep_rpn_fcst_hr_files,
        bunzip2_rpn_fcst_hr_files,
    )
    _handle_missing_hr_files(netcdf_start_date, netcdf_end_date, Path(tmp_dir))
    _handle_missing_vars(netcdf_start_date, netcdf_end_date, Path(tmp_dir))
    _calc_solar_and_precip(netcdf_start_date, netcdf_end_date, dest_dir, Path(tmp_dir))
    days_range = arrow.Arrow.range("day", netcdf_start_date, netcdf_end_date)
    for netcdf_date in days_range:
        nemo_date = f"y{netcdf_date.year}m{netcdf_date.month:02d}d{netcdf_date.day:02d}"
        nemo_day_ds_path = dest_dir / f"gemlam_{nemo_date}.nc"
        bash_cmd = f"cat-hrs-to-days {nemo_day_ds_path.with_suffix('')}"
        _exec_bash_func(bash_cmd)


def _rpn_hrs_to_nemo_hrs(
    netcdf_start_date,
    netcdf_end_date,
    forecast,
    rpn_dir,
    tmp_dir,
    keep_rpn_fcst_hr_files,
    bunzip2_rpn_fcst_hr_files,
):
    """Create hour forecast files containing NEMO/FVCOM variables from RPN files.

    :param netcdf_start_date: Start date for which to calculate netCDF file from RPN files.
    :type netcdf_start_date: :py:class:`arrow.Arrow`

    :param netcdf_end_date: End date for which to calculate netCDF file from RPN files.
    :type netcdf_end_date: :py:class:`arrow.Arrow`

    :param str forecast: HRDPS forecast to calculate netCDF file from; 00, 06, 12, or 18.

    :param rpn_dir: Directory tree in which GEMLAM RPN files are stored in year directories.
    :type rpn_dir: :py:class:`pathlib.Path`

    :param tmp_dir: Temporary working directory for files created during processing.
    :type tmp_dir: :py:class:`pathlib.Path`

    :param keep_rpn_fcst_hr_files: Don't delete the uncompressed RPN forecast hour files
                                   from :command:`bzip2 -d`.
                                   *This is a debugging option that is only useful in
                                   combination with the :kbd:`--tmp_dir` command-line option.*
    :type keep_rpn_fcst_hr_files: boolean

    :param bunzip2_rpn_fcst_hr_files: Uncompress RPN forecast hour files with :command:`bzip2 -d`.
                                      *This is a debugging option that is only useful in
                                      combination with the :kbd:`--tmp_dir` command-line option,
                                      and after having run with :kbd:`--keep-rpn-fcst-hr-files`.*
    :type bunzip2_rpn_fcst_hr_files: boolean
    """
    days_range = arrow.Arrow.range(
        "day", netcdf_start_date.shift(days=-1), netcdf_end_date
    )
    for netcdf_date in days_range:
        bash_cmd = (
            f"rpn-netcdf {forecast} {netcdf_date.format('YYYY-MM-DD')} {rpn_dir} {tmp_dir} "
            f"{keep_rpn_fcst_hr_files} {bunzip2_rpn_fcst_hr_files}"
        )
        _exec_bash_func(bash_cmd)
        nemo_date = f"y{netcdf_date.year}m{netcdf_date.month:02d}d{netcdf_date.day:02d}"
        for hr in range(24 - int(forecast), 25):
            rpn_hr_ds_path = (
                tmp_dir
                / f"{netcdf_date.shift(days=-1).format('YYYYMMDD')}{forecast}_{hr:03d}.nc"
            )
            nemo_hr_ds_path = (
                tmp_dir / f"gemlam_{nemo_date}_{(hr - (24-int(forecast))):03d}.nc"
            )
            try:
                _write_nemo_hr_file(rpn_hr_ds_path, nemo_hr_ds_path)
                rpn_hr_ds_path.unlink()
            except FileNotFoundError:
                # Missing forecast hour; we'll fill it in later
                continue
        for hr in range(24 - int(forecast)):
            rpn_hr_ds_path = (
                tmp_dir
                / f"{netcdf_date.format('YYYYMMDD')}{forecast}_{(hr + 1):03d}.nc"
            )
            nemo_hr_ds_path = (
                tmp_dir / f"gemlam_{nemo_date}_{(hr + 1 + int(forecast)):03d}.nc"
            )
            try:
                _write_nemo_hr_file(rpn_hr_ds_path, nemo_hr_ds_path)
                rpn_hr_ds_path.unlink()
            except FileNotFoundError:
                # Missing forecast hour; we'll fill it in later
                continue


def _handle_missing_hr_files(netcdf_start_date, netcdf_end_date, tmp_dir):
    """Fill in missing forecast hour files by interpolation.

    :param netcdf_start_date: Start date for which to calculate netCDF file from RPN files.
    :type netcdf_start_date: :py:class:`arrow.Arrow`

    :param netcdf_end_date: End date for which to calculate netCDF file from RPN files.
    :type netcdf_end_date: :py:class:`arrow.Arrow`

    :param tmp_dir: Temporary working directory for files created during processing.
    :type tmp_dir: :py:class:`pathlib.Path`
    """
    hrs_range = arrow.Arrow.range(
        "hour", netcdf_start_date.shift(days=-1), netcdf_end_date.shift(hours=+23)
    )
    missing_hrs = []
    for netcdf_hr in hrs_range:
        nemo_date = f"y{netcdf_hr.year}m{netcdf_hr.month:02d}d{netcdf_hr.day:02d}"
        nemo_hr_ds_path = tmp_dir / f"gemlam_{nemo_date}_{netcdf_hr.hour:03d}.nc"
        if nemo_hr_ds_path.exists():
            if missing_hrs:
                if len(missing_hrs) <= 4:
                    _interpolate_intra_day_missing_hrs(missing_hrs)
                    missing_hrs = []
                else:
                    _interpolate_inter_day_missing_hrs(missing_hrs)
                    missing_hrs = []
        else:
            missing_hrs.append({"hr": netcdf_hr, "ds_path": nemo_hr_ds_path})
    if missing_hrs:
        raise FileNotFoundError(f"missing hours at end of date range: {missing_hrs}")


def _interpolate_intra_day_missing_hrs(missing_hrs):
    interp_info = _calc_intra_day_interp_info(missing_hrs)
    logging.info(
        f"interpolating missing hours between "
        f"{interp_info.prev_avail_hr_path} and {interp_info.next_avail_hr_path}"
    )
    for hrs, missing_hr in enumerate(missing_hrs, start=1):
        time_counter = interp_info.prev_avail_time_counter + hrs * 3600
        missing_nemo_date = f"y{missing_hr['hr'].year}m{missing_hr['hr'].month:02d}d{missing_hr['hr'].day:02d}"
        missing_hr_path = missing_hr["ds_path"].with_name(
            f"gemlam_{missing_nemo_date}_{missing_hr['hr'].hour:03d}.nc"
        )
        bash_cmd = (
            f"interp-for-time_counter-value {time_counter} "
            f"{interp_info.prev_avail_hr_path} {interp_info.next_avail_hr_path} {missing_hr_path}"
        )
        _exec_bash_func(bash_cmd)
        logging.info(f"created {missing_hr_path} by interpolation")


def _calc_intra_day_interp_info(missing_hrs):
    prev_avail_hr = missing_hrs[0]["hr"].shift(hours=-1)
    prev_nemo_date = (
        f"y{prev_avail_hr.year}m{prev_avail_hr.month:02d}d{prev_avail_hr.day:02d}"
    )
    prev_avail_hr_path = missing_hrs[0]["ds_path"].with_name(
        f"gemlam_{prev_nemo_date}_{prev_avail_hr.hour:03d}.nc"
    )
    with xarray.open_dataset(prev_avail_hr_path, decode_cf=False) as ds:
        missing_vars = ds.attrs.get("missing_variables")
        if missing_vars is not None:
            logging.error(
                f"this will not end well: found missing {missing_vars} variables "
                f"in previous available hour dataset during preparation to "
                f"interpolate missing hours: {prev_avail_hr_path}"
            )
            raise SystemExit(2)
        prev_avail_time_counter = int(ds.time_counter.values[0])
    next_avail_hr = missing_hrs[-1]["hr"].shift(hours=+1)
    next_nemo_date = (
        f"y{next_avail_hr.year}m{next_avail_hr.month:02d}d{next_avail_hr.day:02d}"
    )
    next_avail_hr_path = missing_hrs[0]["ds_path"].with_name(
        f"gemlam_{next_nemo_date}_{next_avail_hr.hour:03d}.nc"
    )
    with xarray.open_dataset(next_avail_hr_path) as ds:
        missing_vars = ds.attrs.get("missing_variables")
        if missing_vars is not None:
            logging.error(
                f"this will not end well: found missing {missing_vars} variables "
                f"in next available hour dataset during preparation to "
                f"interpolate missing hours: {next_avail_hr_path}"
            )
            raise SystemExit(2)
    return SimpleNamespace(
        prev_avail_hr_path=prev_avail_hr_path,
        prev_avail_time_counter=prev_avail_time_counter,
        next_avail_hr_path=next_avail_hr_path,
    )


def _interpolate_inter_day_missing_hrs(missing_hrs):
    for missing_hr in missing_hrs:
        interp_info = _calc_inter_day_interp_info(missing_hr)
        logging.info(
            f"interpolating for hour {missing_hr['hr'].hour:03d} "
            f"across days between {interp_info.prev_day_hr_path} and {interp_info.next_day_hr_path}"
        )
        for day in range((interp_info.next_day_hr - interp_info.prev_day_hr).days - 1):
            time_counter = interp_info.prev_day_time_counter + (day + 1) * 86400
            missing_nemo_date = f"y{missing_hr['hr'].year}m{missing_hr['hr'].month:02d}d{missing_hr['hr'].day:02d}"
            missing_hr_path = missing_hr["ds_path"].with_name(
                f"gemlam_{missing_nemo_date}_{missing_hr['hr'].hour:03d}.nc"
            )
            bash_cmd = (
                f"interp-for-time_counter-value {time_counter} "
                f"{interp_info.prev_day_hr_path} {interp_info.next_day_hr_path} {missing_hr_path}"
            )
            _exec_bash_func(bash_cmd)
            logging.info(f"calculated {missing_hr_path} by interpolation")


def _calc_inter_day_interp_info(missing_hr):
    prev_day_hr = missing_hr["hr"].shift(days=-1)
    prev_nemo_date = (
        f"y{prev_day_hr.year}m{prev_day_hr.month:02d}d{prev_day_hr.day:02d}"
    )
    prev_day_hr_path = missing_hr["ds_path"].with_name(
        f"gemlam_{prev_nemo_date}_{prev_day_hr.hour:03d}.nc"
    )
    with xarray.open_dataset(prev_day_hr_path, decode_cf=False) as ds:
        prev_day_time_counter = int(ds.time_counter.values[0])
    next_day_hr = missing_hr["hr"].shift(days=+1)
    next_nemo_date = (
        f"y{next_day_hr.year}m{next_day_hr.month:02d}d{next_day_hr.day:02d}"
    )
    next_day_hr_path = missing_hr["ds_path"].with_name(
        f"gemlam_{next_nemo_date}_{next_day_hr.hour:03d}.nc"
    )
    if not next_day_hr_path.exists():
        raise FileNotFoundError(
            f"can't complete inter-day interpolation due to not yet calculated "
            f"next day hour file: {next_day_hr_path}"
        )
    return SimpleNamespace(
        prev_day_hr=prev_day_hr,
        prev_day_hr_path=prev_day_hr_path,
        prev_day_time_counter=prev_day_time_counter,
        next_day_hr=next_day_hr,
        next_day_hr_path=next_day_hr_path,
    )


def _handle_missing_vars(netcdf_start_date, netcdf_end_date, tmp_dir):
    """Fill in missing RPN variables by interpolation.

    :param netcdf_start_date: Start date for which to calculate netCDF file from RPN files.
    :type netcdf_start_date: :py:class:`arrow.Arrow`

    :param netcdf_end_date: End date for which to calculate netCDF file from RPN files.
    :type netcdf_end_date: :py:class:`arrow.Arrow`

    :param tmp_dir: Temporary working directory for files created during processing.
    :type tmp_dir: :py:class:`pathlib.Path`
    """
    hrs_range = arrow.Arrow.range(
        "hour", netcdf_start_date.shift(days=-1), netcdf_end_date.shift(hours=+23)
    )
    missing_var_hrs = {}
    for netcdf_hr in hrs_range:
        nemo_date = f"y{netcdf_hr.year}m{netcdf_hr.month:02d}d{netcdf_hr.day:02d}"
        nemo_hr_ds_path = tmp_dir / f"gemlam_{nemo_date}_{netcdf_hr.hour:03d}.nc"
        with xarray.open_dataset(nemo_hr_ds_path) as ds:
            missing_vars = ds.attrs.get("missing_variables")
        if missing_vars is None:
            for var, missing_hrs in missing_var_hrs.copy().items():
                if len(missing_hrs) <= 4:
                    _interpolate_intra_day_missing_var_hrs(var, missing_hrs)
                    del missing_var_hrs[var]
                else:
                    _interpolate_inter_day_missing_var_hrs(var, missing_hrs)
                    del missing_var_hrs[var]
        else:
            for var in missing_vars.split(", "):
                try:
                    missing_var_hrs[var].append(
                        {"hr": netcdf_hr, "ds_path": nemo_hr_ds_path}
                    )
                except KeyError:
                    missing_var_hrs[var] = [
                        {"hr": netcdf_hr, "ds_path": nemo_hr_ds_path}
                    ]
    for missing_hr in missing_var_hrs.get("solar", []).copy():
        # Special handling for 1feb07 to 23feb07 period in which there are no solar radiation values
        in_feb07_solar_gap = missing_hr["hr"].is_between(
            arrow.get("2007-02-01"), arrow.get("2007-02-24"), bounds="[)"
        )
        if not in_feb07_solar_gap:
            break
        # Calculate solar radiation from cloud fraction and time of day sun angle
        solar = _calc_solar_from_clouds_and_angle(
            missing_hr["hr"], missing_hr["ds_path"]
        )
        solar = solar.astype("float32", casting="same_kind")
        solar.attrs["level"] = "surface"
        solar.attrs["long_name"] = "Downward Short-Wave Radiation Flux"
        solar.attrs["standard_name"] = "net_downward_shortwave_flux_in_air"
        solar.attrs["units"] = "W/m^2"
        with xarray.open_dataset(missing_hr["ds_path"]) as ds:
            ds_w_solar = ds.copy(deep=True).assign(solar=solar)
        missing_vars = ds_w_solar.attrs["missing_variables"].split(", ")
        missing_vars.remove("solar")
        if missing_vars:
            ds_w_solar.attrs["missing_variables"] = ", ".join(missing_vars)
        else:
            del ds_w_solar.attrs["missing_variables"]
        _write_netcdf_file(ds_w_solar, missing_hr["ds_path"])
        missing_var_hrs["solar"].remove(missing_hr)
    else:
        if "solar" in missing_var_hrs and not missing_var_hrs["solar"]:
            del missing_var_hrs["solar"]
    if missing_var_hrs:
        raise ValueError(f"missing variables at end of date range: {missing_var_hrs}")


def _interpolate_intra_day_missing_var_hrs(var, missing_hrs):
    interp_info = _calc_intra_day_interp_info(missing_hrs)
    logging.info(
        f"interpolating {var} for missing hour(s) between "
        f"{interp_info.prev_avail_hr_path} and {interp_info.next_avail_hr_path}"
    )
    for hrs, missing_hr in enumerate(missing_hrs, start=1):
        time_counter = interp_info.prev_avail_time_counter + hrs * 3600
        missing_nemo_date = f"y{missing_hr['hr'].year}m{missing_hr['hr'].month:02d}d{missing_hr['hr'].day:02d}"
        missing_hr_path = missing_hr["ds_path"].with_name(
            f"gemlam_{missing_nemo_date}_{missing_hr['hr'].hour:03d}.nc"
        )
        bash_cmd = (
            f"interp-var-for-time_counter-value {var} {time_counter} "
            f"{interp_info.prev_avail_hr_path} {interp_info.next_avail_hr_path} {missing_hr_path}"
        )
        _exec_bash_func(bash_cmd)
        logging.info(f"calculated {var} for {missing_hr_path} by interpolation")


def _interpolate_inter_day_missing_var_hrs(var, missing_hrs):
    for missing_hr in missing_hrs:
        interp_info = _calc_inter_day_interp_info(missing_hr)
        logging.info(
            f"interpolating {var} for hour {missing_hr['hr'].hour:03d} "
            f"across days between {interp_info.prev_day_hr_path} and {interp_info.next_day_hr_path}"
        )
        for day in range((interp_info.next_day_hr - interp_info.prev_day_hr).days - 1):
            time_counter = interp_info.prev_day_time_counter + (day + 1) * 86400
            missing_nemo_date = f"y{missing_hr['hr'].year}m{missing_hr['hr'].month:02d}d{missing_hr['hr'].day:02d}"
            missing_hr_path = missing_hr["ds_path"].with_name(
                f"gemlam_{missing_nemo_date}_{missing_hr['hr'].hour:03d}.nc"
            )
            bash_cmd = (
                f"interp-var-for-time_counter-value {var} {time_counter} "
                f"{interp_info.prev_day_hr_path} {interp_info.next_day_hr_path} {missing_hr_path}"
            )
            _exec_bash_func(bash_cmd)
            logging.info(f"calculated {var} for {missing_hr_path} by interpolation")


def _calc_solar_from_clouds_and_angle(hr, ds_path):
    """Calculate solar radiation from cloud fraction and time of day sun angle.
    """
    # Solar radiation [W/m^2] incident on top of atmosphere
    Q_o = 1368.0
    # Cloud model based on Dobson and Smith, table 5
    #   SEA -- May 2010 : redid the cloud parametrization based on UBC
    #   Solar data (/ocean/shared/SoG/met/solar/) fitting Q to cos_Z
    #   (not Q/cos_Z as Kate did).  Allen and Wolfe (2013).  (0) no
    #   clouds, (1) 1/10 cloud fraction (10) 100% clouds.  Four sig
    #   figs are what comes out of matlab but standard deviations are
    #   40W/m2 for low cloud fraction to 120 W/m2 for 6-9 cloud
    #   fraction to 85 W/m2 for completely cloudy.
    cloud_consts = SimpleNamespace(
        A=numpy.array(
            [
                0.6337,
                0.6149,
                0.5861,
                0.5512,
                0.5002,
                0.4649,
                0.4225,
                0.3669,
                0.2468,
                0.1981,
                0.0841,
            ]
        ),
        B=numpy.array(
            [
                0.1959,
                0.2119,
                0.2400,
                0.2859,
                0.3192,
                0.3356,
                0.3339,
                0.3490,
                0.4427,
                0.3116,
                0.2283,
            ]
        ),
    )
    # Local standard time
    ## WARNING: .to("PST") may be fragile and incorrect for summer-time dates
    lst = hr.to("PST")
    # day_time is in seconds, LST
    day_time = (lst - lst.floor("day")).seconds
    # hour of day as degrees from noon
    hour = (day_time / 3600 - 12) * 15
    # day is year-day
    day = (lst - lst.floor("year")).days
    # solar declination [radians]
    declination = (
        23.45 * numpy.pi / 180 * numpy.sin((284 + day) / 365.25 * 2 * numpy.pi)
    )
    # Latitude of approximate centre of model domain in radians
    lat = numpy.pi * 50 / 180
    # solar elevation
    elev_sin = numpy.sin(declination) * numpy.sin(lat)
    elev_cos = numpy.cos(declination) * numpy.cos(lat)
    cos_Z = elev_sin + elev_cos * numpy.cos(numpy.pi / 180 * hour)
    # cos of -hour_angle in radians
    hour_angle = numpy.tan(lat) * numpy.tan(declination)
    # assume we are south of the Arctic Circle
    day_length = numpy.arccos(-hour_angle) / 15 * 2 * 180 / numpy.pi
    sunrise = 12 - 0.5 * day_length  # hours
    sunset = 12 + 0.5 * day_length  # hours
    Qso = Q_o * (1 + 0.033 * numpy.cos(day / 365.25 * 2 * numpy.pi))
    with xarray.open_dataset(ds_path) as ds:
        cf_value = ds.percentcloud * 10
        fcf = numpy.floor(cf_value).astype(int)  # integer below cf value
        fcf = xarray.where(fcf == 10, 9, fcf).data
        ccf = fcf + 1  # integer above cf value
        if (sunrise > day_time / 3600) or (day_time / 3600 > sunset):
            # nighttime
            return xarray.zeros_like(ds.percentcloud)
        return (
            Qso
            * (
                cloud_consts.A[fcf] * (ccf - cf_value)
                + cloud_consts.A[ccf] * (cf_value - fcf)
                + (
                    cloud_consts.B[fcf] * (ccf - cf_value)
                    + cloud_consts.B[ccf] * (cf_value - fcf)
                )
                * cos_Z
            )
            * cos_Z
        )


def _calc_solar_and_precip(netcdf_start_date, netcdf_end_date, dest_dir, tmp_dir):
    """Calculate solar radiation and precipitation flux for each forecast hour.

    Solar radiation is average of instantaneous values from RPN from hour and preceding hour.
    Precipitation flux is calculated by hour to hour differences from RPN accumulated precipitation.

    :param netcdf_start_date: Start date for which to calculate netCDF file from RPN files.
    :type netcdf_start_date: :py:class:`arrow.Arrow`

    :param netcdf_end_date: End date for which to calculate netCDF file from RPN files.
    :type netcdf_end_date: :py:class:`arrow.Arrow`

    :param dest_dir: Directory in which to store GEMLAM netCDF file calculated from RPN files.
    :type dest_dir: :py:class:`pathlib.Path`

    :param tmp_dir: Temporary working directory for files created during processing.
    :type tmp_dir: :py:class:`pathlib.Path`
    """
    hrs_range = arrow.Arrow.range(
        "hour", netcdf_start_date, netcdf_end_date.shift(hours=+23)
    )
    for netcdf_hr in hrs_range:
        prev_hr = netcdf_hr.shift(hours=-1)
        prev_nemo_date = f"y{prev_hr.year}m{prev_hr.month:02d}d{prev_hr.day:02d}"
        prev_nemo_hr_ds_path = (
            tmp_dir / f"gemlam_{prev_nemo_date}_{prev_hr.hour:03d}.nc"
        )
        nemo_date = f"y{netcdf_hr.year}m{netcdf_hr.month:02d}d{netcdf_hr.day:02d}"
        nemo_hr_ds_path = tmp_dir / f"gemlam_{nemo_date}_{netcdf_hr.hour:03d}.nc"
        nemo_hr_ds_dest = dest_dir / nemo_hr_ds_path.name
        shutil.copy2(nemo_hr_ds_path, nemo_hr_ds_dest)
        bash_cmd = (
            f"avg-diff-hrs {prev_nemo_hr_ds_path} {nemo_hr_ds_path} {nemo_hr_ds_dest}"
        )
        _exec_bash_func(bash_cmd)


def _write_nemo_hr_file(rpn_hr_ds_path, nemo_hr_ds_path):
    """Write forecast hour file with file name and variable names expected by NEMO and FVCOM.

    File includes variables from GEMLAM RPN as well as calculated variables.
    Calculated variables are:

    * specific humidity 2m above surface
    * relative humidity 2m above surface
    * incoming longwave radiation at surface
    * TODO: latent heat flux at surface

    :param :py:class:`pathlib.Path` rpn_hr_ds_path: File path of forecast hour from RPN file.

    :param :py:class:`pathlib.Path` nemo_hr_ds_path: File path of forecast hour file with NEMO
                                                     variable names and file name.
    """
    with xarray.open_dataset(rpn_hr_ds_path) as rpn_hr:
        logging.debug(
            f"calculating specific humidity & incoming longwave radiation from {rpn_hr_ds_path}"
        )
        qair, ilwr, rh = _calc_qair_ilwr(rpn_hr)
        u_out, v_out = _rotate_winds(rpn_hr)
        data_vars = {
            "nav_lon": rpn_hr.nav_lon,
            "nav_lat": rpn_hr.nav_lat,
            # [:, 0] drops z dimension that NEMO will not tolerate
            "qair": qair[:, 0],
            "RH_2maboveground": rh[:, 0],
            "therm_rad": ilwr[:, 0],
            "u_wind": u_out[:, 0],
            "v_wind": v_out[:, 0],
            # "LHTFL_surface": ** needs to be calculated**,
        }
        nemo_rpn_vars = (
            ("atmpres", "PN"),
            ("percentcloud", "NT"),
            ("PRATE_surface", "RT"),
            ("precip", "PR"),
            ("solar", "FB"),
            ("tair", "TT"),
        )
        missing_vars = ""
        for nemo_var, rpn_var in nemo_rpn_vars:
            try:
                # [:, 0] drops z dimension that NEMO will not tolerate
                data_vars.update({nemo_var: getattr(rpn_hr, rpn_var)[:, 0]})
            except AttributeError:
                # Variable is missing from RPN dataset, so provide a placeholder DataArray
                # full of NaNs that we will deal with later via interpolation
                data_vars.update(
                    {nemo_var: xarray.DataArray(numpy.full_like(qair[:, 0], numpy.nan))}
                )
                missing_vars = (
                    ", ".join((missing_vars, nemo_var)) if missing_vars else nemo_var
                )
                logging.warning(f"missing RPN variable {rpn_var} from {rpn_hr_ds_path}")
        nemo_hr = xarray.Dataset(
            data_vars=data_vars, coords=rpn_hr.coords, attrs=rpn_hr.attrs
        )
        nemo_hr.attrs["history"] += (
            f"\n{arrow.now().format('ddd MMM DD HH:mm:ss YYYY')}: "
            f"Add specific and relative humidity and incoming longwave radiation variables from "
            f"correlations"
        )
        if missing_vars:
            nemo_hr.attrs["missing_variables"] = missing_vars
        _add_vars_metadata(nemo_hr)
        _write_netcdf_file(nemo_hr, nemo_hr_ds_path)


def _write_netcdf_file(dataset, dataset_path):
    encoding = {
        "time_counter": {"dtype": "float", "units": "seconds since 1950-01-01 00:00:00"}
    }
    dataset.to_netcdf(dataset_path, encoding=encoding, unlimited_dims=("time_counter",))


def _calc_qair_ilwr(rpn_hr):
    """Calculate specific humidity and incoming longwave radiation data arrays for a
    forecast hour dataset.

    :param :py:class:`xarray.Dataset` rpn_hr: Forecast hour dataset.

    :returns: Specific humidity, relative humidity Incoming longwave radiation data arrrays
    :rtype: 3-tuple of :py:class:`xarray.DataArray`
    """
    # saturation water vapour at the dew point in the pure phase
    # which within 0.5% is that of moist air
    ew = 6.112 * numpy.exp(17.62 * rpn_hr.TD / (243.12 + rpn_hr.TD))
    xvw = ew / (0.01 * rpn_hr.PN)  # converting P to hectopascals
    r = 0.62198 * xvw / (1 - xvw)  # as at Td r = rw
    qair = xarray.DataArray(r / (1 + r))
    # saturation water vapour at the current temperature in the pure phase
    TT = rpn_hr.TT - 273.15  # change temperature back to Celcius
    eT = 6.112 * numpy.exp(17.62 * TT / (243.12 + TT))
    rh = 100 * (ew / eT)

    ew = ew / 10.0  # Change vapour pressure to from hecto pascal to kPa
    w = 465 * ew / rpn_hr.TT
    Lclr = (
        59.38 + 113.7 * (rpn_hr.TT / 273.16) ** 6 + 96.96 * numpy.sqrt(w / 2.5)
    )  # Dilley
    # Unsworth
    sigma = 5.6697e-8
    eclr = Lclr / (sigma * rpn_hr.TT ** 4)
    ewc = (1 - 0.84 * rpn_hr.NT) * eclr + 0.84 * rpn_hr.NT
    ilwr = xarray.DataArray(ewc * sigma * rpn_hr.TT ** 4)

    return qair, ilwr, rh


def _rotate_winds(rpn_hr):
    """Rotate winds to true north, east

    :param :py:class:`xarray.Dataset' rpn_hr: Foreast hour dataset.

    :returns: uwind, vwind data arrrays
    :rtype: 2-tuple of :py:class:`xarray.DataArray`
    """
    coords = {"lon": rpn_hr.nav_lon, "lat": rpn_hr.nav_lat}
    u_out, v_out = viz_tools.rotate_vel_bybearing(
        rpn_hr.UU, rpn_hr.VV, coords, origin="grid"
    )

    return u_out, v_out


def _add_vars_metadata(nemo_hr):
    """Add metadata to variables that will be stored in final netCDF file.

    :param :py:class:`xarray.Dataset` nemo_hr: Forecast hour dataset.
    """
    nemo_hr.atmpres.attrs["level"] = "mean sea level"
    nemo_hr.atmpres.attrs["long_name"] = "Pressure Reduced to MSL"
    nemo_hr.atmpres.attrs["standard_name"] = "air_pressure_at_sea_level"
    nemo_hr.atmpres.attrs["units"] = "Pa"

    # nemo_hr.LHTFL_surface.attrs["level"] = "surface"
    # nemo_hr.LHTFL_surface.attrs["long_name"] = ""
    # nemo_hr.LHTFL_surface.attrs["standard_name"] = ""
    # nemo_hr.LHTFL_surface.attrs["units"] = ""
    # nemo_hr.LHTFL_surface.attrs["ioos_category"] = ""
    # nemo_hr.LHTFL_surface.attrs["comment"] = "how calculated"

    nemo_hr.percentcloud.attrs["long_name"] = "Cloud Fraction"
    nemo_hr.percentcloud.attrs["standard_name"] = "cloud_area_fraction"
    nemo_hr.percentcloud.attrs["units"] = "percent"

    nemo_hr.PRATE_surface.attrs["level"] = "surface"
    nemo_hr.PRATE_surface.attrs["long_name"] = "Precipitation Rate"
    nemo_hr.PRATE_surface.attrs["standard_name"] = "precipitation_flux"
    nemo_hr.PRATE_surface.attrs["units"] = "kg/m^2/s"

    nemo_hr.nav_lat.attrs["ioos_category"] = "location"

    nemo_hr.nav_lon.attrs["ioos_category"] = "location"

    nemo_hr.precip.attrs["level"] = "surface"
    nemo_hr.precip.attrs["long_name"] = "Total Precipitation"
    nemo_hr.precip.attrs["standard_name"] = "precipitation_flux"
    nemo_hr.precip.attrs["units"] = "kg/m^2/s"

    nemo_hr.qair.attrs["level"] = "2 m above surface"
    nemo_hr.qair.attrs["long_name"] = "Specific Humidity"
    nemo_hr.qair.attrs["standard_name"] = "specific_humidity_2maboveground"
    nemo_hr.qair.attrs["units"] = "kg/kg"
    nemo_hr.qair.attrs[
        "comment"
    ] = "calculated from sea level air pressure and dewpoint temperature via WMO 2012 ocean best practices"

    nemo_hr.RH_2maboveground.attrs["level"] = "2 m above surface"
    nemo_hr.RH_2maboveground.attrs["long_name"] = "Relative Humidity"
    nemo_hr.RH_2maboveground.attrs["standard_name"] = "relative_humidity_2maboveground"
    nemo_hr.RH_2maboveground.attrs["units"] = "percent"
    nemo_hr.RH_2maboveground.attrs[
        "comment"
    ] = "calculated from air temperature and dewpoint temperature via WMO 2012 ocean best practices"

    nemo_hr.solar.attrs["level"] = "surface"
    nemo_hr.solar.attrs["long_name"] = "Downward Short-Wave Radiation Flux"
    nemo_hr.solar.attrs["standard_name"] = "net_downward_shortwave_flux_in_air"
    nemo_hr.solar.attrs["units"] = "W/m^2"

    nemo_hr.tair.attrs["level"] = "2 m above surface"
    nemo_hr.tair.attrs["long_name"] = "Air Temperature"
    nemo_hr.tair.attrs["standard_name"] = "air_temperature_2maboveground"
    nemo_hr.tair.attrs["units"] = "K"

    nemo_hr.therm_rad.attrs["level"] = "surface"
    nemo_hr.therm_rad.attrs["long_name"] = "Downward Long-Wave Radiation Flux"
    nemo_hr.therm_rad.attrs["standard_name"] = "net_downward_longwave_flux_in_air"
    nemo_hr.therm_rad.attrs["units"] = "W/m^2"
    nemo_hr.therm_rad.attrs["comment"] = (
        "calculated from saturation water vapour pressure, air temperature, and cloud fraction "
        "via Dilly-Unsworth correlation"
    )

    nemo_hr.u_wind.attrs["level"] = "10 m above surface"
    nemo_hr.u_wind.attrs["long_name"] = "U-Component of Wind"
    nemo_hr.u_wind.attrs["standard_name"] = "x_wind"
    nemo_hr.u_wind.attrs["units"] = "m/s"
    nemo_hr.u_wind.attrs["ioos_category"] = "wind speed and direction"

    nemo_hr.v_wind.attrs["level"] = "10 m above surface"
    nemo_hr.v_wind.attrs["long_name"] = "V-Component of Wind"
    nemo_hr.v_wind.attrs["standard_name"] = "y_wind"
    nemo_hr.v_wind.attrs["units"] = "m/s"
    nemo_hr.v_wind.attrs["ioos_category"] = "wind speed and direction"

    nemo_hr.attrs[
        "history"
    ] += f"\n{arrow.now().format('ddd MMM DD HH:mm:ss YYYY')}: Add data variables metadata"


def _exec_bash_func(bash_cmd):
    """Execute bash function from :file:`rpn_netcdf.sh` in a subprocess.

    :file:`rpn_netcdf.sh` is sourced before :kbd:`bash_cmd` to bring functions defintions
    into environment.

    Bash command that is being executed and its output are logged to stdout at the DEBUG level.

    :param str bash_cmd: Bash function and arguments to execute.
    """
    rpn_netcdf_sh = Path(__file__).with_name("rpn_netcdf.sh")
    cmd = f"bash -c {shlex.quote(f'source {rpn_netcdf_sh}; {bash_cmd}')}"
    logging.info(f"executing: {cmd}")
    proc = subprocess.run(
        shlex.split(cmd),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    logging.debug(proc.stdout)


@click.command(help=rpn_to_gemlam.__doc__)
@click.version_option()
@click.argument("netcdf_start_date", type=click.DateTime(formats=("%Y-%m-%d",)))
@click.argument("netcdf_end_date", type=click.DateTime(formats=("%Y-%m-%d",)))
@click.argument("forecast", type=click.Choice(("00", "06", "12", "18")))
@click.argument("rpn_dir", type=click.Path(exists=True))
@click.argument("dest_dir", type=click.Path(writable=True))
@click.option(
    "-v",
    "--verbosity",
    default="warning",
    show_default=True,
    type=click.Choice(("debug", "info", "warning", "error", "critical")),
    help="""
        Choose how much information you want to see about the progress of the process;
        warning, error, and critical should be silent unless something bad goes wrong.
    """,
)
@click.option(
    "--tmp_dir",
    default="",
    show_default=True,
    help="""
        Absolute path of directory to use for temporary files storage for debugging
    """,
)
@click.option(
    "--keep-rpn-fcst-hr-files/--no-keep-rpn-fcst-hr-files",
    default=False,
    show_default=True,
    help="""
        Don't delete the uncompressed RPN forecast hour files from :command:`bzip2 -d`. *This 
        is a debugging option that is only useful in combination with the :kbd:`--tmp_dir` 
        command-line option.*
    """,
)
@click.option(
    "--bunzip2-rpn-fcst-hr-files/--no-bunzip2-rpn-fcst-hr-files",
    default=True,
    show_default=True,
    help="""
        Uncompress RPN forecast hour files with :command:`bzip2 -d`. *This is a debugging 
        option that is only useful in combination with the :kbd:`--tmp_dir` command-line 
        option, and after having run with :kbd:`--keep-rpn-fcst-hr-files`.*
    """,
)
def cli(
    netcdf_start_date,
    netcdf_end_date,
    forecast,
    rpn_dir,
    dest_dir,
    verbosity,
    tmp_dir,
    keep_rpn_fcst_hr_files,
    bunzip2_rpn_fcst_hr_files,
):
    """Command-line interface for :py:func:`rpn_to_gemlam.rpn_to_gemlam`.

    Please see:

      rpn-to-gemlam --help

    :param netcdf_start_date: Start date for which to calculate netCDF file from RPN files.
    :type netcdf_start_date: :py:class:`datetime.datetime`

    :param netcdf_end_date: End date for which to calculate netCDF file from RPN files.
    :type netcdf_end_date: :py:class:`datetime.datetime`

    :param str forecast: HRDPS forecast to calculate netCDF file from; 00, 06, 12, or 18.

    :param rpn_dir: Directory tree in which GEMLAM RPN files are stored in year directories.
    :type rpn_dir: :py:class:`pathlib.Path`

    :param dest_dir: Directory in which to store GEMLAM netCDF file calculated from RPN files.
    :type dest_dir: :py:class:`pathlib.Path`

    :param str verbosity: Verbosity level of logging messages about the progress of the
                          process.
                          Choices are :kbd:`debug, info, warning, error, critical`.
                          :kbd:`warning`, :kbd:`error`, and :kbd:`critical` should be silent
                          unless something bad goes wrong.
                          Default is :kbd:`warning`.

    :param str tmp_dir: Directory to use for temporary files storage for debugging.

    :param keep_rpn_fcst_hr_files: Don't delete the uncompressed RPN forecast hour files
                                   from :command:`bzip2 -d`.
                                   *This is a debugging option that is only useful in
                                   combination with the :kbd:`--tmp_dir` command-line option.*
    :type keep_rpn_fcst_hr_files: boolean

    :param bunzip2_rpn_fcst_hr_files: Uncompress RPN forecast hour files with :command:`bzip2 -d`.
                                      *This is a debugging option that is only useful in
                                      combination with the :kbd:`--tmp_dir` command-line option,
                                      and after having run with :kbd:`--keep-rpn-fcst-hr-files`.*
    :type bunzip2_rpn_fcst_hr_files: boolean
    """
    logging_level = getattr(logging, verbosity.upper())
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s rpn-to-gemlam %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    rpn_to_gemlam(
        arrow.get(netcdf_start_date),
        arrow.get(netcdf_end_date),
        forecast,
        Path(rpn_dir),
        Path(dest_dir),
        tmp_dir,
        keep_rpn_fcst_hr_files,
        bunzip2_rpn_fcst_hr_files,
    )
