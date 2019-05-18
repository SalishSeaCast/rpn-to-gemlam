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
import shlex
import subprocess
import sys
from pathlib import Path

import arrow
import click
import numpy
import xarray

logging.getLogger(__name__).addHandler(logging.NullHandler())


def rpn_to_gemlam(netcdf_date, rpn_dir, dest_dir):
    """Generate an atmospheric forcing file for the SalishSeaCast NEMO model
    from the ECCC 2007-2014 archival GEMLAM files produced by the experimental
    phase of the HRPDS model.
    \f
    :param netcdf_date: Date for which to calculate netCDF file from RPN files.
    :type netcdf_date: :py:class:`arrow.Arrow`

    :param rpn_dir: Directory tree in which GEMLAM RPN files are stored in year directories.
    :type rpn_dir: :py:class:`pathlib.Path`

    :param dest_dir: Directory in which to store GEMLAM netCDF file calculated from RPN files.
    :type dest_dir: :py:class:`pathlib.Path`
    """
    tmp_dir = Path("/data/dlatorne/tmp-rpn-to-gem-lam")
    tmp_dir.mkdir(exist_ok=True)

    bash_cmd = (
        f"rpn-netcdf {netcdf_date.format('YYYY-MM-DD')} {rpn_dir} {tmp_dir} {dest_dir}"
    )
    _exec_bash_func(bash_cmd)
    nemo_date = f"y{netcdf_date.year}m{netcdf_date.month:02d}d{netcdf_date.day:02d}"
    for hr in range(18, 25):
        hr_ds_path = (
            tmp_dir / f"{netcdf_date.shift(days=-1).format('YYYYMMDD')}06_{(hr):03d}.nc"
        )
        nemo_hr_ds_path = tmp_dir / f"gemlam_{nemo_date}_{(hr - 18):03d}.nc"
        try:
            _write_nemo_hr_file(hr_ds_path, nemo_hr_ds_path)
        except FileNotFoundError:
            # Missing forecast hour; we'll fill it in later
            continue
    for hr in range(18):
        hr_ds_path = tmp_dir / f"{netcdf_date.format('YYYYMMDD')}06_{(hr + 1):03d}.nc"
        nemo_hr_ds_path = tmp_dir / f"gemlam_{nemo_date}_{(hr + 1 + 6):03d}.nc"
        try:
            _write_nemo_hr_file(hr_ds_path, nemo_hr_ds_path)
        except FileNotFoundError:
            # Missing forecast hour; we'll fill it in later
            continue


def _write_nemo_hr_file(hr_ds_path, nemo_hr_ds_path):
    """Write forecast hour file with file name and variable names expected by NEMO and FVCOM.

    File includes variables from GEMLAM RPN as well as calculated variables.
    Calculated variables are:

    * specific humidity 2m above surface
    * relative humidity 2m above surface
    * incoming longwave radiation at surface
    * TODO: latent heat flux at surface

    :param :py:class:`pathlib.Path` hr_ds_path: File path of forecast hour from RPN file.

    :param :py:class:`pathlib.Path` nemo_hr_ds_path: File path of forecast hour file with NEMO
                                                     variable names and file name.
    """
    with xarray.open_dataset(hr_ds_path) as ds_hr:
        logging.debug(
            f"calculating specific humidity & incoming longwave radiation from {hr_ds_path}"
        )
        qair, ilwr, rh = _calc_qair_ilwr(ds_hr)
        ds_hr_ext = xarray.Dataset(
            data_vars={
                "atmpres": ds_hr.PN,
                # "LHTFL_surface":   ** needs to be calculated**
                "percentcloud": ds_hr.NT,
                "PRATE_surface": ds_hr.RT,
                "nav_lat": ds_hr.nav_lat,
                "nav_lon": ds_hr.nav_lon,
                "precip": ds_hr.PN,
                "qair": qair,
                "RH_2maboveground": rh,
                "solar": ds_hr.FB,
                "tair": ds_hr.TT,
                "therm_rad": ilwr,
                "u_wind": ds_hr.UU,
                "v_wind": ds_hr.VV,
            },
            coords=ds_hr.coords,
            attrs=ds_hr.attrs,
        )
        ds_hr_ext.attrs["history"] += (
            f"\n{arrow.now().format('ddd MMM DD HH:mm:ss YYYY')}: "
            f"Add specific and relative humidity and incoming longwave radiation variables from "
            f"correlations"
        )
        _add_vars_metadata(ds_hr_ext)
        encoding = {
            "time_counter": {
                "dtype": "float",
                "units": "seconds since 1950-01-01 00:00:00",
            }
        }
        ds_hr_ext.to_netcdf(
            nemo_hr_ds_path, encoding=encoding, unlimited_dims=("time_counter",)
        )


