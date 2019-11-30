m=3;
cp /data/dlatorne/tmp-rpn-to-gem-lam/gemlam_y2010m0${m}d24_023.nc .
for d in 26 28;
 do
 for h in {013..023};
  do  cp /data/dlatorne/tmp-rpn-to-gem-lam/gemlam_y2010m0${m}d${d}_$h.nc .
  done;
 done
for d in 25 27;
 do
 for h in {000..012};
  do  cp /data/dlatorne/tmp-rpn-to-gem-lam/gemlam_y2010m0${m}d${d}_$h.nc .
  done;
 done
for d in {25..28};
 do
 p=`expr $d - 1`;
 ncra -v solar gemlam_y2010m0${m}d${p}_023.nc gemlam_y2010m0${m}d${d}_000.nc newfile.nc
 ncap2 -s 'time_counter+=1800' newfile.nc asolar_y2010m0${m}d${d}_000.nc
 echo -n "asolar_y2010m0${m}d${d}_000.nc: ";
 rm -f newfile.nc
 for h in {1..9};
 do
 ph=`expr $h - 1`;
 ncra -v solar gemlam_y2010m0${m}d${d}_00${ph}.nc gemlam_y2010m0${m}d${d}_00${h}.nc newfile.nc
 ncap2 -s 'time_counter+=1800' newfile.nc asolar_y2010m0${m}d${d}_00${h}.nc
 echo -n "asolar_y2010m0${m}d${d}_00${h}.nc: ";
 rm -f newfile.nc
 done;
 ncra -v solar gemlam_y2010m0${m}d${d}_009.nc gemlam_y2010m0${m}d${d}_010.nc newfile.nc
 ncap2 -s 'time_counter+=1800' newfile.nc asolar_y2010m0${m}d${d}_010.nc
  echo -n "asolar_y2010m0${m}d${d}_010.nc: ";
 rm -f newfile.nc
 for h in {11..23};
 do
 ph=`expr $h - 1`;
 ncra -v solar gemlam_y2010m0${m}d${d}_0${ph}.nc gemlam_y2010m0${m}d${d}_0${h}.nc newfile.nc
 ncap2 -s 'time_counter+=1800' newfile.nc asolar_y2010m0${m}d${d}_0${h}.nc
 echo -n "asolar_y2010m0${m}d${d}_0${h}.nc: ";
 rm -f newfile.nc
 done;
done;



 
