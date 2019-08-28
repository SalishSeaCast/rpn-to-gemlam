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
"""Unit tests for rpn_to_gemlam module.
"""
from pathlib import Path
from unittest.mock import call, patch

import arrow
import pytest

from rpn_to_gemlam import rpn_to_gemlam


@pytest.mark.parametrize("forecast", ("00", "06", "12", "18"))
@patch("rpn_to_gemlam.rpn_to_gemlam._exec_bash_func", autospec=True)
@patch("rpn_to_gemlam.rpn_to_gemlam._write_nemo_hr_file", autospec=True)
class TestRPN_HrsToNEMO_Hrs:
    """Unit tests for _rpn_hrs_to_nemo_hrs().
    """

    def test_rpn_netcdf_calls(self, m_write_nemo_hr_file, m_exec_bash_func, forecast):
        rpn_to_gemlam._rpn_hrs_to_nemo_hrs(
            arrow.get("2007-01-01"),
            arrow.get("2007-01-01"),
            forecast,
            Path("rpn_dir"),
            Path("tmp_dir"),
            keep_rpn_fcst_hr_files=False,
            bunzip2_rpn_fcst_hr_files=True,
        )
        assert m_exec_bash_func.call_args_list == [
            call(f"rpn-netcdf {forecast} 2006-12-31 rpn_dir tmp_dir False True"),
            call(f"rpn-netcdf {forecast} 2007-01-01 rpn_dir tmp_dir False True"),
        ]

    def test_write_nemo_hr_file_calls(
        self, m_write_nemo_hr_file, m_exec_bash_func, forecast
    ):
        rpn_to_gemlam._rpn_hrs_to_nemo_hrs(
            arrow.get("2007-01-01"),
            arrow.get("2007-01-01"),
            forecast,
            Path("rpn_dir"),
            Path("tmp_dir"),
            keep_rpn_fcst_hr_files=False,
            bunzip2_rpn_fcst_hr_files=True,
        )
        assert m_write_nemo_hr_file.call_count == 50
        assert m_write_nemo_hr_file.call_args_list[0] == call(
            Path(f"tmp_dir/20061230{forecast}_{(24-int(forecast)):03d}.nc"),
            Path(f"tmp_dir/gemlam_y2006m12d31_000.nc"),
        )
        assert m_write_nemo_hr_file.call_args_list[-1] == call(
            Path(f"tmp_dir/20070101{forecast}_{(24-int(forecast)):03d}.nc"),
            Path(f"tmp_dir/gemlam_y2007m01d01_024.nc"),
        )


@patch("rpn_to_gemlam.rpn_to_gemlam._interpolate_inter_day_missing_hrs", autospec=True)
@patch("rpn_to_gemlam.rpn_to_gemlam._interpolate_intra_day_missing_hrs", autospec=True)
@patch("rpn_to_gemlam.rpn_to_gemlam.Path.exists", autospec=True)
class TestHandleMissingHrFiles:
    """Unit tests for _handle_missing_hr_files().
    """

    def test_lteq_4_missing_hrs(
        self, m_exists, m_interp_intra_day_missing_hrs, m_interp_inter_day_missing_hrs
    ):
        m_exists.side_effect = [True, False, False] + [True] * 45
        rpn_to_gemlam._handle_missing_hr_files(
            arrow.get("2013-08-29"), arrow.get("2013-08-29"), Path("tmp_dir")
        )
        m_interp_intra_day_missing_hrs.assert_called_once_with(
            [
                {
                    "hr": arrow.get("2013-08-28 01:00:00"),
                    "ds_path": Path("tmp_dir", "gemlam_y2013m08d28_001.nc"),
                },
                {
                    "hr": arrow.get("2013-08-28 02:00:00"),
                    "ds_path": Path("tmp_dir", "gemlam_y2013m08d28_002.nc"),
                },
            ]
        )

    def test_gt_4_missing_hrs(
        self, m_exists, m_interp_intra_day_missing_hrs, m_interp_inter_day_missing_hrs
    ):
        m_exists.side_effect = [True] * 24 + [False] * 5 + [True] * 19
        rpn_to_gemlam._handle_missing_hr_files(
            arrow.get("2007-02-01"), arrow.get("2007-02-01"), Path("tmp_dir")
        )
        m_interp_inter_day_missing_hrs.assert_called_once_with(
            [
                {
                    "hr": arrow.get("2007-02-01 00:00:00"),
                    "ds_path": Path("tmp_dir", "gemlam_y2007m02d01_000.nc"),
                },
                {
                    "hr": arrow.get("2007-02-01 01:00:00"),
                    "ds_path": Path("tmp_dir", "gemlam_y2007m02d01_001.nc"),
                },
                {
                    "hr": arrow.get("2007-02-01 02:00:00"),
                    "ds_path": Path("tmp_dir", "gemlam_y2007m02d01_002.nc"),
                },
                {
                    "hr": arrow.get("2007-02-01 03:00:00"),
                    "ds_path": Path("tmp_dir", "gemlam_y2007m02d01_003.nc"),
                },
                {
                    "hr": arrow.get("2007-02-01 04:00:00"),
                    "ds_path": Path("tmp_dir", "gemlam_y2007m02d01_004.nc"),
                },
            ]
        )

    def test_missing_hrs_at_end_of_date_range(
        self, m_exists, m_interp_intra_day_missing_hrs, m_interp_inter_day_missing_hrs
    ):
        m_exists.side_effect = [True] * 36 + [False] * 12
        with pytest.raises(
            FileNotFoundError, match="missing hours at end of date range"
        ):
            rpn_to_gemlam._handle_missing_hr_files(
                arrow.get("2007-02-01"), arrow.get("2007-02-01"), Path("tmp_dir")
            )


