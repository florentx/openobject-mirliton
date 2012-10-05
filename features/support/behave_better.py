# -*- coding: utf-8 -*-
"""Enhancements for Behave.

Some of them might be proposed upstream
"""
from behave import formatter
from behave import matchers
from behave import model

__all__ = ['patch_all']
_behave_patched = False


def patch_all():
    global _behave_patched
    if not _behave_patched:
        patch_matchers_get_matcher()
        patch_model_Table_raw()
        formatter.formatters.register(PrettyFormatter)
        _behave_patched = True


def patch_matchers_get_matcher():
    # Detect the regex expressions
    # https://github.com/jeamland/behave/issues/73
    def get_matcher(func, string):
        if string[:1] == string[-1:] == '/':
            return matchers.RegexMatcher(func, string[1:-1])
        return matchers.current_matcher(func, string)
    matchers.get_matcher = get_matcher


def patch_model_Table_raw():
    # Add attribute Table.raw
    def raw(self):
        yield list(self.headings)
        for row in self.rows:
            yield list(row)
    model.Table.raw = property(raw)


# Fixes:
# * colors for tags
# * colors for tables
# * colors for docstrings
class PrettyFormatter(formatter.pretty.PrettyFormatter):

    def table(self, table, strformat=unicode):
        cell_lengths = []
        all_rows = [table.headings] + table.rows
        for row in all_rows:
            lengths = [len(formatter.pretty.escape_cell(c)) for c in row]
            cell_lengths.append(lengths)

        max_lengths = []
        for col in range(0, len(cell_lengths[0])):
            max_lengths.append(max([c[col] for c in cell_lengths]))

        for i, row in enumerate(all_rows):
            #for comment in row.comments:
            #    self.stream.write('      %s\n' % comment.value)
            self.stream.write('      |')
            for j, (cell, max_length) in enumerate(zip(row, max_lengths)):
                self.stream.write(' ')
                self.stream.write(strformat(cell))
                self.stream.write(' ' * (max_length - cell_lengths[i][j]))
                self.stream.write(' |')
            self.stream.write('\n')
        self.stream.flush()

    def doc_string(self, doc_string, strformat=unicode):
        triplequotes = self.format('comments').text(u'"""')
        doc_string = strformat(self.escape_triple_quotes(doc_string))
        self.stream.write(self.indent(u'\n'.join([
            triplequotes, doc_string, triplequotes]), u'      ') + u'\n')

    def print_step(self, status, arguments, location, proceed):
        if proceed:
            step = self.steps.pop(0)
        else:
            step = self.steps[0]

        text_format = self.format(status)
        arg_format = self.arg_format(status)

        self.stream.write('    ')
        self.stream.write(text_format.text(step.keyword + ' '))
        line_length = 5 + len(step.keyword)

        step_name = unicode(step.name)

        text_start = 0
        for arg in arguments:
            text = step_name[text_start:arg.start]
            self.stream.write(text_format.text(text))
            line_length += len(text)
            self.stream.write(arg_format.text(arg.original))
            line_length += len(arg.original)
            text_start = arg.end

        if text_start != len(step_name):
            text = step_name[text_start:]
            self.stream.write(text_format.text(text))
            line_length += (len(text))

        location = self.indented_location(location, proceed)
        if self.show_source:
            self.stream.write(self.format('comments').text(location))
            line_length += len(location)
        self.stream.write("\n")

        self.step_lines = int((line_length - 1) / self.display_width)

        if self.show_multiline:
            if step.text:
                self.doc_string(step.text, strformat=text_format.text)
            if step.table:
                self.table(step.table, strformat=text_format.text)

    def print_tags(self, tags, indent):
        if not tags:
            return
        formatted_tags = u' '.join(self.format('tag').text('@' + tag)
                                   for tag in tags)
        self.stream.write(indent + formatted_tags + '\n')

    def eof(self):
        self.replay()
        self.stream.write('\033[A')
        self.stream.flush()
