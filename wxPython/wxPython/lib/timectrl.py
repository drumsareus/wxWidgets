#----------------------------------------------------------------------------
# Name:         wxTimeCtrl.py
# Author:       Will Sadkin
# Created:      09/19/2002
# Copyright:   (c) 2002 by Will Sadkin, 2002
# License:     wxWindows license
#----------------------------------------------------------------------------
# NOTE:
#   This was written way it is because of the lack of masked edit controls
#   in wxWindows/wxPython.  I would also have preferred to derive this
#   control from a wxSpinCtrl rather than wxTextCtrl, but the wxTextCtrl
#   component of that control is inaccessible through the interface exposed in
#   wxPython.
#
#   wxTimeCtrl does not use validators, because it does careful manipulation
#   of the cursor in the text window on each keystroke, and validation is
#   cursor-position specific, so the control intercepts the key codes before the
#   validator would fire.
#

from wxPython.wx import *
import string

# The following bit of function is for debugging the subsequent code.
# To turn on debugging output, set _debug to 1
_debug = 0
_indent = 0

def _dbg(*args, **kwargs):
    global _indent

    if _debug:
        if len(args):
            if _indent:      print ' ' * 3 * _indent,
            for arg in args: print arg,
            print
    # else do nothing

    # post process args:
    for kwarg, value in kwargs.items():
        if kwarg == 'indent' and value:         _indent = _indent + 1
        elif kwarg == 'indent' and value == 0:  _indent = _indent - 1
        if _indent < 0: _indent = 0



# This class of event fires whenever the value of the time changes in the control:
wxEVT_TIMEVAL_UPDATED = wxNewId()
def EVT_TIMEUPDATE(win, id, func):
    """Used to trap events indicating that the current time has been changed."""
    win.Connect(id, -1, wxEVT_TIMEVAL_UPDATED, func)

class TimeUpdatedEvent(wxPyCommandEvent):
    def __init__(self, id, value ='12:00:00 AM'):
        wxPyCommandEvent.__init__(self, wxEVT_TIMEVAL_UPDATED, id)
        self.value = value
    def GetValue(self):
        """Retrieve the value of the float control at the time this event was generated"""
        return self.value