@patch("rpn_to_gemlam.rpn_to_gemlam.logging", autospec=True)
@patch("rpn_to_gemlam.rpn_to_gemlam.xarray.open_dataset")
@patch("rpn_to_gemlam.rpn_to_gemlam._exec_bash_func", autospec=True)
class TestInterpolateMissingHrs:
    """Unit tests for _interpolate_intra_day_missing_hrs().
    """

    def test_lteq_4_missing_hrs(self, m_exec_bash_func, m_open_ds, m_logging):
        m_open_ds().__enter__().time_counter.values = [2008911600.0]
        m_open_ds().__enter__().attrs = {}
        missing_hrs = [
            {
                "hr": arrow.get("2013-08-28 00:00:00"),
                "ds_path": Path("tmp_dir", "gemlam_y2013m08d28_000.nc"),
            },
            {
                "hr": arrow.get("2013-08-28 01:00:00"),
                "ds_path": Path("tmp_dir", "gemlam_y2013m08d28_001.nc"),
            },
        ]
        rpn_to_gemlam._interpolate_intra_day_missing_hrs(missing_hrs)
        assert m_exec_bash_func.call_args_list == [
            call(
                f'interp-for-time_counter-value 2008915200 {Path("tmp_dir", "gemlam_y2013m08d27_023.nc")} '
                f'{Path("tmp_dir", "gemlam_y2013m08d28_002.nc")} '
                f'{Path("tmp_dir", "gemlam_y2013m08d28_000.nc")}'
            ),
            call(
                f'interp-for-time_counter-value 2008918800 {Path("tmp_dir", "gemlam_y2013m08d27_023.nc")} '
                f'{Path("tmp_dir", "gemlam_y2013m08d28_002.nc")} '
                f'{Path("tmp_dir", "gemlam_y2013m08d28_001.nc")}'
            ),
        ]

    @pytest.mark.parametrize(
        "ds_attrs, expected",
        (
            (({"missing_variables": "solar"}, None), "previous available hour"),
            ((None, {"missing_variables": "solar"}), "next available hour"),
        ),
    )
    def test_avail_hr_ds_missing_vars(
        self, m_exec_bash_func, m_open_ds, m_logging, ds_attrs, expected
    ):
        m_open_ds().__enter__().attrs.get.side_effect = ds_attrs
        missing_hrs = [
            {
                "hr": arrow.get("2013-08-28 00:00:00"),
                "ds_path": Path("tmp_dir", "gemlam_y2013m08d28_000.nc"),
            },
            {
                "hr": arrow.get("2013-08-28 01:00:00"),
                "ds_path": Path("tmp_dir", "gemlam_y2013m08d28_001.nc"),
            },
        ]
        with pytest.raises(SystemExit):
            rpn_to_gemlam._interpolate_intra_day_missing_hrs(missing_hrs)
        assert expected in m_logging.error.call_args_list[0][0][0]
