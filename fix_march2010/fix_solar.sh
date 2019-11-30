m=3;
for d in 25 27;
 do
 echo $d
 p=`expr $d - 1`;
 n=`expr $d + 1`;
 for h in {013..023};
  do echo -n "gemlam_y2010m0${m}d${d}_$h.nc: ";
      /usr/bin/ncra -v solar /data/dlatorne/tmp-rpn-to-gem-lam/gemlam_y2010m0${m}d${p}_$h.nc /data/dlatorne/tmp-rpn-to-gem-lam/gemlam_y2010m0${m}d${n}_$h.nc newfile.nc;
      cp /data/dlatorne/tmp-rpn-to-gem-lam/gemlam_y2010m0${m}d${d}_$h.nc .
      ncks -x -v solar gemlam_y2010m0${m}d${d}_$h.nc testfile.nc
      ncks -A -v solar newfile.nc testfile.nc
      mv testfile.nc gemlam_y2010m0${m}d${d}_$h.nc
      rm -f newfile.nc
  done;
 done
