#!/bin/env python

import urwid
import config


def exit_on_q(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()


logo_text = urwid.Text(config.logo.text, align='center')
logo = urwid.LineBox(logo_text)
uname = urwid.Edit('username: ')
passw = urwid.Edit('password: ', mask='*')
login = urwid.LineBox(urwid.Pile([uname, passw]))
body = urwid.ListBox([logo, login])
frame = urwid.Frame(body, header=urwid.Text(
    'SuperSafeChat v0.0.1'), footer=urwid.Text('Not Connected'))
loop = urwid.MainLoop(frame, unhandled_input=exit_on_q)
loop.run()
