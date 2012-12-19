# -*- coding: utf-8 -*-
"""Enhancements for Behave.

Some of them might be proposed upstream
"""
import os.path

from behave import formatter
from behave import matchers
from behave import model
from behave import runner

__all__ = ['patch_all']
_behave_patched = False


def patch_all():
    global _behave_patched
    if not _behave_patched:
        patch_matchers_get_matcher()
        patch_model_Feature_run()
        patch_model_Table_raw()
        patch_runner_Runner_feature_files()
        formatter.formatters.register(PlainFormatter)
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


def patch_model_Feature_run():
    # Fix exit status
    # https://github.com/jeamland/behave/issues/52
    def run(self, runner):
        self._run_orig(runner)
        return runner.context.failed
    model.Feature._run_orig = model.Feature.run
    model.Feature.run = run


def patch_model_Table_raw():
    # Add attribute Table.raw
    def raw(self):
        yield list(self.headings)
        for row in self.rows:
            yield list(row)
    model.Table.raw = property(raw)


def patch_runner_Runner_feature_files():
    # Fix features loading
    def feature_files(self):
        files = []
        for path in self.config.paths:
            if os.path.isdir(path):
                new_files = []
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        if filename.endswith('.feature'):
                            new_files.append(os.path.join(dirpath, filename))
                new_files.sort()
                files.extend(new_files)
            elif path.startswith('@') and os.path.exists(path[1:]):
                with open(path[1:]) as f:
                    files.extend([filename.strip() for filename in f])
            elif os.path.exists(path):
                files.append(path)
            else:
                raise RuntimeError("Can't find path: %s" % path)
        return files
    runner.Runner.feature_files = feature_files


# Flush the output after each scenario
class PlainFormatter(formatter.plain.PlainFormatter):

    def result(self, result):
        super(PlainFormatter, self).result(result)
        self.stream.flush()


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
        tags = u' '.join(u'@' + tag for tag in tags)
        self.stream.write(indent + self.format('tag').text(tags) + '\n')

    def eof(self):
        self.replay()
        # Skip empty line (key up)
        self.stream.write('\033[A')
        self.stream.flush()
