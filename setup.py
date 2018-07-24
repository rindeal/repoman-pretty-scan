#!/usr/bin/env python3
# Compatibility: python3.6+
##
# Copyright (C) 2018 Jan Chren (rindeal)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-only
##

from distutils.core import setup
import os
import sys


# make sure local modules are imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from rindeal.portage.repoman.pretty_scan import __PkgMetadata__ as metadata


setup(
	# >> required fields
	name=metadata.name,
	version=metadata.version,
	url=metadata.url,
	description=metadata.summary,

	# >> creator section
	author=metadata.author,
	author_email=metadata.author_email,
	license=metadata.licence_identifier,

	# >> dependencies
	platforms=(
		"linux",
		"python3.6+",
	),
	requires=(
		"repoman",
		"rindeal.travis_ci.utils",
	),

	# >> stuff to actually do
	package_dir={
		'': 'lib',
	},
	packages=(
		"rindeal.portage.repoman.pretty_scan",
	),
	scripts=(
		"bin/repoman-pretty-scan",
	),
)
