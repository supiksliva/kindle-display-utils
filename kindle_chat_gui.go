package main

import (
	"encoding/binary"
	"fmt"
	"strings"
	"syscall"
	"unicode"
)

const (
	X_RES  = 600
	Y_RES  = 800
	STRIDE = 300 // 600 / 2 for 4bpp

	FONT_W   = 12
	FONT_H   = 24
	MAX_COLS = 48

	EVIOCGRAB = 0x40044590

	REQ_FILE  = "/var/tmp/ai_req.txt"
	RESP_FILE = "/var/tmp/ai_resp.txt"

	// Colors for high contrast Dark Mode (White on Black)
	COLOR_BG   byte = 0x00 // Pure Black
	COLOR_TEXT byte = 0x0F // Pure White
	COLOR_LINE byte = 0x0F // Pure White separator
)

// Linux input event struct for 32-bit ARM (16 bytes)
type InputEvent struct {
	TimeSec  uint32
	TimeUsec uint32
	Type     uint16
	Code     uint16
	Value    int32
}

type DisplayLine struct {
	Text   string
	IsUser bool
	IsMeta bool
}

var (
	fb     = make([]byte, 240000)
	fbFd   int = -1
	kpadFd int = -1

	displayLines []DisplayLine
	scrollOffset = 0
	inputRunes   []rune
	langMode     = "RU" // "RU" or "EN"

	shiftDown   = false
	shiftSticky = false
	altDown     = false
	altSticky   = false

	lastSpaceMs int64 = 0
)

// Direct Linux system calls (zero Go runtime timer/netpoll dependencies)
func rawSleepMs(ms int) {
	ts := syscall.Timespec{
		Sec:  int32(ms / 1000),
		Nsec: int32((ms % 1000) * 1000000),
	}
	_ = syscall.Nanosleep(&ts, nil)
}

func nowMs() int64 {
	var tv syscall.Timeval
	_ = syscall.Gettimeofday(&tv)
	return int64(tv.Sec)*1000 + int64(tv.Usec)/1000
}

func rawOpenFile(path string, mode int, perm uint32) (int, error) {
	return syscall.Open(path, mode, perm)
}

func rawReadFile(path string) ([]byte, error) {
	fd, err := syscall.Open(path, syscall.O_RDONLY, 0)
	if err != nil {
		return nil, err
	}
	defer syscall.Close(fd)
	buf := make([]byte, 32768)
	n, err := syscall.Read(fd, buf)
	if err != nil {
		return nil, err
	}
	return buf[:n], nil
}

func rawWriteFile(path string, data []byte) error {
	fd, err := syscall.Open(path, syscall.O_CREAT|syscall.O_WRONLY|syscall.O_TRUNC, 0666)
	if err != nil {
		return err
	}
	defer syscall.Close(fd)
	_, err = syscall.Write(fd, data)
	return err
}

func rawRemove(path string) {
	_ = syscall.Unlink(path)
}

func setPixel(x, y int, color byte) {
	if x < 0 || x >= X_RES || y < 0 || y >= Y_RES {
		return
	}
	idx := y*STRIDE + x/2
	c := color & 0x0F
	if x%2 == 0 {
		fb[idx] = (fb[idx] & 0x0F) | (c << 4)
	} else {
		fb[idx] = (fb[idx] & 0xF0) | c
	}
}

func drawRect(x, y, w, h int, color byte) {
	for cy := y; cy < y+h; cy++ {
		for cx := x; cx < x+w; cx++ {
			setPixel(cx, cy, color)
		}
	}
}

func drawRune(x, y int, r rune, fg, bg byte) {
	data, ok := Font24[r]
	if !ok {
		data, ok = Font24['?']
		if !ok {
			return
		}
	}

	for row := 0; row < 24; row++ {
		rowVal := (uint16(data[row*2]) << 8) | uint16(data[row*2+1])
		for col := 0; col < 12; col++ {
			if (rowVal & (1 << (15 - col))) != 0 {
				setPixel(x+col, y+row, fg)
			} else if bg != 0xFF { // 0xFF means transparent
				setPixel(x+col, y+row, bg)
			}
		}
	}
}

