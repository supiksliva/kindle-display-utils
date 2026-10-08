package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

const (
	defaultAPIKey = "YOUR_API_KEY_HERE"
	defaultModel  = "z-ai/glm-5.3-flash"
	apiURL        = "https://api.polza.ai/v1/chat/completions"
	configFile    = "/mnt/us/ai/config.json"
)

type Config struct {
	APIKey string `json:"api_key"`
	Model  string `json:"model"`
}

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatRequest struct {
	Model       string    `json:"model"`
	Messages    []Message `json:"messages"`
	Temperature float64   `json:"temperature"`
}

type ChatChoice struct {
	Message Message `json:"message"`
}

type ChatResponse struct {
	Choices []ChatChoice `json:"choices"`
	Error   *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

func loadConfig() Config {
	cfg := Config{
		APIKey: defaultAPIKey,
		Model:  defaultModel,
	}
	data, err := os.ReadFile(configFile)
	if err == nil {
		_ = json.Unmarshal(data, &cfg)
	}
	return cfg
}

func wrapText(text string, maxWidth int) string {
	if maxWidth <= 0 {
		maxWidth = 50
	}
	var result strings.Builder
	paragraphs := strings.Split(text, "\n")

	for pIdx, p := range paragraphs {
		words := strings.Fields(p)
		if len(words) == 0 {
			result.WriteString("\n")
			continue
		}

		currentLineLen := 0
		for _, w := range words {
			wLen := len([]rune(w))
			if currentLineLen == 0 {
				result.WriteString(w)
				currentLineLen = wLen
			} else if currentLineLen+1+wLen <= maxWidth {
				result.WriteString(" ")
				result.WriteString(w)
				currentLineLen += 1 + wLen
			} else {
				result.WriteString("\n")
				result.WriteString(w)
				currentLineLen = wLen
			}
		}

		if pIdx < len(paragraphs)-1 {
			result.WriteString("\n")
		}
	}
	return result.String()
}

func main() {
	cfg := loadConfig()

	// Clear terminal screen
	fmt.Print("\033[2J\033[H")

	fmt.Println("==================================================")
	fmt.Println("       🤖 KINDLE AI CHAT (GLM-5.3 FLASH)          ")
	fmt.Println("==================================================")
	fmt.Println(" Напишите вопрос и нажмите [ENTER].")
	fmt.Println(" Для спецсимволов нажмите кнопку [SYM].")
	fmt.Println(" Команды: /new (новый диалог), /exit (выход).")
	fmt.Println(" Или нажмите физическую кнопку [HOME] для выхода.")
	fmt.Println("==================================================")
	fmt.Println()

	client := &http.Client{
		Timeout: 35 * time.Second,
	}

	history := []Message{
		{
			Role:    "system",
			Content: "Ты полезный, умный ассистент на электронной книге Kindle. Отвечай емко, понятно, по существу. Используй списки и абзацы.",
		},
	}

	reader := bufio.NewReader(os.Stdin)

	for {
		fmt.Print("Вы: ")
		input, err := reader.ReadString('\n')
		if err != nil {
			break
		}

		prompt := strings.TrimSpace(input)
		if prompt == "" {
			continue
		}

		// Handle local commands
		if strings.EqualFold(prompt, "/exit") || strings.EqualFold(prompt, "exit") || strings.EqualFold(prompt, "quit") {
			fmt.Println("\nДо свидания!")
			time.Sleep(500 * time.Millisecond)
			break
		}

		if strings.EqualFold(prompt, "/new") || strings.EqualFold(prompt, "/clear") {
			history = []Message{
				{
					Role:    "system",
					Content: "Ты полезный, умный ассистент на электронной книге Kindle. Отвечай емко, понятно, по существу. Используй списки и абзацы.",
				},
			}
			fmt.Print("\033[2J\033[H")
			fmt.Println("--- Новый диалог начат ---")
			fmt.Println()
			continue
		}

		if strings.EqualFold(prompt, "/help") {
			fmt.Println("\nКоманды:")
			fmt.Println("  /new  - начать новый диалог с чистого листа")
			fmt.Println("  /exit - закрыть приложение")
			fmt.Println("  [SYM] - меню спецсимволов и пунктуации")
			fmt.Println("  [HOME]- выход на главный экран Kindle\n")
			continue
		}

		history = append(history, Message{Role: "user", Content: prompt})

		fmt.Println("\n[ИИ думает...]")

		reqBody := ChatRequest{
			Model:       cfg.Model,
			Messages:    history,
			Temperature: 0.7,
		}

		reqBytes, err := json.Marshal(reqBody)
		if err != nil {
			fmt.Printf("Ошибка подготовки запроса: %v\n\n", err)
			continue
		}

		httpReq, err := http.NewRequest("POST", apiURL, bytes.NewBuffer(reqBytes))
		if err != nil {
			fmt.Printf("Ошибка запроса: %v\n\n", err)
			continue
		}

		httpReq.Header.Set("Authorization", "Bearer "+cfg.APIKey)
		httpReq.Header.Set("Content-Type", "application/json")

		resp, err := client.Do(httpReq)
		if err != nil {
			fmt.Printf("\n[Ошибка сети]: %v\nПроверьте подключение к Wi-Fi на Kindle.\n\n", err)
			// Remove failed user prompt from history
			if len(history) > 0 {
				history = history[:len(history)-1]
			}
			continue
		}

		body, err := io.ReadAll(resp.Body)
		resp.Body.Close()

		if err != nil {
			fmt.Printf("\n[Ошибка чтения ответа]: %v\n\n", err)
			continue
		}

		if resp.StatusCode != http.StatusOK {
			fmt.Printf("\n[Ошибка сервера %d]: %s\n\n", resp.StatusCode, string(body))
			continue
		}

		var chatResp ChatResponse
		if err := json.Unmarshal(body, &chatResp); err != nil {
			fmt.Printf("\n[Ошибка парсинга ответа]: %v\n\n", err)
			continue
		}

		if len(chatResp.Choices) == 0 {
			fmt.Println("\n[ИИ вернул пустой ответ]")
			continue
		}

		aiText := chatResp.Choices[0].Message.Content
		history = append(history, Message{Role: "assistant", Content: aiText})

		// Beautiful wrapped output for Kindle screen width (approx 48 chars in 24px font)
		wrapped := wrapText(aiText, 48)

		fmt.Println("\n--------------------------------------------------")
		fmt.Printf("ИИ:\n%s\n", wrapped)
		fmt.Println("--------------------------------------------------\n")
	}
}