class wxTimeCtrl(wxTextCtrl):
    def __init__ (
                self, parent, id=-1, value = '12:00:00 AM',
                pos = wxDefaultPosition, size = wxDefaultSize,
                fmt24hr=0,
                spinButton = None,
                style = wxTE_PROCESS_TAB, name = "time"
        ):
        wxTextCtrl.__init__(self, parent, id, value='',
                            pos=pos, size=size, style=style, name=name)

        self.__fmt24hr = fmt24hr
        if size == wxDefaultSize:
            # set appropriate default sizes depending on format:
            if self.__fmt24hr:
                testText = '00:00:00 '
            else:
                testText = '00:00:00 XXX'
            w, h = self.GetTextExtent(testText)
            self.SetClientSize( (w+4, -1) )

        # Set up all the positions of the cells in the wxTimeCtrl (once):
        # Format of control is:
        #               hh:mm:ss xM
        #                         1
        # positions:    01234567890

        self.__listCells = ['hour', 'minute', 'second', 'am_pm']
        self.__listCellRange =   [(0,1,2), (3,4,5), (6,7,8), (9,10,11)]
        self.__listDelimPos =  [2,5,8]

        # Create dictionary of cell ranges, indexed by name or position in the range:
        self.__dictCellRange = {}
        for i in range(4):
            self.__dictCellRange[self.__listCells[i]] = self.__listCellRange[i]

        for cell in self.__listCells:
            for i in self.__dictCellRange[cell]:
                self.__dictCellRange[i] = self.__dictCellRange[cell]


        # Create lists of starting and ending positions for each range, and a dictionary of starting
        # positions indexed by name
        self.__listStartCellPos = []
        self.__listEndCellPos = []
        for tup in self.__listCellRange:
            self.__listStartCellPos.append(tup[0])  # 1st char of cell
            self.__listEndCellPos.append(tup[1])    # last char of cell (not including delimiter)

        self.__dictStartCellPos = {}
        for i in range(4):
            self.__dictStartCellPos[self.__listCells[i]] = self.__listStartCellPos[i]

        if self.__fmt24hr:  self.__lastCell = 'second'
        else:               self.__lastCell = 'am_pm'

        # Validate initial value and set if appropriate
        try:
            self.SetValue(value)
        except ValueError:
            self.SetValue('12:00:00 AM')

        # set initial position and selection state
        self.__SetCurrentCell(self.__dictStartCellPos['hour'])
        self.__bSelection = false

        EVT_TEXT(self, self.GetId(), self.__OnTextChange)
        EVT_SET_FOCUS(self, self.__OnFocus)
        EVT_CHAR(self, self.__OnChar)

        if spinButton:
            self.BindSpinbutton(spinButton)     # bind spin button up/down events to this control


    def SetValue(self, value):
        """
        Validating SetValue function for time strings, doing 12/24 format conversion as appropriate.
        """
        _dbg('wxTimeCtrl::SetValue', indent=1)
        dict_range = self.__dictCellRange
        dict_start = self.__dictStartCellPos

        fmt12len = dict_range['am_pm'][-1]
        fmt24len = dict_range['second'][-1]
        try:
            separators_correct = value[2] == ':' and value[5] == ':'
            len_ok = len(value) in (fmt12len, fmt24len)

            if len(value) > fmt24len:
                separators_correct = separators_correct and value[8] == ' '
            hour = int(value[dict_range['hour'][0]:dict_range['hour'][-1]])
            hour_ok = ((hour in range(0,24) and len(value) == fmt24len)
                       or (hour in range(1,13) and len(value) == fmt12len
                           and value[dict_start['am_pm']:] in ('AM', 'PM')))

            minute = int(value[dict_range['minute'][0]:dict_range['minute'][-1]])
            min_ok  = minute in range(60)
            second  = int(value[dict_range['second'][0]:dict_range['second'][-1]])
            sec_ok  = second in range(60)

            _dbg('len_ok =', len_ok, 'separators_correct =', separators_correct)
            _dbg('hour =', hour, 'hour_ok =', hour_ok, 'min_ok =', min_ok, 'sec_ok =', sec_ok)

            if len_ok and hour_ok and min_ok and sec_ok and separators_correct:
                _dbg('valid time string')


                self.__hour = hour
                if len(value) == fmt12len:                      # handle 12 hour format conversion for actual hour:
                    am = value[dict_start['am_pm']:] == 'AM'
                    if hour != 12 and not am:
                        self.__hour = hour = (hour+12) % 24
                    elif hour == 12:
                        if am: self.__hour = hour = 0

                self.__minute = minute
                self.__second = second

                # valid time
                need_to_convert = ((self.__fmt24hr and len(value) == fmt12len)
                                   or (not self.__fmt24hr and len(value) == fmt24len))
                _dbg('need_to_convert =', need_to_convert)

                if need_to_convert:     #convert to 12/24 hour format as specified:
                    dict_start = self.__dictStartCellPos
                    if self.__fmt24hr and len(value) == fmt12len:
                        text = '%.2d:%.2d:%.2d' % (hour, minute, second)
                    else:
                        if hour > 12:
                            hour = hour - 12
                            am_pm = 'PM'
                        elif hour == 12:
                            am_pm = 'PM'
                        else:
                            if hour == 0: hour = 12
                            am_pm = 'AM'
                        text = '%2d:%.2d:%.2d %s' % (hour, minute, second, am_pm)
                else:
                    text = value
                _dbg('text=', text)
                wxTextCtrl.SetValue(self, text)
                _dbg('firing TimeUpdatedEvent...')
                self.GetEventHandler().ProcessEvent(TimeUpdatedEvent(self.GetId(), text))
            else:
                _dbg('len_ok:', len_ok, 'separators_correct =', separators_correct)
                _dbg('hour_ok:', hour_ok, 'min_ok:', min_ok, 'sec_ok:', sec_ok, indent=0)
                raise ValueError, 'value is not a valid time string'

        except (TypeError, ValueError):
            _dbg(indent=0)
            raise ValueError, 'value is not a valid time string'
        _dbg(indent=0)

    def SetFromWxDateTime(self, wxdt):
        value = '%2d:%.2d:%.2d' % (wxdt.GetHour(), wxdt.GetMinute(), wxdt.GetSecond())
        self.SetValue(value)

    def GetWxDateTime(self):
        t = wxDateTimeFromHMS(self.__hour, self.__minute, self.__second)
        return t

    def SetMxDateTime(self, mxdt):
        from mx import DateTime
        value = '%2d:%.2d:%.2d' % (mxdt.hour, mxdt.minute, mxdt.second)
        self.SetValue(value)

    def GetMxDateTime(self):
        from mx import DateTime
        t = DateTime.Time(self.__hour, self.__minute, self.__second)
        return t

    def BindSpinButton(self, sb):
        """
        This function binds an externally created spin button to the control, so that
        up/down events from the button automatically change the control.
        """
        _dbg('wxTimeCtrl::BindSpinButton')
        self.__spinButton = sb
        if self.__spinButton:
            EVT_SPIN_UP(self.__spinButton, self.__spinButton.GetId(), self.__OnSpinUp)  # bind event handler to spin ctrl
            EVT_SPIN_DOWN(self.__spinButton, self.__spinButton.GetId(), self.__OnSpinDown)  # bind event handler to spin ctrl


