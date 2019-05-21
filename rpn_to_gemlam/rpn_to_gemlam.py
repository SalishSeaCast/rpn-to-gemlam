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

import arrow
import click
import numpy
import xarray

from salishsea_tools import viz_tools

logging.getLogger(__name__).addHandler(logging.NullHandler())


def rpn_to_gemlam(netcdf_start_date, netcdf_end_date, rpn_dir, dest_dir):
    """Generate an atmospheric forcing file for the SalishSeaCast NEMO model
    from the ECCC 2007-2014 archival GEMLAM files produced by the experimental
    phase of the HRPDS model.
    \f
    :param netcdf_start_date: Start date for which to calculate netCDF file from RPN files.
    :type netcdf_start_date: :py:class:`arrow.Arrow`

    :param netcdf_end_date: End date for which to calculate netCDF file from RPN files.
    :type netcdf_end_date: :py:class:`arrow.Arrow`

    :param rpn_dir: Directory tree in which GEMLAM RPN files are stored in year directories.
    :type rpn_dir: :py:class:`pathlib.Path`

    :param dest_dir: Directory in which to store GEMLAM netCDF file calculated from RPN files.
    :type dest_dir: :py:class:`pathlib.Path`
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        _rpn_hrs_to_nemo_hrs(netcdf_start_date, netcdf_end_date, rpn_dir, Path(tmp_dir))
        _handle_missing_hr_files(netcdf_end_date, netcdf_start_date, Path(tmp_dir))
        _calc_solar_and_precip(
            netcdf_start_date, netcdf_end_date, dest_dir, Path(tmp_dir)
        )
        days_range = arrow.Arrow.range("day", netcdf_start_date, netcdf_end_date)
        for netcdf_date in days_range:
            nemo_date = (
                f"y{netcdf_date.year}m{netcdf_date.month:02d}d{netcdf_date.day:02d}"
            )
            nemo_day_ds_path = dest_dir / f"gemlam_{nemo_date}.nc"
            bash_cmd = f"cat-hrs-to-days {nemo_day_ds_path.stem}"
            _exec_bash_func(bash_cmd)


def _rpn_hrs_to_nemo_hrs(netcdf_start_date, netcdf_end_date, rpn_dir, tmp_dir):
    """Create hour forecast files containing NEMO/FVCOM variables from RPN files.

    :param netcdf_start_date: Start date for which to calculate netCDF file from RPN files.
    :type netcdf_start_date: :py:class:`arrow.Arrow`

    :param netcdf_end_date: End date for which to calculate netCDF file from RPN files.
    :type netcdf_end_date: :py:class:`arrow.Arrow`

    :param rpn_dir: Directory tree in which GEMLAM RPN files are stored in year directories.
    :type rpn_dir: :py:class:`pathlib.Path`

    :param tmp_dir: Temporary working directory for files created during processing.
    :type tmp_dir: :py:class:`pathlib.Path`
    """
    days_range = arrow.Arrow.range(
        "day", netcdf_start_date.shift(days=-1), netcdf_end_date
    )
    for netcdf_date in days_range:
        bash_cmd = f"rpn-netcdf {netcdf_date.format('YYYY-MM-DD')} {rpn_dir} {tmp_dir}"
        _exec_bash_func(bash_cmd)
        nemo_date = f"y{netcdf_date.year}m{netcdf_date.month:02d}d{netcdf_date.day:02d}"
        for hr in range(18, 25):
            rpn_hr_ds_path = (
                tmp_dir
                / f"{netcdf_date.shift(days=-1).format('YYYYMMDD')}06_{(hr):03d}.nc"
            )
            nemo_hr_ds_path = tmp_dir / f"gemlam_{nemo_date}_{(hr - 18):03d}.nc"
            try:
                _write_nemo_hr_file(rpn_hr_ds_path, nemo_hr_ds_path)
                rpn_hr_ds_path.unlink()
            except FileNotFoundError:
                # Missing forecast hour; we'll fill it in later
                continue
        for hr in range(18):
            rpn_hr_ds_path = (
                tmp_dir / f"{netcdf_date.format('YYYYMMDD')}06_{(hr + 1):03d}.nc"
            )
            nemo_hr_ds_path = tmp_dir / f"gemlam_{nemo_date}_{(hr + 1 + 6):03d}.nc"
            try:
                _write_nemo_hr_file(rpn_hr_ds_path, nemo_hr_ds_path)
                rpn_hr_ds_path.unlink()
            except FileNotFoundError:
                # Missing forecast hour; we'll fill it in later
                continue


def _handle_missing_hr_files(netcdf_end_date, netcdf_start_date, tmp_dir):
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
    for netcdf_hr in hrs_range:
        nemo_date = f"y{netcdf_hr.year}m{netcdf_hr.month:02d}d{netcdf_hr.day:02d}"
        nemo_hr_ds_path = tmp_dir / f"gemlam_{nemo_date}_{netcdf_hr.hour:03d}.nc"
        if not nemo_hr_ds_path.exists():
            raise FileNotFoundError(f"missing {nemo_hr_ds_path}")


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
        nemo_hr = xarray.Dataset(
            data_vars={
                # [:, 0] drops z dimension that NEMO will not tolerate
                "atmpres": rpn_hr.PN[:, 0],
                # "LHTFL_surface":   ** needs to be calculated**
                "percentcloud": rpn_hr.NT[:, 0],
                "PRATE_surface": rpn_hr.RT[:, 0],
                "nav_lat": rpn_hr.nav_lat,
                "nav_lon": rpn_hr.nav_lon,
                "precip": rpn_hr.PR[:, 0],
                "qair": qair[:, 0],
                "RH_2maboveground": rh[:, 0],
                "solar": rpn_hr.FB[:, 0],
                "tair": rpn_hr.TT[:, 0],
                "therm_rad": ilwr[:, 0],
                "u_wind": u_out[:, 0],
                "v_wind": v_out[:, 0],
            },
            coords=rpn_hr.coords,
            attrs=rpn_hr.attrs,
        )
        nemo_hr.attrs["history"] += (
            f"\n{arrow.now().format('ddd MMM DD HH:mm:ss YYYY')}: "
            f"Add specific and relative humidity and incoming longwave radiation variables from "
            f"correlations"
        )
        _add_vars_metadata(nemo_hr)
        encoding = {
            "time_counter": {
                "dtype": "float",
                "units": "seconds since 1950-01-01 00:00:00",
            }
        }
        nemo_hr.to_netcdf(
            nemo_hr_ds_path, encoding=encoding, unlimited_dims=("time_counter",)
        )


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
@click.argument("netcdf_start_date", type=click.DateTime(formats=("%Y-%m-%d",)))
@click.argument("netcdf_end_date", type=click.DateTime(formats=("%Y-%m-%d",)))
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
def cli(netcdf_start_date, netcdf_end_date, rpn_dir, dest_dir, verbosity):
    """Command-line interface for :py:func:`rpn_to_gemlam.rpn_to_gemlam`.

    Please see:

      rpn-to-gemlam --help

    :param netcdf_start_date: Start date for which to calculate netCDF file from RPN files.
    :type netcdf_start_date: :py:class:`datetime.datetime`

    :param netcdf_end_date: End date for which to calculate netCDF file from RPN files.
    :type netcdf_end_date: :py:class:`datetime.datetime`

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
        Path(rpn_dir),
        Path(dest_dir),
    )