def _calc_qair_ilwr(ds_hr):
    """Calculate specific humidity and incoming longwave radiation data arrays for a
    forecast hour dataset.

    :param :py:class:`xarray.Dataset` ds_hr: Forecast hour dataset.

    :returns: Specific humidity, Incoming longwave radiation data arrrays
    :rtype: 2-tuple of :py:class:`xarray.DataArray`
    """
    # saturation water vapour at the dew point in the pure phase
    # which within 0.5% is that of moist air
    ew = 6.112 * numpy.exp(17.62 * ds_hr.TD / (243.12 + ds_hr.TD))
    xvw = ew / (0.01 * ds_hr.PN)  # converting P to hectopascals
    r = 0.62198 * xvw / (1 - xvw)  # as at Td r = rw
    qair = xarray.DataArray(r / (1 + r))
    # saturation water vapour at the current temperature in the pure phase
    TT = ds_hr.TT - 273.15  # change temperature back to Celcius
    eT = 6.112 * numpy.exp(17.62 * TT / (243.12 + TT))
    rh = 100 * (ew / eT)

    ew = ew / 10.0  # Change vapour pressure to from hecto pascal to kPa
    w = 465 * ew / ds_hr.TT
    Lclr = (
        59.38 + 113.7 * (ds_hr.TT / 273.16) ** 6 + 96.96 * numpy.sqrt(w / 2.5)
    )  # Dilley
    # Unsworth
    sigma = 5.6697e-8
    eclr = Lclr / (sigma * ds_hr.TT ** 4)
    ewc = (1 - 0.84 * ds_hr.NT) * eclr + 0.84 * ds_hr.NT
    ilwr = xarray.DataArray(ewc * sigma * ds_hr.TT ** 4)

    return qair, ilwr, rh


