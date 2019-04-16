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
    for hr in range(24):
        hr_ds_path = tmp_dir / f"{netcdf_date.format('YYYYMMDD')}06_{(hr + 1):03d}.nc"
        try:
            with xarray.open_dataset(hr_ds_path) as ds_hr:
                logging.debug(
                    f"calculating specific humidity & incoming longwave radiation from {hr_ds_path}"
                )
                da_qair, da_ilwr = _calc_qair_ilwr(ds_hr)
        except FileNotFoundError:
            # Missing forecast hour; we'll fill it in later
            continue


def _calc_qair_ilwr(ds_hr):
    """Calculate specific humidity and incoming longwave radiation data arrays from an
    forecast hour dataset.

    :param :py:class:`xarray.Dataset` ds_hr: Forecast hour dataset.

    :returns: Specific humidity, Incoming longwave radiation data arrrays
    :rtype: 2-tuple of :py:class:`xarray.DataArray`
    """
    P = ds_hr.PN / 100  # convert to hectopascals
    # saturation water vapour at the dew point in the pure phase
    ew = 6.112 * numpy.exp(17.62 * ds_hr.TD / (243.12 + ds_hr.TD))
    xvw = ew / (0.01 * ds_hr.PN)  # converting P to hectopascals
    r = 0.62198 * xvw / (1 - xvw)  # as at Td r = rw
    qair = xarray.DataArray(r / (1 + r))

    ew = ew / 1000.0  # Change vapour pressure to kPa
    w = 465 * ew / ds_hr.TT
    Lclr = (
        59.38 + 113.7 * (ds_hr.TT / 273.16) ** 6 + 96.96 * numpy.sqrt(w / 2.5)
    )  # Dilley
    # Unsworth
    sigma = 5.6697e-8
    eclr = Lclr / (sigma * ds_hr.TT ** 4)
    ewc = (1 - 0.84 * ds_hr.NT) * eclr + 0.84 * ds_hr.NT
    ilwr = xarray.DataArray(ewc * sigma * ds_hr.TT ** 4)

    return qair, ilwr


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
