#!/bin/env python

import curses
import curses.textpad
from curses import wrapper, textpad
import config
import time


class Logo:
    def __init__(self):
        text = config.logo.text
        self.width = curses.COLS
        self.height = len(text) + 2

        self.logo_height = len(text)
        self.logo_width = len(max(text, key=lambda l: len(l)))
        self.text = text

        self.win = curses.newwin(self.height, self.width, 0, 0)

    def draw(self):
        curr_line = 1
        for l in config.logo.text:
            x = (self.width - 1) / 2 - self.logo_width / 2
            self.win.addstr(curr_line, int(x), l)
            curr_line += 1
        textpad.rectangle(
            self.win, 0, 0, self.height - 1, self.width - 2)


def main(stdscr):
    curses.curs_set(False)
    stdscr.clear()

    logo = Logo()
    windows = [stdscr, logo.win]

    running = True
    while running:
        logo.draw()

        for w in windows:
            w.refresh()

        c = stdscr.getch()
        if c == ord('q'):
            running = False


if __name__ == "__main__":
    wrapper(main)
