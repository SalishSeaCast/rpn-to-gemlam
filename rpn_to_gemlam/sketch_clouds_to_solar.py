Q_o = 1368.0
cloud_consts = { A : [0.6337, 0.6149, 0.5861, 0.5512, 0.5002, 0.4649, 0.4225, 0.3669, 0.2468, 0.1981, 0.0841],
                 B : [0.1959, 0.2119, 0.2400, 0.2859, 0.3192, 0.3356, 0.3339, 0.3490, 0.4427, 0.3116, 0.2283]
                 }
# day_time : seconds, LST
hour = (day_time / 3600.0 - 12.0) * 15.0  # degrees
# day : yearday
declination = 23.45 * np.pi / 180.0 * np.sin((284.0 + day) / 365.25 * 2.0 * np.pi)  # radians
# latitude in degrees
# Convert latitude of centre of model domain from degrees to radians
lat = np.pi * latitude / 180.0

a = np.sin(declination) * np.sin(lat)
b = np.cos(declination) * np.cos(lat)
cos_Z = a + b * np.cos(np.pi / 180.0 * hour)      # solar elevation
hour_angle = np.tan(lat) * np.tan(declination)  # cos of -hour_angle in radians
# assume we are south of the Arctic Circle
day_length = np.arccos(-hour_angle) / 15.0 * 2 * 180.0 / np.pi # hours: 15 = 360/24
sunrise = 12.0 - 0.5 * day_length   # hours
sunset = 12.0 + 0.5 * day_length   # hours
Qso = Q_o * (1.0 + 0.033 * np.cos(day / 365.25 * 2 * np.pi))
# cf_value is cloud fraction in tenths, decimal is fine
fcf = floor(cf_value)   # integer below cf value
ccf = ceiling(cf_value) # integer above cf value
if fcf == ccf:
    if fcf == 10:
        fcf = 9
    else:
        ccf = fcf+1
                                                                                                                                                                                     if day_time / 3600.0 > sunrise and day_time / 3600.0 < sunset:
    solar = Qso * (cloud_consts.A[fcf] * (ccf - cf_value) + cloud_consts.A[ccf] * (cf_value - fcf)
                  + (cloud_consts.B[fcf] * (ccf - cf_value) + cloud_consts.B[ccf] * (cf_value - fcf))
                  * cos_Z) * cos_Z
else:
    solar = 0.
