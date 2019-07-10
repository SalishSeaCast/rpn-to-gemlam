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


@patch("rpn_to_gemlam.rpn_to_gemlam._interpolate_missing_hrs", autospec=True)
@patch("rpn_to_gemlam.rpn_to_gemlam.Path.exists", autospec=True)
class TestHandleMissingHrFiles:
    """Unit tests for _handle_missing_hr_files().
    """

    def test_lteq_4_missing_hrs(self, m_exists, m_interp_missing_hrs):
        m_exists.side_effect = [True, False, False] + [True] * 45
        missing_hrs = rpn_to_gemlam._handle_missing_hr_files(
            arrow.get("2013-08-29"), arrow.get("2013-08-29"), Path("tmp_dir")
        )
        m_interp_missing_hrs.assert_called_once_with(
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

    def test_gt_4_missing_hrs(self, m_exists, m_interp_missing_hrs):
        m_exists.side_effect = [True] + [False] * 5 + [True] * 42
        with pytest.raises(FileNotFoundError):
            rpn_to_gemlam._handle_missing_hr_files(
                arrow.get("2013-08-29"), arrow.get("2013-08-29"), Path("tmp_dir")
            )
        assert not m_interp_missing_hrs.called


class TestInterpolateMissingHrs:
    """Unit tests for _interpolate_missing_hrs().
    """

    @patch("rpn_to_gemlam.rpn_to_gemlam.xarray.open_dataset")
    @patch("rpn_to_gemlam.rpn_to_gemlam._exec_bash_func", autospec=True)
    def test_lteq_4_missing_hrs(self, m_exec_bash_func, m_open_ds):
        m_open_ds().__enter__().time_counter.values = [2008911600.0]
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
        rpn_to_gemlam._interpolate_missing_hrs(missing_hrs)
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
