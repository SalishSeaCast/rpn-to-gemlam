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
  forecast=$1
  day=$2
  hr=$3
  yr=$(date --date="${day}" +%Y)
  rpn_dir=$4
  tmp_dir=$5
  keep_rpn_fcst_hr_files=$6
  bunzip2_rpn_fcst_hr_files=$7

  if [ ${bunzip2_rpn_fcst_hr_files} = True ]
  then
    # decompress GEMLAM RPN forecast hour file
    /bin/bzip2 -c -k -d \
      ${rpn_dir}/${yr}/${day}${forecast}_${hr}.bz2 > "${tmp_dir}/${day}${forecast}_${hr}"
  fi

  # extract variables of interest from GEMLAM RPN file
  for var in FB NT PN PR RN RT
  do
     LD_LIBRARY_PATH=${LD_LIBRARY_PATH} ${CSTRPN2CDF} \
        -s ${tmp_dir}/${day}${forecast}_${hr} \
        -d ${tmp_dir}/${day}${forecast}_${var}_${hr} \
        -nomv ${var} -ip1 0
  done
  for var in TD TT UU VV
  do
     LD_LIBRARY_PATH=${LD_LIBRARY_PATH} ${CSTRPN2CDF} \
     -s ${tmp_dir}/${day}${forecast}_${hr} \
     -d ${tmp_dir}/${day}${forecast}_${var}_${hr} \
     -nomv ${var} -ip1 12000
  done

  if [ ${keep_rpn_fcst_hr_files} = False  ]
  then
    # delete GEMLAM RPN forecast hour file
    /bin/rm -f ${tmp_dir}/${day}${forecast}_${hr}
  fi

  # append single variable files into a single file for the hour
  for var in FB NT PN PR RN RT TD TT UU VV
  do
    /usr/bin/ncks -4 -h -A \
      ${tmp_dir}/${day}${forecast}_${var}_${hr}.nc ${tmp_dir}/${day}${forecast}_${hr}.nc
  done

  # delete single variable files
  /bin/rm -f ${tmp_dir}/${day}${forecast}_*_${hr}.nc

  # Reduce grid size to what is needed for SalishSeaCast
  /usr/bin/ncea -4 -O -d y,20,285 -d x,110,365 \
    ${tmp_dir}/${day}${forecast}_${hr}.nc ${tmp_dir}/${day}${forecast}_${hr}.nc

  # Convert air temperature from Celcuis to Kelvin
  /usr/bin/ncap2 -4 -O -s "TT=TT+273.14" \
    ${tmp_dir}/${day}${forecast}_${hr}.nc ${tmp_dir}/${day}${forecast}_${hr}.nc

  # Convert atmospheric pressure from millibars to Pascals
  /usr/bin/ncap2 -4 -O -s "PN=PN*100" \
    ${tmp_dir}/${day}${forecast}_${hr}.nc ${tmp_dir}/${day}${forecast}_${hr}.nc

  # Convert wind from knots to m/s
  /usr/bin/ncap2 -4 -O -s "UU=UU*0.514444" \
    ${tmp_dir}/${day}${forecast}_${hr}.nc ${tmp_dir}/${day}${forecast}_${hr}.nc
  /usr/bin/ncap2 -4 -O -s "VV=VV*0.514444" \
    ${tmp_dir}/${day}${forecast}_${hr}.nc ${tmp_dir}/${day}${forecast}_${hr}.nc

  # Convert accumulated precip to kg m^2 / s  (from m accumulated over an hour)
  /usr/bin/ncap2 -4 -O -s "PR=PR/3.6" \
    ${tmp_dir}/${day}${forecast}_${hr}.nc ${tmp_dir}/${day}${forecast}_${hr}.nc

  # Convert instantaneous precip to kg m^2 / s (from m / s)
  /usr/bin/ncap2 -4 -O -s "RT=RT*1000" \
    ${tmp_dir}/${day}${forecast}_${hr}.nc ${tmp_dir}/${day}${forecast}_${hr}.nc
}


rpn-netcdf () {
  forecast=$1
  netcdf_date=$2
  rpn_dir=$3
  tmp_dir=$4
  keep_rpn_fcst_hr_files=$5
  bunzip2_rpn_fcst_hr_files=$6

  case ${forecast} in
  00)
    daym1=$(date --date="${netcdf_date} -1 day" +%Y%m%d)
    _rpn-netcdf-hour ${forecast} ${daym1} 024 ${rpn_dir} ${tmp_dir} \
      ${keep_rpn_fcst_hr_files} ${bunzip2_rpn_fcst_hr_files}
    day=$(date --date="${netcdf_date}" +%Y%m%d)
    for hr in {001..023}
    do
      _rpn-netcdf-hour ${forecast} ${day} ${hr} ${rpn_dir} ${tmp_dir} \
        ${keep_rpn_fcst_hr_files} ${bunzip2_rpn_fcst_hr_files}
    done
    ;;
  06)
    daym1=$(date --date="${netcdf_date} -1 day" +%Y%m%d)
    for hr in {018..024}
    do
      _rpn-netcdf-hour ${forecast} ${daym1} ${hr} ${rpn_dir} ${tmp_dir} \
        ${keep_rpn_fcst_hr_files} ${bunzip2_rpn_fcst_hr_files}
    done
    day=$(date --date="${netcdf_date}" +%Y%m%d)
    for hr in {001..017}
    do
      _rpn-netcdf-hour ${forecast} ${day} ${hr} ${rpn_dir} ${tmp_dir} \
        ${keep_rpn_fcst_hr_files} ${bunzip2_rpn_fcst_hr_files}
    done
    ;;
  12)
    daym1=$(date --date="${netcdf_date} -1 day" +%Y%m%d)
    for hr in {012..024}
    do
      _rpn-netcdf-hour ${forecast} ${daym1} ${hr} ${rpn_dir} ${tmp_dir} \
        ${keep_rpn_fcst_hr_files} ${bunzip2_rpn_fcst_hr_files}
    done
    day=$(date --date="${netcdf_date}" +%Y%m%d)
    for hr in {001..011}
    do
      _rpn-netcdf-hour ${forecast} ${day} ${hr} ${rpn_dir} ${tmp_dir} \
        ${keep_rpn_fcst_hr_files} ${bunzip2_rpn_fcst_hr_files}
    done
    ;;
  18)
    daym1=$(date --date="${netcdf_date} -1 day" +%Y%m%d)
    for hr in {006..024}
    do
      _rpn-netcdf-hour ${forecast} ${daym1} ${hr} ${rpn_dir} ${tmp_dir} \
        ${keep_rpn_fcst_hr_files} ${bunzip2_rpn_fcst_hr_files}
    done
    day=$(date --date="${netcdf_date}" +%Y%m%d)
    for hr in {001..005}
    do
      _rpn-netcdf-hour ${forecast} ${day} ${hr} ${rpn_dir} ${tmp_dir} \
        ${keep_rpn_fcst_hr_files} ${bunzip2_rpn_fcst_hr_files}
    done
    ;;
