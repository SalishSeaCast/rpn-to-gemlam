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

from rpn_to_gemlam import rpn_to_gemlam


class TestRpnToGemlam:
    """Unit tests for rpn_to_gemlam().
    """

    @patch("rpn_to_gemlam.rpn_to_gemlam._exec_bash_func", autospec=True)
    def test_rpn_to_gemlam(self, m_exec_bash_cmd):
        rpn_to_gemlam.rpn_to_gemlam(
            arrow.get("2014-11-02"),
            Path("/opp/GEMLAM/"),
            Path("/results/forcing/atmospheric/GEM2.5/gemlam/"),
        )
        assert m_exec_bash_cmd.call_args_list == [call()]