func drawString(x, y int, s string, fg, bg byte) {
	curX := x
	for _, r := range s {
		if curX+FONT_W > X_RES {
			break
		}
		drawRune(curX, y, r, fg, bg)
		curX += FONT_W
	}
}

func flushFb() {
	if fbFd >= 0 {
		_, _ = syscall.Seek(fbFd, 0, 0)
		_, _ = syscall.Write(fbFd, fb)
	}
}

func refreshScreen(full bool) {
	flushFb()
	val := []byte("1\n")
	if full {
		val = []byte("2\n")
	}
	_ = rawWriteFile("/proc/eink_fb/update_display", val)
}

func refreshInputArea() {
	flushFb()
	_ = rawWriteFile("/proc/eink_fb/update_display", []byte("1\n"))
}

func wrapText(text string, maxWidth int) []string {
	var result []string
	paragraphs := strings.Split(text, "\n")
	for _, p := range paragraphs {
		words := strings.Fields(p)
		if len(words) == 0 {
			result = append(result, "")
			continue
		}
		cur := ""
		for _, w := range words {
			wRunes := len([]rune(w))
			curRunes := len([]rune(cur))
			if cur == "" {
				cur = w
			} else if curRunes+1+wRunes <= maxWidth {
				cur += " " + w
			} else {
				result = append(result, cur)
				cur = w
			}
		}
		if cur != "" {
			result = append(result, cur)
		}
	}
	return result
}

func addDisplayLines(text string, isUser, isMeta bool) {
	wrapped := wrapText(text, MAX_COLS)
	for _, l := range wrapped {
		displayLines = append(displayLines, DisplayLine{
			Text:   l,
			IsUser: isUser,
			IsMeta: isMeta,
		})
	}
	autoScrollBottom()
}

func autoScrollBottom() {
	maxVisible := 27
	if len(displayLines) > maxVisible {
		scrollOffset = len(displayLines) - maxVisible
	} else {
		scrollOffset = 0
	}
}

func redrawAll() {
	// 1. Clear entire background to pure Black (0x00) for high-contrast dark mode
	for i := range fb {
		fb[i] = COLOR_BG
	}

	// 2. Top Header Bar: White text on Black background
	drawString(12, 6, "KINDLE AI (GLM-5.3)", COLOR_TEXT, COLOR_BG)
	drawString(380, 6, "[HOME: Выход]", COLOR_TEXT, COLOR_BG)

	// Dividing line below header
	drawRect(0, 34, X_RES, 2, COLOR_LINE)

	// 3. Chat History Area (y = 40 .. 705)
	startY := 42
	maxVisible := 27
	startIdx := scrollOffset
	if startIdx < 0 {
		startIdx = 0
	}
	endIdx := startIdx + maxVisible
	if endIdx > len(displayLines) {
		endIdx = len(displayLines)
	}

	curY := startY
	for i := startIdx; i < endIdx; i++ {
		line := displayLines[i]
		// All text in pure White on Black for 100% contrast
		drawString(12, curY, line.Text, COLOR_TEXT, COLOR_BG)
		curY += FONT_H
	}

	// 4. White separator line above input bar
	drawRect(0, 715, X_RES, 2, COLOR_LINE)

	// 5. Input Area
	redrawInputOnly()
}

func redrawInputOnly() {
	// Black background for input area
	drawRect(0, 717, X_RES, 83, COLOR_BG)

	effectiveShift := shiftDown || shiftSticky
	effectiveAlt := altDown || altSticky

	var modeBadge string
	var hintText string

	if langMode == "RU" {
		if effectiveAlt {
			modeBadge = "RU-ALT"
			hintText = "P:х O:ъ L:ж K:э M:б E:ё .: . Sp: ,"
		} else if effectiveShift {
			modeBadge = "RU-ВВЕРХ"
			hintText = "Заглавные буквы | Alt: х,ъ,ж,э,б,ё"
		} else {
			modeBadge = "RU"
			hintText = "SYM: EN | Alt: х,ъ,ж,э,б,ё | Enter: Отправить"
		}
	} else {
		if effectiveAlt {
			modeBadge = "EN-ALT"
			hintText = "Q-P: 1..0 | A-L: !..("
		} else if effectiveShift {
			modeBadge = "EN-CAPS"
			hintText = "CAPITAL LETTERS"
		} else {
			modeBadge = "EN"
			hintText = "SYM: RU | Alt: 123/Sym | Enter: Send"
		}
	}

	// Draw Hint Line in White on Black
	drawString(12, 722, fmt.Sprintf("[%s] %s", modeBadge, hintText), COLOR_TEXT, COLOR_BG)

	// Draw Prompt Line in White on Black
	promptStr := fmt.Sprintf("[%s] Вы: %s_", modeBadge, string(inputRunes))
	runes := []rune(promptStr)
	if len(runes) > MAX_COLS {
		promptStr = "..." + string(runes[len(runes)-MAX_COLS+3:])
	}
	drawString(12, 752, promptStr, COLOR_TEXT, COLOR_BG)

	refreshInputArea()
}

