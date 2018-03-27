#!/usr/bin/env python3.6
##
# Copyright (C) 2018  Jan Chren (rindeal)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
##

import collections
import re
import sys
import typing

from rindeal.travis_ci.utils import colour


class _MyDict(collections.OrderedDict):
	@staticmethod
	def _sort_key(key_val):
		key, val = key_val
		return key

	def sort(self):
		for x in self.values():
			x.sort()
		self.__init__(sorted(self.items(), key=self._sort_key))

	def _new_key(self, key):
		raise NotImplementedError

	def ensure_key_exists(self, key: str):
		if key not in self:
			self._new_key(key)

	def __getitem__(self, key):
		self.ensure_key_exists(key)
		return super().__getitem__(key)


class MsgList(list):
	pass


MsgListType = typing.List[str]


class MsgCode:
	name: str = None
	msgs: MsgListType = None

	def __init__(self, name):
		self.name = name
		self.msgs = MsgList()

	def sort(self):
		self.msgs.sort()


class MsgCodeList(_MyDict):

	def _new_key(self, key):
		self[key] = MsgCode(key)


MsgCodeListType = typing.Union[MsgCodeList, typing.Dict[str, MsgCode]]


class File:
	name: str = None
	msgcodes: MsgCodeListType = None

	def __init__(self, name):
		self.name = name
		self.msgcodes = MsgCodeList()

	def sort(self):
		self.msgcodes.sort()


class FileList(_MyDict):

	def _new_key(self, key):
		self[key] = File(key)


FileListType = typing.Union['FileList', typing.Dict[str, File]]


class Pkg:
	id: str = None
	msgcodes: MsgCodeListType = None
	files: FileListType = None
	msgs: MsgListType = None

	def __init__(self, id_):
		self.id = id_
		self.msgcodes = MsgCodeList()
		self.msgs = MsgList()
		self.files = FileList()

	def sort(self):
		self.files.sort()
		self.msgcodes.sort()
		self.msgs.sort()


class PkgList(_MyDict):

	def _new_key(self, key):
		self[key] = Pkg(key)


PkgListType = typing.Union[PkgList, typing.Dict[str, Pkg]]


class Parser:

	_PAT1 = re.compile(
		"""
		^
		(?P<msgcode>
			[a-zA-Z\._]+
		)
		\ +          # followed by some spaces
		(?P<msg>
			.+
		)
		""",
		re.VERBOSE
	)
	_PAT2 = re.compile(
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

	_stream: typing.TextIO

	pkgs: PkgListType
	other_msgcodes: MsgCodeListType
	invalid_lines: list
	raw_input: typing.List[str]

	def __init__(self, stream: typing.TextIO = sys.stdin):
		self._stream = stream

		self.pkgs = PkgList()
		self.other_msgcodes = MsgCodeList()
		self.invalid_lines = []
		self.raw_input = []

	def _parse_line(self, line: str):
		m = re.match(self._PAT1, line)
		if m is not None:
			msgcode_name, msg = m.group('msgcode', 'msg')
			msgcode_name: str
			msg: str

			m = re.match(self._PAT2, msg)
			if m is not None:
				pkgid, filename, msg = m.group('pkgid', 'file', 'msg')
				pkgid: str
				filename: typing.Optional[str]
				msg: typing.Optional[str]

				if filename is None:
					msgcode = (
						self
						.pkgs[pkgid]
						.msgcodes[msgcode_name]
					)
				else:
					msgcode = (
						self
						.pkgs[pkgid]
						.files[filename]
						.msgcodes[msgcode_name]
					)
			else:
				msgcode = (
					self
					.other_msgcodes[msgcode_name]
				)

			if msg is not None:
				msgcode.msgs.append(msg)
		else:
			self.invalid_lines.append(line)

	def parse(self):
		lineno = 0
		for line in self._stream:
			lineno += 1

			# skip repoman's own header
			if lineno < 4:
				continue
			# skip lines announcing the number of reports
			if line.startswith('NumberOf'):
				continue
			# any empty line after those lines marks the end of a useful output
			if len(line) <= 2:
				break

			self.raw_input.append(line)

			line = line.rstrip()
			self._parse_line(line)

		self.pkgs.sort()


class Printer:
	INDENT_PREFIX = "  "

	TRAVIS_CI_MAX_LINE_WIDTH = 130

	_pkgs: PkgListType
	_other_msgcodes: MsgCodeListType
	_invalid_lines: list
	_max_width: int
	_truncate_: bool
	_truncate_placeholder: str

	def __init__(
			self,
			pkgs: PkgListType,
			other_msgcodes: MsgCodeListType,
			invalid_lines: list,
			truncate: bool = True,
			max_width: int = TRAVIS_CI_MAX_LINE_WIDTH - 1,
			placeholder: str = "..."
	):
		self._pkgs = pkgs
		self._other_msgcodes = other_msgcodes
		self._invalid_lines = invalid_lines
		self._max_width = max_width
		self._truncate_ = truncate
		self._truncate_placeholder = placeholder

	def _truncate(self, line: str):
		if len(line) > self._max_width:
			# make space for placeholder
			tr_line_len = self._max_width - len(self._truncate_placeholder)
			return line[:tr_line_len] + self._truncate_placeholder
		else:
			return line

	def _print_indented_line(self, line: str, indent_lvl: int = 0):
		line = "{}{}".format(self.INDENT_PREFIX * indent_lvl, line)
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
		header_width = 100
		print()
		print(colour("=" * header_width, fg='green'))
		print(colour("<<< Repoman results >>>".center(header_width, ' '), fg='yellow'))
		print(colour("=" * header_width, fg='green'))
		print()

		if self._pkgs:
			self._print_pkgs(self._pkgs, 0)
		if self._other_msgcodes:
			print()
			print(colour("Other messages", fg='yellow', bg='black') + ":")
			self._print_msgcodes(self._other_msgcodes, 1)
		if self._invalid_lines:
			print()
			print(colour("Invalid unparsable lines", fg='red', bg='black') + ":")
			for l in self._invalid_lines:
				print(l)