#-------------------------------------------------------------------------------------------------------------
# these are private functions and overrides:

    def __SetCurrentCell(self, pos):
        """
        Sets state variables that indicate the current cell and position within the control.
        """
        self.__posCurrent = pos
        self.__cellStart, self.__cellEnd = self.__dictCellRange[pos][0], self.__dictCellRange[pos][-1]

    def SetInsertionPoint(self, pos):
        """
        Records the specified position and associated cell before calling base class' function.
        """
        self.__SetCurrentCell(pos)
        wxTextCtrl.SetInsertionPoint(self, pos)                 # (causes EVT_TEXT event to fire)


    def __OnTextChange(self, event):
        """
        This private event handler is required to retain the current position information of the cursor
        after update to the underlying text control is done.
        """
        _dbg('wxTimeCtrl::OnTextChange', indent=1)
        self.__SetCurrentCell(self.__posCurrent)                # ensure cell range vars are set

        # Note: must call self.SetSelection here to preserve insertion point cursor after update!
        # (I don't know why, but this does the trick!)
        if self.__bSelection:
            _dbg('reselecting from ', self.__posCurrent, 'to', self.__posSelectTo)
            self.SetSelection(self.__posCurrent, self.__posSelectTo)
        else:
            self.SetSelection(self.__posCurrent, self.__posCurrent)
        event.Skip()
        _dbg(indent=0)

    def __OnFocus(self, event):
        """
        This internal event handler ensures legal setting of input cursor on (re)focus to the control.
        """
        _dbg('wxTimeCtrl::OnFocus; ctrl id=', event.GetId())
        self.__SetCurrentCell(0)
        self.__bSelection = false
        self.__posSelectTo = self.__posCurrent
        self.SetInsertionPoint(self.__posCurrent)
        event.Skip()


    def __OnSpinUp(self, event):
        """
        Event handler for any bound spin button on EVT_SPIN_UP;
        causes control to behave as if up arrow was pressed.
        """
        _dbg('wxTimeCtrl::OnSpinUp')
        pos = self.GetInsertionPoint()
        self.IncrementValue(WXK_UP, pos)
        self.SetInsertionPoint(pos)

    def __OnSpinDown(self, event):
        """
        Event handler for any bound spin button on EVT_SPIN_DOWN;
        causes control to behave as if down arrow was pressed.
        """
        _dbg('wxTimeCtrl::OnSpinDown')
        pos = self.GetInsertionPoint()
        self.IncrementValue(WXK_DOWN, pos)
        self.SetInsertionPoint(pos)


    def __OnChar(self, event):
        """
        This private event handler is the main control point for the wxTimeCtrl.
        It governs whether input characters are accepted and if so, handles them
        so as to provide appropriate cursor and selection behavior for the control.
        """
        _dbg('wxTimeCtrl::OnChar', indent=1)

        # NOTE: Returning without calling event.Skip() eats the event before it
        # gets to the text control...

        key = event.GetKeyCode()
        text = self.GetValue()
        pos = self.GetInsertionPoint()
        if pos != self.__posCurrent:
            _dbg("insertion point has moved; resetting current cell")
            self.__SetCurrentCell(pos)
            self.SetSelection(self.__posCurrent, self.__posCurrent)

        sel_start, sel_to = self.GetSelection()
        selection = sel_start != sel_to
        if not selection:
            self.__bSelection = false           # predict unselection of entire region

        _dbg('keycode = ', key)
        _dbg('pos = ', pos)

        if key in (WXK_DELETE, WXK_BACK):                   # don't allow deletion
            _dbg(indent=0)
            return

        elif key == WXK_TAB:                                # skip to next field if applicable:
            _dbg('key == WXK_TAB')
            dict_range = self.__dictCellRange
            dict_start = self.__dictStartCellPos
            if event.ShiftDown():                           # tabbing backwords

                ###(NOTE: doesn't work; wxTE_PROCESS_TAB doesn't appear to send us this event!)

                _dbg('event.ShiftDown()')
                if pos in dict_range['hour']:               # already in 1st field
                    self.__SetCurrentCell(dict_start['hour']) # ensure we have our member vars set
                    event.Skip()                            #then do normal tab processing for the form

                elif pos in dict_range['minute']:           # skip to hours field
                    new_pos = dict_start['hour']
                elif pos in dict_range['second']:           # skip to minutes field
                    new_pos = dict_start['minute']
                elif pos in dict_range['am_pm']:            # skip to seconds field
                    new_pos = dict_start['second']

                self.__bSelection = true
                self.__posSelectTo = new_pos+2
                self.SetInsertionPoint(new_pos)             # force insert point to jump to next cell (swallowing TAB)

            else:
                if pos in dict_range[self.__lastCell]:      # already in last field; ensure we have our members set
                    self.__SetCurrentCell(dict_start[self.__lastCell])
                    _dbg('tab in last cell')
                    event.Skip()                            # then do normal tab processing for the form
                    _dbg(indent=0)
                    return

                if pos in dict_range['second']:             # skip to AM/PM field (if not last cell)
                    new_pos = dict_start['am_pm']
                elif pos in dict_range['minute']:           # skip to seconds field
                    new_pos = dict_start['second']
                elif pos in dict_range['hour']:             # skip to minutes field
                    new_pos = dict_start['minute']

                self.__bSelection = true
                self.__posSelectTo = new_pos+2
                self.SetInsertionPoint(new_pos)             # force insert point to jump to next cell (swallowing TAB)

        elif key == WXK_LEFT:                               # move left; set insertion point as appropriate:
            _dbg('key == WXK_LEFT')
            if event.ShiftDown():                           # selecting a range...
                _dbg('event.ShiftDown()')
                if sel_to != pos:
                    if sel_to - 1 == pos:                   # allow unselection of position
                        self.__bSelection = false           # predict unselection of entire region
                    event.Skip()
                if pos in self.__listStartCellPos:          # can't select pass delimiters
                    _dbg(indent=0)
                    return
                elif pos in self.__listEndCellPos:          # can't use normal selection, because position ends up
                                                            # at delimeter
                    _dbg('set selection from', pos-1, 'to', self.__posCurrent)
                    self.__bSelection = true
                    self.__posSelectTo = pos
                    self.__posCurrent = pos-1
                    self.SetSelection(self.__posCurrent, self.__posSelectTo)
                    _dbg(indent=0)
                    return
                else: event.Skip()                          # allow selection

            # else... not selecting
            if selection:
                _dbg('sel_start=', sel_start, 'sel_to=', sel_to, '(Clearing selection)')
                self.SetSelection(pos,pos)                  # clear selection
                self.__bSelection = false

            if pos == 0:                                    # let base ctrl handle left bound case
                event.Skip()
            elif pos in self.__listStartCellPos:            # skip (left) OVER the colon/space:
                self.SetInsertionPoint(pos-1)               # (this causes a EVT_TEXT)
                self.__SetCurrentCell(pos-2)                # set resulting position as "current"
            else:
                self.__SetCurrentCell(pos-1)                # record the new cell position after the event is finishedI
                                                            # and update spinbutton as necessary
            event.Skip()                                    # let base control handle event

        elif key == WXK_RIGHT:                              # move right
            _dbg('key == WXK_RIGHT')
            if event.ShiftDown():
                _dbg('event.ShiftDown()')
                if sel_to in self.__listDelimPos:           # can't select pass delimiters
                    _dbg(indent=0)
                    return
                elif pos in self.__listEndCellPos:          # can't use normal selection, because position ends up
                                                            # at delimeter
                    _dbg('set selection from', self.__posCurrent, 'to', pos+1)
                    self.__bSelection = true
                    self.__posSelectTo = pos+1
                    self.SetSelection(self.__posCurrent, self.__posSelectTo)
                    _dbg(indent=0)
                    return
                else: event.Skip()

            else:
                if selection:
                    _dbg('sel_start=', sel_start, 'sel_to=', sel_to, '(Clearing selection)')
                    pos = sel_start
                    self.SetSelection(pos,pos)              # clear selection
                    self.__bSelection = false
                if pos == self.__dictStartCellPos[self.__lastCell]+1:
                    _dbg(indent=0)
                    return                                  # don't allow cursor past last cell
                if pos in self.__listEndCellPos:            # skip (right) OVER the colon/space:
                    self.SetInsertionPoint(pos+1)           # (this causes a EVT_TEXT)
                    self.__SetCurrentCell(pos+2)            # set resulting position
                else:
                    self.__SetCurrentCell(pos+1)            # record the new cell position after the event is finished
                self.__bSelection = false
                event.Skip()

        elif key in (WXK_UP, WXK_DOWN):
            _dbg('key in (WXK_UP, WXK_DOWN)')
            self.IncrementValue(key, pos)                   # increment/decrement as appropriate
            self.SetInsertionPoint(pos)

        elif key < WXK_SPACE or key == WXK_DELETE or key > 255:
            event.Skip()                                    # non alphanumeric; process normally (Right thing to do?)

        elif chr(key) in string.digits:                     # let ChangeValue validate and update current position
            self.ChangeValue(chr(key), pos)                 # handle event (and swallow it)

        elif chr(key) in ('A', 'P', 'M', ' '):              # let ChangeValue validate and update current position
            self.ChangeValue(chr(key), pos)                 # handle event (and swallow it)

        else:                                               # disallowed char; swallow event
            _dbg(indent=0)
            return
        _dbg(indent=0)

    def IncrementValue(self, key, pos):
        _dbg('wxTimeCtrl::IncrementValue', key, pos)
        text = self.GetValue()

        sel_start, sel_to = self.GetSelection()
        selection = sel_start != sel_to
        cell_selected = selection and sel_to -1 != pos

        dict_start = self.__dictStartCellPos

        # Determine whether we should change the entire cell or just a portion of it:
        if( not selection
            or cell_selected
            or text[pos] == ' '
            or text[pos] == '9' and text[pos-1] == ' ' and key == WXK_UP
            or text[pos] == '1' and text[pos-1] == ' ' and key == WXK_DOWN
            or pos >= dict_start['am_pm']):
            _dbg(indent=1)
            self.IncrementCell(key, pos)
            _dbg(indent=0)
        else:
            if key == WXK_UP:   inc = 1
            else:               inc = -1

            if pos == dict_start['hour'] and not self.__fmt24hr:
                if text[pos] == ' ': digit = '1'                    # allow ' ' or 1 for 1st digit in 12hr format
                else:                digit = ' '
            else:
                if pos == dict_start['hour']:
                    if int(text[pos + 1]) >3:   mod = 2            # allow for 20-23
                    else:                       mod = 3            # allow 00-19
                elif pos == dict_start['hour'] + 1:
                    if self.__fmt24hr:
                        if text[pos - 1] == '2': mod = 4            # allow hours 20-23
                        else:                    mod = 10           # allow hours 00-19
                    else:
                        if text[pos - 1] == '1': mod = 3            # allow hours 10-12
                        else:                    mod = 10           # allow 0-9

                elif pos in (dict_start['minute'],
                             dict_start['second']): mod = 6         # allow minutes/seconds 00-59
                else:                               mod = 10

                digit = '%d' % ((int(text[pos]) + inc) % mod)

            _dbg(indent=1)
            _dbg("new digit = \'%s\'" % digit)
            self.ChangeValue(digit, pos)
            _dbg(indent=0)



    def IncrementCell(self, key, pos):
        _dbg('wxTimeCtrl::IncrementCell', key, pos)
        self.__SetCurrentCell(pos)                                  # determine current cell
        hour, minute, second = self.__hour, self.__minute, self.__second
        text = self.GetValue()
        dict_start = self.__dictStartCellPos
        if key == WXK_UP:   inc = 1
        else:               inc = -1

        if self.__cellStart == dict_start['am_pm']:
            am = text[dict_start['am_pm']:] == 'AM'
            if am: hour = hour + 12
            else:  hour = hour - 12
        else:
            if self.__cellStart == dict_start['hour']:
                hour = (hour + inc) % 24
            elif self.__cellStart == dict_start['minute']:
                minute = (minute + inc) % 60
            elif self.__cellStart == dict_start['second']:
                second = (second + inc) % 60

        newvalue = '%.2d:%.2d:%.2d' % (hour, minute, second)

        self.__posCurrent = self.__cellStart
        self.__posSelectTo = self.__cellEnd
        self.__bSelection = true
        _dbg(indent=1)
        self.SetValue(newvalue)
        _dbg(indent=0)


    def ChangeValue(self, char, pos):
        _dbg('wxTimeCtrl::ChangeValue', "\'" + char + "\'", pos)
        text = self.GetValue()

        self.__SetCurrentCell(pos)
        sel_start, sel_to = self.GetSelection()
        self.__posSelectTo = sel_to
        self.__bSelection = selection = sel_start != sel_to
        cell_selected = selection and sel_to -1 != pos

        dict_start = self.__dictStartCellPos

        if pos in self.__listDelimPos: return                   # don't allow change of punctuation

        elif( 0 < pos < dict_start['am_pm'] and char not in string.digits):
            return                                              # AM/PM not allowed in this position

        # See if we're changing the hour cell, and validate/update appropriately:
        #
        hour_start = dict_start['hour']                         # (ie. 0)

        if pos == hour_start:                                   # if at 1st position,
            if self.__fmt24hr:                                  # and using 24 hour format
                if char not in ('0', '1', '2'):                 # return if digit not 0,1, or 2
                    return
                if cell_selected:                               # replace cell contents
                    newtext = '%.2d' % int(char) + text[hour_start+2:]
                else:                                           # relace current position
                    newtext = char + text[pos+1:]
            else:                                               # (12 hour format)
                if char not in ('1', ' '):                      # can only type a 1 or space
                    return
                if text[pos+1] not in ('0', '1', '2'):          # and then, only if other column is 0,1, or 2
                    return
                if( char == ' '                                 # and char isn't space and
                      and (cell_selected or text[pos+1] == '0')):  # 2nd column is 0 or cell isn't selected
                    return
                # else... ok
                if cell_selected:                               # replace cell contents
                    newtext = '%2d' % int(char) + text[hour_start+2:]
                else:                                           # relace current position
                    newtext = char + text[pos+1:]
                if char == ' ': self.SetInsertionPoint(pos+1)   # move insert point to legal position

        elif pos == hour_start+1:                               # if editing 2nd position of hour
            if( not self.__fmt24hr                              # and using 12 hour format
                and text[hour_start] == '1'                     # if 1st char is 1,
                and char not in ('0', '1', '2')):               # disallow anything bug 0,1, or 2
                return
            newtext = text[hour_start] + char + text[hour_start+2:]  # else any digit ok

        # Do the same sort of validation for minute and second cells
        elif pos in (dict_start['minute'], dict_start['second']):
            if cell_selected:                                   # if cell selected, replace value
                newtext = text[:pos] + '%.2d' % int(char) + text[pos+2:]
            elif int(char) > 5: return                          # else disallow > 59 for minute and second fields
            else:
                newtext = text[:pos] + char + text[pos+1:]      # else ok

        elif pos in (dict_start['minute']+1, dict_start['second']+1):
            newtext = text[:pos] + char + text[pos+1:]          # all digits ok for 2nd digit of minute/second

        # Process AM/PM cell
        elif pos == dict_start['am_pm']:
            if char not in ('A','P'): return                    # disallow all but A or P as 1st char of column
            newtext = text[:pos] + char + text[pos+1:]
        else: return    # not a valid position

        # update member position vars and set selection to character changed
        self.__posCurrent = pos+1
        self.__SetCurrentCell(self.__posCurrent)
        _dbg(indent=1)
        _dbg('newtext=', newtext)
        _dbg(indent=0)
        self.SetValue(newtext)
        self.SetInsertionPoint(pos+1)

