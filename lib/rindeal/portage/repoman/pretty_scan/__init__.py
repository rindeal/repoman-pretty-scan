# Python-Version-Compatibility: 3.6
##
# Copyright (C)  2018 Jan Chren (rindeal)
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

__all__ = ('Parser', 'Printer')


import collections
import re
import sys
import typing

from rindeal.travis_ci.utils import colour


class _MyDict(collections.OrderedDict):

	def sort(self):
		for x in self.values():
			x.sort()

		def _sort_key(key_val: typing.Tuple[str, typing.Any]):
			key, val = key_val
			return key

		# NOTE: is second __init__() a hack?
		self.__init__(sorted(self.items(), key=_sort_key))

	def _new_key(self, key: str):
		raise NotImplementedError

	def __getitem__(self, key: str):
		if key not in self:
			self._new_key(key)

		return super().__getitem__(key)


# >>> Msg --------------------------------------------------------------------------------------------------------------


class Msg(str):
	pass


class MsgList(list):
	pass


MsgListType = typing.List[str]


# >>> MsgCode ----------------------------------------------------------------------------------------------------------


class MsgCode:
	name: str = None
	msgs: MsgListType = None

	def __init__(self, name):
		self.name = name
		self.msgs = MsgList()

	def sort(self):
		self.msgs.sort()


class MsgCodeList(_MyDict):

	def _new_key(self, key: str):
		self[key] = MsgCode(key)


MsgCodeListType = typing.Union[MsgCodeList, typing.Dict[str, MsgCode]]


# >>> File -------------------------------------------------------------------------------------------------------------


class File:
	name: str = None
	msgcodes: MsgCodeListType = None

	def __init__(self, name: str):
		self.name = name
		self.msgcodes = MsgCodeList()

	def sort(self):
		self.msgcodes.sort()


class FileList(_MyDict):

	def _new_key(self, key):
		self[key] = File(key)


FileListType = typing.Union[FileList, typing.Dict[str, File]]


# >>> Pkg --------------------------------------------------------------------------------------------------------------


class Pkg:
	id: str
	msgcodes: MsgCodeListType
	files: FileListType
	msgs: MsgListType

	def __init__(self, id_: str):
		self.id = id_
		self.msgcodes = MsgCodeList()
		self.msgs = MsgList()
		self.files = FileList()

	def sort(self):
		for o in (self.files, self.msgcodes, self.msgs):
			o.sort()


class PkgList(_MyDict):

	def _new_key(self, key):
		self[key] = Pkg(key)


PkgListType = typing.Union[PkgList, typing.Dict[str, Pkg]]


class ParserResult:
	raw_input: typing.List[str] = []

	pkgs: PkgListType
	unaccountable_msgcodes: MsgCodeListType
	repoman_sez: str = ""

	unrecognized_lines: typing.List[str] = []

	def __init__(
			self,

			raw_input: typing.Optional[typing.List[str]] =None,

			pkgs: typing.Optional[PkgListType] = None,
			unaccountable_msgcodes: typing.Optional[MsgCodeListType] = None,
			repoman_sez: typing.Optional[str] = None,

			unrecognized_lines: typing.Optional[typing.List[str]] = None,
	) -> None:
		self.raw_input = [] if raw_input is None else raw_input

		self.pkgs = PkgList() if pkgs is None else pkgs
		self.unaccountable_msgcodes = MsgCodeList() if unaccountable_msgcodes is None else unaccountable_msgcodes
		self.repoman_sez = "" if repoman_sez is None else repoman_sez

		self.unrecognized_lines = [] if unrecognized_lines is None else unrecognized_lines


