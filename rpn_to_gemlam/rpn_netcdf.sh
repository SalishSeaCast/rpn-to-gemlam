#!/usr/bin/env bash
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

# cstrpn2cdf executable and libs it depends on
CSTRPN2CDF=/data/dlatorne/MEOPAR/cstrpn2cdf/cstrpn2cdf
LD_LIBRARY_PATH=/data/dlatorne/MEOPAR/cstrpn2cdf:${LD_LIBRARY_PATH}

_rpn-netcdf-hour () {
  day=$1
  hr=$2
  yr=$(date --date="${day}" +%Y)
  rpn_dir=$3
  tmp_dir=$4

  # decompress GEMLAM RPN forecast hour file
  /bin/bzip2 -c -k -d ${rpn_dir}/${yr}/${day}06_${hr}.bz2 > "${tmp_dir}/${day}06_${hr}"

  # extract variables of interest from GEMLAM RPN file
  for var in FB NT PN PR RN RT
  do
     LD_LIBRARY_PATH=${LD_LIBRARY_PATH} ${CSTRPN2CDF} \
        -s ${tmp_dir}/${day}06_${hr} \
        -d ${tmp_dir}/${day}06_${var}_${hr} \
        -nomv ${var} -ip1 0
  done
  for var in TD TT UU VV
  do
     LD_LIBRARY_PATH=${LD_LIBRARY_PATH} ${CSTRPN2CDF} \
     -s ${tmp_dir}/${day}06_${hr} \
     -d ${tmp_dir}/${day}06_${var}_${hr} \
     -nomv ${var} -ip1 12000
  done

  # # delete GEMLAM RPN forecast hour file
   /bin/rm -f ${tmp_dir}/${day}06_${hr}

  # append single variable files into a single file for the hour
  for var in FB NT PN PR RN RT TD TT UU VV
  do
    /usr/bin/ncks -4 -h -A ${tmp_dir}/${day}06_${var}_${hr}.nc ${tmp_dir}/${day}06_${hr}.nc
  done

   # delete single variable files
   /bin/rm -f ${tmp_dir}/${day}06_*_${hr}.nc
}


rpn-netcdf () {
  netcdf_date=$1
  rpn_dir=$2
  tmp_dir=$3
  dest_dir=$4
#  daym1=$(date --date="${netcdf_date} -1 day" +%Y%m%d)
#  for hr in {018..024}
#  do
#    _rpn-netcdf-hour ${daym1} ${hr} ${rpn_dir} ${tmp_dir}
#  done
#
#  day=$(date --date="${netcdf_date}" +%Y%m%d)
#  for hr in {001..017}
#  do
#    _rpn-netcdf-hour ${day} ${hr} ${rpn_dir} ${tmp_dir}
#  done

  # single hour for testing
  day=$(date --date="${netcdf_date}" +%Y%m%d)
  for hr in {012..012}
  do
    _rpn-netcdf-hour ${day} ${hr} ${rpn_dir} ${tmp_dir}
  done

  # # delete empty files from missing hours
  # /usr/bin/find ${tmp_dir} -empty -delete

  # # concatenate netCDF hour file along time dimension
  # ncrcat -4 -L4 -O -o ${tmp_dir}/${day}06.nc ${tmp_dir}/${daym1}06_0*.nc ${dest_dir}${day}06_0*.nc

  # # delete hourly files
  # /bin/rm -f ${tmp_dir}/${daym1}06_0*.nc ${tmp_dir}/${day}06_0*.nc
}