#----------------------------------------------------------------------------


if __name__ == '__main__':
    import traceback

    class TestPanel(wxPanel):
        def __init__(self, parent, id,
                     pos = wxPyDefaultPosition, size = wxPyDefaultSize,
                     fmt24hr = 0, test_mx = 0,
                     style = wxTAB_TRAVERSAL ):

            self.test_mx = test_mx
            wxPanel.__init__(self, parent, id, pos, size, style)

            sizer = wxBoxSizer( wxHORIZONTAL )
            self.tc = wxTimeCtrl(self, 10, fmt24hr = fmt24hr)
            sizer.AddWindow( self.tc, 0, wxALIGN_CENTRE|wxLEFT|wxTOP|wxBOTTOM, 5 )
            sb = wxSpinButton( self, 20, wxDefaultPosition, wxSize(-1,20), 0 )
            self.tc.BindSpinButton(sb)
            sizer.AddWindow( sb, 0, wxALIGN_CENTRE|wxRIGHT|wxTOP|wxBOTTOM, 5 )

            self.SetAutoLayout( true )
            self.SetSizer( sizer )
            sizer.Fit( self )
            sizer.SetSizeHints( self )

            EVT_TIMEUPDATE(self, self.tc.GetId(), self.OnTimeChange)

        def OnTimeChange(self, event):
            _dbg('OnTimeChange: value = ', event.GetValue())
            wxdt = self.tc.GetWxDateTime()
            _dbg('wxdt =', wxdt.GetHour(), wxdt.GetMinute(), wxdt.GetSecond())
            if self.test_mx:
                mxdt = self.tc.GetMxDateTime()
                _dbg('mxdt =', mxdt.hour, mxdt.minute, mxdt.second)


    class MyApp(wxApp):
        def OnInit(self):
            import sys
            fmt24hr = '24' in sys.argv
            test_mx = 'mx' in sys.argv
            try:
                frame = wxFrame(NULL, -1, "Junk", wxPoint(20,20), wxSize(100,100) )
                panel = TestPanel(frame, -1, wxPoint(-1,-1), fmt24hr=fmt24hr, test_mx = test_mx)
                frame.Show(true)
            except:
                traceback.print_exc()
                return false
            return true

    try:
        app = MyApp(0)
        app.MainLoop()
    except:
        traceback.print_exc()