func sendQuestionToAI(prompt string) {
	addDisplayLines("» Вы: "+prompt, true, false)
	addDisplayLines("[ИИ думает...]", false, true)
	redrawAll()
	refreshScreen(false)

	// Clear any previous response
	rawRemove(RESP_FILE)

	// Write prompt to request file for native background curl worker
	err := rawWriteFile(REQ_FILE, []byte(prompt))
	if err != nil {
		if len(displayLines) > 0 && displayLines[len(displayLines)-1].IsMeta {
			displayLines = displayLines[:len(displayLines)-1]
		}
		addDisplayLines(fmt.Sprintf("[Ошибка записи запроса]: %v", err), false, true)
		redrawAll()
		refreshScreen(false)
		return
	}

	// Wait up to 45 seconds for response using raw nanosleep syscall
	gotResponse := false
	for i := 0; i < 450; i++ {
		rawSleepMs(100)
		respData, err := rawReadFile(RESP_FILE)
		if err == nil && len(respData) > 0 {
			rawRemove(RESP_FILE)

			// Remove thinking line
			if len(displayLines) > 0 && displayLines[len(displayLines)-1].IsMeta {
				displayLines = displayLines[:len(displayLines)-1]
			}

			aiText := strings.TrimSpace(string(respData))
			if strings.HasPrefix(aiText, "[Ошибка") {
				addDisplayLines(aiText, false, true)
			} else {
				addDisplayLines("» ИИ: "+aiText, false, false)
			}
			redrawAll()
			refreshScreen(true) // Full refresh after AI response
			gotResponse = true
			break
		}
	}

	if !gotResponse {
		if len(displayLines) > 0 && displayLines[len(displayLines)-1].IsMeta {
			displayLines = displayLines[:len(displayLines)-1]
		}
		addDisplayLines("[Таймаут: сервер не ответил вовремя. Проверьте Wi-Fi]", false, true)
		redrawAll()
		refreshScreen(false)
	}
}