def _add_vars_metadata(ds_hr):
    """Add metadata to variables that will be stored in final netCDF file.

    :param :py:class:`xarray.Dataset` ds_hr: Forecast hour dataset.
    """
    ds_hr.atmpres.attrs["level"] = "mean sea level"
    ds_hr.atmpres.attrs["long_name"] = "Pressure Reduced to MSL"
    ds_hr.atmpres.attrs["standard_name"] = "air_pressure_at_sea_level"
    ds_hr.atmpres.attrs["units"] = "Pa"

    # ds_hr.LHTFL_surface.attrs["level"] = "surface"
    # ds_hr.LHTFL_surface.attrs["long_name"] = ""
    # ds_hr.LHTFL_surface.attrs["standard_name"] = ""
    # ds_hr.LHTFL_surface.attrs["units"] = ""
    # ds_hr.LHTFL_surface.attrs["ioos_category"] = ""
    # ds_hr.LHTFL_surface.attrs["comment"] = "how calculated"

    ds_hr.percentcloud.attrs["long_name"] = "Cloud Fraction"
    ds_hr.percentcloud.attrs["standard_name"] = "cloud_area_fraction"
    ds_hr.percentcloud.attrs["units"] = "percent"

    ds_hr.PRATE_surface.attrs["level"] = "surface"
    ds_hr.PRATE_surface.attrs["long_name"] = "Precipitation Rate"
    ds_hr.PRATE_surface.attrs["standard_name"] = "precipitation_flux"
    ds_hr.PRATE_surface.attrs["units"] = "kg/m^2/s"

    ds_hr.nav_lat.attrs["ioos_category"] = "location"

    ds_hr.nav_lon.attrs["ioos_category"] = "location"

    ds_hr.precip.attrs["level"] = "surface"
    ds_hr.precip.attrs["long_name"] = "Total Precipitation"
    ds_hr.precip.attrs["standard_name"] = "precipitation_flux"
    ds_hr.precip.attrs["units"] = "kg/m^2/hr"

    ds_hr.qair.attrs["level"] = "2 m above surface"
    ds_hr.qair.attrs["long_name"] = "Specific Humidity"
    ds_hr.qair.attrs["standard_name"] = "specific_humidity_2maboveground"
    ds_hr.qair.attrs["units"] = "kg/kg"
    ds_hr.qair.attrs[
        "comment"
    ] = "calculated from sea level air pressure and dewpoint temperature via WMO 2012 ocean best practices"

    ds_hr.RH_2maboveground.attrs["level"] = "2 m above surface"
    ds_hr.RH_2maboveground.attrs["long_name"] = "Relative Humidity"
    ds_hr.RH_2maboveground.attrs["standard_name"] = "relative_humidity_2maboveground"
    ds_hr.RH_2maboveground.attrs["units"] = "percent"
    ds_hr.RH_2maboveground.attrs[
        "comment"
    ] = "calculated from air temperature and dewpoint temperature via WMO 2012 ocean best practices"

    ds_hr.solar.attrs["level"] = "surface"
    ds_hr.solar.attrs["long_name"] = "Downward Short-Wave Radiation Flux"
    ds_hr.solar.attrs["standard_name"] = "net_downward_shortwave_flux_in_air"
    ds_hr.solar.attrs["units"] = "W/m^2"

    ds_hr.tair.attrs["level"] = "2 m above surface"
    ds_hr.tair.attrs["long_name"] = "Air Temperature"
    ds_hr.tair.attrs["standard_name"] = "air_temperature_2maboveground"
    ds_hr.tair.attrs["units"] = "K"

    ds_hr.therm_rad.attrs["level"] = "surface"
    ds_hr.therm_rad.attrs["long_name"] = "Downward Long-Wave Radiation Flux"
    ds_hr.therm_rad.attrs["standard_name"] = "net_downward_longwave_flux_in_air"
    ds_hr.therm_rad.attrs["units"] = "W/m^2"
    ds_hr.therm_rad.attrs["comment"] = (
        "calculated from saturation water vapour pressure, air temperature, and cloud fraction "
        "via Dilly-Unsworth correlation"
    )

    ds_hr.u_wind.attrs["level"] = "10 m above surface"
    ds_hr.u_wind.attrs["long_name"] = "U-Component of Wind"
    ds_hr.u_wind.attrs["standard_name"] = "x_wind"
    ds_hr.u_wind.attrs["units"] = "m/s"
    ds_hr.u_wind.attrs["ioos_category"] = "wind speed and direction"

    ds_hr.v_wind.attrs["level"] = "10 m above surface"
    ds_hr.v_wind.attrs["long_name"] = "V-Component of Wind"
    ds_hr.v_wind.attrs["standard_name"] = "y_wind"
    ds_hr.v_wind.attrs["units"] = "m/s"
    ds_hr.v_wind.attrs["ioos_category"] = "wind speed and direction"

    ds_hr.attrs[
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
@click.argument("netcdf_date", type=click.DateTime(formats=("%Y-%m-%d",)))
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
def cli(netcdf_date, rpn_dir, dest_dir, verbosity):
    """Command-line interface for :py:func:`rpn_to_gemlam.rpn_to_gemlam`.

    Please see:

      rpn-to-gemlam --help

    :param netcdf_date: Date for which to calculate netCDF file from RPN files.
    :type netcdf_date: :py:class:`datetime.datetime`

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
    rpn_to_gemlam(arrow.get(netcdf_date), rpn_dir, dest_dir)
