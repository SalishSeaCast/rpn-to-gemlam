m=3;
for d in {25..29};
do
dest_file_stem=asolar_y2010m0${m}d${d}
final_file_stem=gemlam_y2010m0${m}d${d}
echo $dest_file_stem
/usr/bin/ncrcat -4 -L4 -O ${dest_file_stem}_0??.nc ${dest_file_stem}.nc
cp /results/forcing/atmospheric/GEM2.5/gemlam/${final_file_stem}.nc .
ncks -x -v solar ${final_file_stem}.nc testfile.nc
ncks -A -v solar ${dest_file_stem}.nc testfile.nc
mv testfile.nc ${final_file_stem}.nc
done