esac

  # delete empty files from missing hours
  /usr/bin/find ${tmp_dir} -empty -delete
}


avg-diff-hrs () {
  prev_hr_file=$1
  hr_file=$2
  dest_file=$3

  # average instantaneous solar radiation from 2 hours to get value that should be
  # reasonably consistent with the hour-averaged values we get from HRDPS GRIBs
  /usr/bin/ncra -4 -O -o /dev/shm/solar.nc -v solar ${prev_hr_file} ${hr_file}
  /usr/bin/ncks -4 -A -v solar /dev/shm/solar.nc ${dest_file}
  /bin/rm -f /dev/shm/solar.nc

  # calculate precipitation sums over domain to use as check for whether or not
  # we are at the first hour of a day's precipitation accumulation
  /usr/bin/ncwa -4 -O -o /dev/shm/prev_precip_sum.nc -v precip ${prev_hr_file}
  /usr/bin/ncwa -4 -O -o /dev/shm/hr_precip_sum.nc -v precip ${hr_file}

  # calculate difference of precipitation sums
  prev_precip_sum=$(/usr/bin/ncdump -v precip /dev/shm/prev_precip_sum.nc | grep 'precip =' | cut -c 11-)
  prev_precip_sum=${prev_precip_sum::-2}
  hr_precip_sum=$(/usr/bin/ncdump -v precip /dev/shm/hr_precip_sum.nc | grep 'precip =' | cut -c 11-)
  hr_precip_sum=${hr_precip_sum::-2}
  accumulating=$(echo "${hr_precip_sum}>${prev_precip_sum}" | bc)
  /bin/rm -f /dev/shm/prev_precip_sum.nc /dev/shm/hr_precip_sum.nc

  if [ ${accumulating} -eq 1 ]
  then
    # precipitation value is accumulated in this hour so calculate this hour value
    # by subtracting previous hour value
    /usr/bin/ncdiff -4 -O -o /dev/shm/precip.nc -v precip ${hr_file} ${prev_hr_file}
    /usr/bin/ncks -4 -A -v precip /dev/shm/precip.nc ${dest_file}
    /bin/rm -f /dev/shm/precip.nc
  fi

  # adjust time_counter value so that it is always on the hour
  # increment by 900 instead of 1800 because ncap2 int() rounds rather than truncating
  /usr/bin/ncap2 -O -s 'time_counter=int((time_counter+900)/3600)*3600;' ${dest_file} ${dest_file}
}


cat-hrs-to-days () {
  dest_file_stem=$1

  /usr/bin/ncrcat -4 -L4 -O ${dest_file_stem}_0??.nc ${dest_file_stem}.nc
  /bin/rm -f ${dest_file_stem}_0??.nc
}


interp-for-time_counter-value () {
  # Interpolate variable values for time_counter_value from prev_avail_hr_file and
  # next_avail_hr_file into missing_hr_file
  time_counter_value=$1
  prev_avail_hr_file=$2
  next_avail_hr_file=$3
  missing_hr_file=$4

  /usr/bin/ncflint -i time_counter,${time_counter_value} \
    -v atmpres,percentcloud,PRATE_surface,precip,qair,RH_2maboveground,solar,tair,therm_rad,u_wind,v_wind \
    ${prev_avail_hr_file} ${next_avail_hr_file} ${missing_hr_file}
}


interp-var-for-time_counter-value () {
  # Interpolate specified variable values for time_counter_value from prev_avail_hr_file and
  # next_avail_hr_file into missing_hr_file
  var=$1
  time_counter_value=$2
  prev_avail_hr_file=$3
  next_avail_hr_file=$4
  missing_hr_file=$5

  /usr/bin/ncflint -O -i time_counter,${time_counter_value} -v ${var} \
    ${prev_avail_hr_file} ${next_avail_hr_file} ${var}.nc
  /usr/bin/ncks -A -v ${var} ${var}.nc ${missing_hr_file}
  /usr/bin/ncatted -a missing_variables,global,d,, ${missing_hr_file}
}