class Parser:

	_PAT_GENERIC_MSGCODE = re.compile(
		"""
		^
		(?P<msgcode>
			[a-zA-Z_]+\.[a-zA-Z_]+
		)
		\ +          # followed by some spaces
		(?P<msg>
			.+
		)
		""",
		re.VERBOSE
	)
	_PAT_MSGCODE_AND_FILE = re.compile(
		"""
		^
		## package id
		(?P<pkgid>
			[a-zA-Z0-9-]+     # category
			/
			[a-zA-Z0-9_-]+ # pkg name
		)
		## optional file
		(?:
			/
			(?P<file>
				[^ :]+
			)
		)?
		## optional message
		(?:
			:?  # optionally followed by semicolon
			\ + # and some spaces
			(?P<msg>
				.+
			)
		)?
		""",
		re.VERBOSE
	)
	_PAT_REPOMAN_SEZ = re.compile(
		"""^RepoMan sez: \"(?P<msg>.+)\"""",
		re.VERBOSE
	)

	_stream: typing.TextIO

	_pkgs: PkgListType
	_unacc_msgcodes: MsgCodeListType
	_unrcgn_lines: typing.List[str] = []
	_raw_input: typing.List[str] = []
	_rm_sez_msg: str = ""

	def __init__(self, stream: typing.TextIO = sys.stdin):
		self._stream = stream

		self._pkgs = PkgList()
		self._unacc_msgcodes = MsgCodeList()

	def _parse_line(self, line: str):
		pat1_matches = re.match(self._PAT_GENERIC_MSGCODE, line)
		if pat1_matches is not None:
			print(f"pat1 matches `{line}`")
			msgcode_name, msg = pat1_matches.group('msgcode', 'msg') \
				# type: typing.Optional[str], typing.Optional[str]

			pat2_matches = re.match(self._PAT_MSGCODE_AND_FILE, msg)
			if pat2_matches is not None:
				print(f"pat2 matches `{line}`")
				pkgid, filename, msg = pat2_matches.group('pkgid', 'file', 'msg') \
					# type: str, typing.Optional[str], typing.Optional[str]

				if filename is None:
					msgcode = (
						self
						._pkgs[pkgid]
						.msgcodes[msgcode_name]
					)
				else:
					msgcode = (
						self
						._pkgs[pkgid]
						.files[filename]
						.msgcodes[msgcode_name]
					)
			else:
				msgcode = (
					self
					._unacc_msgcodes[msgcode_name]
				)

			if msg is not None:
				msgcode.msgs.append(Msg(msg))

			return True

		if not self._rm_sez_msg:
		# else:
			print(f"sez matcghing line {line}")
			re.match()
			matches = re.match(self._PAT_REPOMAN_SEZ, line)
			if matches is not None:
				print("sez matched")
				self._rm_sez_msg = matches.group('msg') \
						# type: str

				return True

		return False

	def parse(self):
		lineno = 0
		for line in self._stream:
			lineno += 1
			print(f"processing line #{lineno}: `{line[:-1]}`")

			self._raw_input.append(line)

			if len(line) <= 2:
				print(f"skipping empty line: {line[:-1]}")
				continue

			# skip repoman's own header
			# if lineno < 4:
			# 	print(f"skipping header: {line[:-1]}")
			# 	continue

			if "RepoMan scours the neighborhood" in line:
				continue

			# skip lines announcing the number of reports
			if line.startswith('NumberOf'):
				print(f"skipping numberof: {line[:-1]}")
				continue

			line = line.rstrip()

			if not self._parse_line(line):
				self._unrcgn_lines.append(line)

		# recursive sort
		self._pkgs.sort()

		result = ParserResult(
			raw_input=self._raw_input,

			pkgs=self._pkgs,
			unaccountable_msgcodes=self._unacc_msgcodes,
			repoman_sez=self._rm_sez_msg,

			unrecognized_lines=self._unrcgn_lines
		)

		return result


class Printer:
	INDENT_PREFIX = "  "
	DEFAULT_MAX_LINE_WIDTH = 130

	_results: ParserResult

	_truncate_: bool
	_max_width: int
	_truncate_placeholder: str

	def __init__(
			self,

			results: ParserResult,

			truncate: bool = True,
			max_width: int = DEFAULT_MAX_LINE_WIDTH - 1,
			placeholder: str = "..."
	):
		self._results = results

		self._truncate_ = truncate
		self._max_width = max_width
		self._truncate_placeholder = placeholder

	def _truncate(self, line: str):
		if len(line) > self._max_width:
			# make space for placeholder
			trunc_len = self._max_width - len(self._truncate_placeholder)
			return line[:trunc_len] + self._truncate_placeholder
		else:
			return line

	def _print_indented_line(self, line: str, indent_lvl: int = 0):
		line = (self.INDENT_PREFIX * indent_lvl) + line
		if self._truncate_:
			line = self._truncate(line)
		print(line)

	def _print_msgs(self, msgs: MsgListType, indent_lvl: int = 0):
		for msg in msgs:
			self._print_indented_line(msg, indent_lvl)

	def _print_msgcodes(self, msgcodes: MsgCodeListType, indent_lvl: int = 0):
		for msgcode in msgcodes.values():
			self._print_indented_line(
				colour(msgcode.name, fg='cyan') + (":" if msgcode.msgs else ""),
				indent_lvl
			)
			if msgcode.msgs:
				self._print_msgs(msgcode.msgs, indent_lvl + 1)

	def _print_files(self, files: FileListType, indent_lvl: int = 0):
		for f in files.values():
			self._print_indented_line(
				colour(f.name, fg='blue') + (":" if f.msgcodes else ""),
				indent_lvl
			)
			if f.msgcodes:
				self._print_msgcodes(f.msgcodes, indent_lvl + 1)

	def _print_pkgs(self, pkgs: PkgListType, indent_lvl: int = 0):
		for pkg in pkgs.values():
			self._print_indented_line(
				colour(pkg.id, fg='yellow', bg='black', style='bold') + ":",
				indent_lvl
			)
			if pkg.msgcodes:
				self._print_msgcodes(pkg.msgcodes, indent_lvl + 1)
			if pkg.files:
				self._print_files(pkg.files, indent_lvl + 1)
			if pkg.msgs:
				self._print_msgs(pkg.msgs, indent_lvl + 1)

	def print(self):
		print()
		print(colour("=" * self._max_width, fg='green'))
		print(colour("<<< Repoman results >>>".center(self._max_width, ' '), fg='yellow'))
		print(colour("=" * self._max_width, fg='green'))
		print()

		if self._results.pkgs:
			self._print_pkgs(self._results.pkgs, 0)

		if self._results.unaccountable_msgcodes:
			print()
			print(colour("Other messages", fg='yellow', bg='black') + ":")
			self._print_msgcodes(self._results.unaccountable_msgcodes, 1)

		if self._results.unrecognized_lines:
			print()
			print(colour("Unrecognized lines", fg='magenta', bg='black') + ":")
			for l in self._results.unrecognized_lines:
				print(l)

		if self._results.repoman_sez:
			print()
			print(self._results.repoman_sez)