func main() {
	var err error

	// 1. Open Framebuffer (/dev/fb0) with raw syscall
	fbFd, err = rawOpenFile("/dev/fb0", syscall.O_RDWR, 0)
	if err != nil {
		return
	}
	defer func() {
		if fbFd >= 0 {
			syscall.Close(fbFd)
		}
	}()

	// 2. Open Keyboard (/dev/input/event0) with raw syscall
	kpadFd, err = rawOpenFile("/dev/input/event0", syscall.O_RDONLY, 0)
	if err != nil {
		return
	}
	defer func() {
		if kpadFd >= 0 {
			_, _, _ = syscall.Syscall(syscall.SYS_IOCTL, uintptr(kpadFd), EVIOCGRAB, 0)
			syscall.Close(kpadFd)
		}
	}()

	// Exclusive grab: ioctl(fd, EVIOCGRAB, 1)
	_, _, _ = syscall.Syscall(syscall.SYS_IOCTL, uintptr(kpadFd), EVIOCGRAB, 1)

	// Clean any stale request/response files
	rawRemove(REQ_FILE)
	rawRemove(RESP_FILE)

	// Welcome message (White text on Black)
	addDisplayLines("=== KINDLE AI CHAT (GLM-5.3 FLASH) ===", false, true)
	addDisplayLines("Кнопка [SYM]: переключение языка RU / EN.", false, true)
	addDisplayLines("Буквы х,ъ,ж,э,б,ё: зажмите или нажмите Alt.", false, true)
	addDisplayLines("Знаки препинания: Alt+Пробел = запятая, Alt+. = точка.", false, true)
	addDisplayLines("Двойной пробел: точка с пробелом.", false, true)
	addDisplayLines("Боковые кнопки или Стрелки: прокрутка чата.", false, true)
	addDisplayLines("Кнопка [HOME] или [BACK]: выход на экран книг.", false, true)

	redrawAll()
	refreshScreen(true)

	// Keyboard layout tables
	ruMap := map[uint16]rune{
		16: 'й', 17: 'ц', 18: 'у', 19: 'к', 20: 'е', 21: 'н', 22: 'г', 23: 'ш', 24: 'щ', 25: 'з',
		30: 'ф', 31: 'ы', 32: 'в', 33: 'а', 34: 'п', 35: 'р', 36: 'о', 37: 'л', 38: 'д',
		44: 'я', 45: 'ч', 46: 'с', 47: 'м', 48: 'и', 49: 'т', 50: 'ь', 52: 'ю',
	}

	ruAltMap := map[uint16]rune{
		25: 'х', // Alt + P
		24: 'ъ', // Alt + O
		38: 'ж', // Alt + L
		37: 'э', // Alt + K
		50: 'б', // Alt + M
		18: 'ё', // Alt + E
		52: '.', // Alt + .
		44: '-', // Alt + Z
		30: '!', // Alt + A
		16: '1', // Alt + Q
		17: '2', // Alt + W
		19: '4', // Alt + R
		20: '5', // Alt + T
		21: '6', // Alt + Y
		22: '7', // Alt + U
		23: '8', // Alt + I
	}

	enMap := map[uint16]rune{
		16: 'q', 17: 'w', 18: 'e', 19: 'r', 20: 't', 21: 'y', 22: 'u', 23: 'i', 24: 'o', 25: 'p',
		30: 'a', 31: 's', 32: 'd', 33: 'f', 34: 'g', 35: 'h', 36: 'j', 37: 'k', 38: 'l',
		44: 'z', 45: 'x', 46: 'c', 47: 'v', 48: 'b', 49: 'n', 50: 'm', 52: '.',
	}

	enAltMap := map[uint16]rune{
		16: '1', 17: '2', 18: '3', 19: '4', 20: '5', 21: '6', 22: '7', 23: '8', 24: '9', 25: '0',
		30: '!', 31: '@', 32: '#', 33: '$', 34: '%', 35: '^', 36: '&', 37: '*', 38: '(',
		44: '-', 45: '_', 46: '+', 47: '=', 48: '[', 49: ']', 50: ';', 52: '?',
	}

	var ev InputEvent
	buf := make([]byte, 16)

	for {
		n, err := syscall.Read(kpadFd, buf)
		if err != nil || n < 16 {
			break
		}

		ev.TimeSec = binary.LittleEndian.Uint32(buf[0:4])
		ev.TimeUsec = binary.LittleEndian.Uint32(buf[4:8])
		ev.Type = binary.LittleEndian.Uint16(buf[8:10])
		ev.Code = binary.LittleEndian.Uint16(buf[10:12])
		ev.Value = int32(binary.LittleEndian.Uint32(buf[12:16]))

		if ev.Type != 1 { // EV_KEY
			continue
		}

		// Modifier: Shift (42, 54) or aA (190)
		if ev.Code == 42 || ev.Code == 54 || ev.Code == 190 {
			if ev.Value == 1 {
				shiftDown = true
				shiftSticky = !shiftSticky
			} else if ev.Value == 0 {
				shiftDown = false
			}
			redrawInputOnly()
			continue
		}

		// Modifier: Alt (56, 100)
		if ev.Code == 56 || ev.Code == 100 {
			if ev.Value == 1 {
				altDown = true
				altSticky = !altSticky
			} else if ev.Value == 0 {
				altDown = false
			}
			redrawInputOnly()
			continue
		}

		// Only handle key press (1) and repeat (2)
		if ev.Value == 0 {
			continue
		}

		effectiveShift := shiftDown || shiftSticky
		effectiveAlt := altDown || altSticky

		// Check Home key -> Exit
		if ev.Code == 102 { // KEY_HOME
			break
		}

		// Check Back key
		if ev.Code == 158 { // KEY_BACK
			if len(inputRunes) > 0 {
				inputRunes = inputRunes[:len(inputRunes)-1]
				redrawInputOnly()
			} else {
				break // Exit if buffer is empty
			}
			continue
		}

		// Check SYM key -> Toggle language
		if ev.Code == 126 { // KEY_SYM
			if langMode == "RU" {
				langMode = "EN"
			} else {
				langMode = "RU"
			}
			altSticky = false
			shiftSticky = false
			redrawInputOnly()
			continue
		}

		// Check Scrolling: Page Up / Up Arrow (103, 104, 193, 109)
		if ev.Code == 103 || ev.Code == 193 || ev.Code == 109 {
			if scrollOffset > 0 {
				scrollOffset -= 4
				if scrollOffset < 0 {
					scrollOffset = 0
				}
				redrawAll()
				refreshScreen(false)
			}
			continue
		}

		// Check Scrolling: Page Down / Down Arrow (108, 104, 191)
		if ev.Code == 108 || ev.Code == 104 || ev.Code == 191 {
			maxVisible := 27
			maxScroll := len(displayLines) - maxVisible
			if maxScroll > 0 && scrollOffset < maxScroll {
				scrollOffset += 4
				if scrollOffset > maxScroll {
					scrollOffset = maxScroll
				}
				redrawAll()
				refreshScreen(false)
			}
			continue
		}

		// Check Backspace / Del (14)
		if ev.Code == 14 {
			if len(inputRunes) > 0 {
				inputRunes = inputRunes[:len(inputRunes)-1]
				redrawInputOnly()
			}
			continue
		}

		// Check Space (57)
		if ev.Code == 57 {
			now := nowMs()
			if effectiveAlt {
				// Alt + Space -> comma and space
				inputRunes = append(inputRunes, ',', ' ')
				altSticky = false
			} else if len(inputRunes) > 0 && inputRunes[len(inputRunes)-1] == ' ' && (now-lastSpaceMs) < 700 {
				// Double space -> period and space
				inputRunes[len(inputRunes)-1] = '.'
				inputRunes = append(inputRunes, ' ')
			} else {
				inputRunes = append(inputRunes, ' ')
			}
			lastSpaceMs = now
			redrawInputOnly()
			continue
		}

		// Check Enter (28) or Select (194)
		if ev.Code == 28 || ev.Code == 194 {
			prompt := strings.TrimSpace(string(inputRunes))
			inputRunes = nil
			altSticky = false
			shiftSticky = false

			if prompt == "" {
				redrawInputOnly()
				continue
			}

			// Local commands
			if strings.EqualFold(prompt, "/exit") || strings.EqualFold(prompt, "exit") || strings.EqualFold(prompt, "quit") {
				break
			}
			if strings.EqualFold(prompt, "/new") || strings.EqualFold(prompt, "/clear") {
				displayLines = nil
				addDisplayLines("--- Новый диалог начат ---", false, true)
				redrawAll()
				refreshScreen(true)
				// Send reset to helper
				_ = rawWriteFile(REQ_FILE, []byte("/new"))
				continue
			}

			sendQuestionToAI(prompt)
			continue
		}

		// Character keys
		var ch rune
		if langMode == "RU" {
			if effectiveAlt {
				if r, ok := ruAltMap[ev.Code]; ok {
					ch = r
				}
				// Alt+. with Shift gives ?
				if ev.Code == 52 && effectiveShift {
					ch = '?'
				}
			}
			if ch == 0 {
				if r, ok := ruMap[ev.Code]; ok {
					ch = r
				}
			}
		} else {
			if effectiveAlt {
				if r, ok := enAltMap[ev.Code]; ok {
					ch = r
				}
			}
			if ch == 0 {
				if r, ok := enMap[ev.Code]; ok {
					ch = r
				}
			}
		}

		if ch != 0 {
			if effectiveShift && unicode.IsLetter(ch) {
				ch = unicode.ToUpper(ch)
			}
			inputRunes = append(inputRunes, ch)

			// One-shot modifier reset if sticky
			if !altDown {
				altSticky = false
			}
			if !shiftDown {
				shiftSticky = false
			}

			redrawInputOnly()
		}
	}
}
