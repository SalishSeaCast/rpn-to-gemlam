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

  # delete GEMLAM RPN forecast hour file
  /bin/rm -f ${tmp_dir}/${day}06_${hr}

  # append single variable files into a single file for the hour
  for var in FB NT PN PR RN RT TD TT UU VV
  do
    /usr/bin/ncks -4 -h -A ${tmp_dir}/${day}06_${var}_${hr}.nc ${tmp_dir}/${day}06_${hr}.nc
  done

  # delete single variable files
  /bin/rm -f ${tmp_dir}/${day}06_*_${hr}.nc

  # Reduce grid size to what is needed for SalishSeaCast
  /usr/bin/ncea -4 -O -d y,20,285 -d x,110,365 \
    ${tmp_dir}/${day}06_${hr}.nc ${tmp_dir}/${day}06_${hr}.nc

  # Convert air temperature from Celcuis to Kelvin
  /usr/bin/ncap2 -4 -O -s "TT=TT+273.14" ${tmp_dir}/${day}06_${hr}.nc ${tmp_dir}/${day}06_${hr}.nc

  # Convert atmospheric pressure from millibars to Pascals
  /usr/bin/ncap2 -4 -O -s "PN=PN*100" ${tmp_dir}/${day}06_${hr}.nc ${tmp_dir}/${day}06_${hr}.nc

  # Convert wind from knots to m/s
  /usr/bin/ncap2 -4 -O -s "UU=UU*0.514444" ${tmp_dir}/${day}06_${hr}.nc ${tmp_dir}/${day}06_${hr}.nc
  /usr/bin/ncap2 -4 -O -s "VV=VV*0.514444" ${tmp_dir}/${day}06_${hr}.nc ${tmp_dir}/${day}06_${hr}.nc

  # Convert accumulated precip to kg m^2 / s  (from m accumulated over an hour)
  /usr/bin/ncap2 -4 -O -s "PR=PR/3.6" ${tmp_dir}/${day}06_${hr}.nc ${tmp_dir}/${day}06_${hr}.nc

  # Convert instantaneous precip to kg m^2 / s (from m / s)
  /usr/bin/ncap2 -4 -O -s "RT=RT*1000" ${tmp_dir}/${day}06_${hr}.nc ${tmp_dir}/${day}06_${hr}.nc
}


rpn-netcdf () {
  netcdf_date=$1
  rpn_dir=$2
  tmp_dir=$3

  daym1=$(date --date="${netcdf_date} -1 day" +%Y%m%d)
  for hr in {018..024}
  do
    _rpn-netcdf-hour ${daym1} ${hr} ${rpn_dir} ${tmp_dir}
  done

  day=$(date --date="${netcdf_date}" +%Y%m%d)
  for hr in {001..017}
  do
    _rpn-netcdf-hour ${day} ${hr} ${rpn_dir} ${tmp_dir}
  done

  # delete empty files from missing hours
  /usr/bin/find ${tmp_dir} -empty -delete

  # # concatenate netCDF hour file along time dimension
  # ncrcat -4 -L4 -O -o ${tmp_dir}/${day}06.nc ${tmp_dir}/${daym1}06_0*.nc ${dest_dir}${day}06_0*.nc

  # # delete hourly files
  # /bin/rm -f ${tmp_dir}/${daym1}06_0*.nc ${tmp_dir}/${day}06_0*.nc
}


avg-diff-hrs () {
  prev_hr_file=$1
  hr_file=$2
  dest_file=$3

  # average instantaneous solar radiation from 2 hours to get value that should be
  # reasonably consistent with the hour-averaged values we get from HRDPS GRIBs
  /usr/bin/ncra -4 -O -o /tmp/solar.nc -v solar ${prev_hr_file} ${hr_file}
  /usr/bin/ncks -4 -A -v solar /tmp/solar.nc ${dest_file}
  /bin/rm -f /tmp/solar.nc

  # calculate precipitation sums over domain to use as check for whether or not
  # we are at the first hour of a day's precipitation accumulation
  /usr/bin/ncwa -4 -O -o /tmp/prev_precip_sum.nc -v precip ${prev_hr_file}
  /usr/bin/ncwa -4 -O -o /tmp/hr_precip_sum.nc -v precip ${hr_file}

  # calculate difference of precipitation sums
  prev_precip_sum=$(/usr/bin/ncdump -v precip /tmp/prev_precip_sum.nc | grep 'precip =' | cut -c 11-)
  prev_precip_sum=${prev_precip_sum::-2}
  hr_precip_sum=$(/usr/bin/ncdump -v precip /tmp/hr_precip_sum.nc | grep 'precip =' | cut -c 11-)
  hr_precip_sum=${hr_precip_sum::-2}
  accumulating=$(echo "${hr_precip_sum}>${prev_precip_sum}" | bc)
  /bin/rm -f /tmp/prev_precip_sum.nc /tmp/hr_precip_sum.nc

  if [ ${accumulating} -eq 1 ]
  then
    # precipitation value is accumulated in this hour so calculate this hour value
    # by subtracting previous hour value
    /usr/bin/ncdiff -4 -O -o /tmp/precip.nc -v precip ${hr_file} ${prev_hr_file}
    /usr/bin/ncks -4 -A -v precip /tmp/precip.nc ${dest_file}
    /bin/rm -f /tmp/precip.nc
  fi

  # adjust time_counter value so that it is always on the hour
  /usr/bin/ncap2 -O -s 'time_counter=int((time_counter+1800)/3600)*3600;' ${dest_file} ${dest_file}
}
